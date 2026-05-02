import json
from io import BytesIO

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from . import db
from .insights import analyze_run, dashboard_snapshot, journal_intelligence
from .models import JournalEntry, PersonalityProfile, SimulationRun
from .simulation import Profile, generate_parallel_selves, profile_to_dict

main_bp = Blueprint("main", __name__)


def _get_profile() -> PersonalityProfile:
    prof = PersonalityProfile.query.filter_by(user_id=current_user.id).first()
    if not prof:
        prof = PersonalityProfile(user_id=current_user.id)
        db.session.add(prof)
        db.session.commit()
    return prof


def _parse_run(run: SimulationRun | None):
    if not run:
        return None
    return {
        "record": run,
        "profile_snapshot": json.loads(run.profile_snapshot_json),
        "selves": json.loads(run.result_json),
    }


@main_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("home.html")


@main_bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    prof = _get_profile()
    if request.method == "POST":
        prof.introversion = int(request.form.get("introversion", prof.introversion))
        prof.boldness = int(request.form.get("boldness", prof.boldness))
        prof.creativity = int(request.form.get("creativity", prof.creativity))
        prof.sleep_hours = int(request.form.get("sleep_hours", prof.sleep_hours))
        prof.work_hours = int(request.form.get("work_hours", prof.work_hours))
        db.session.commit()
        flash("Profile saved. Generate your first AI simulation.", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("onboarding.html", prof=prof)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    prof = _get_profile()
    latest_run_record = (
        SimulationRun.query.filter_by(user_id=current_user.id).order_by(SimulationRun.created_at.desc()).first()
    )
    latest_run = _parse_run(latest_run_record)
    recent_entries = (
        JournalEntry.query.filter_by(user_id=current_user.id)
        .order_by(JournalEntry.created_at.desc())
        .limit(10)
        .all()
    )
    ai = dashboard_snapshot(prof, latest_run, recent_entries)
    return render_template("dashboard.html", prof=prof, latest_run=latest_run_record, ai=ai)


@main_bp.route("/simulate", methods=["POST"])
@login_required
def simulate():
    prof = _get_profile()

    prof.introversion = int(request.form.get("introversion", prof.introversion))
    prof.boldness = int(request.form.get("boldness", prof.boldness))
    prof.creativity = int(request.form.get("creativity", prof.creativity))
    prof.sleep_hours = int(request.form.get("sleep_hours", prof.sleep_hours))
    prof.work_hours = int(request.form.get("work_hours", prof.work_hours))
    db.session.commit()

    profile_obj = Profile(
        introversion=prof.introversion,
        boldness=prof.boldness,
        creativity=prof.creativity,
        sleep_hours=prof.sleep_hours,
        work_hours=prof.work_hours,
    )

    selves = generate_parallel_selves(profile_obj, seed=prof.id * 100 + current_user.id)
    run = SimulationRun(
        user_id=current_user.id,
        profile_snapshot_json=json.dumps(profile_to_dict(profile_obj)),
        result_json=json.dumps(selves),
    )
    db.session.add(run)
    db.session.commit()

    flash("Advanced simulation generated successfully.", "success")
    return redirect(url_for("main.run_detail", run_id=run.id))


@main_bp.route("/runs")
@login_required
def runs():
    runs = SimulationRun.query.filter_by(user_id=current_user.id).order_by(SimulationRun.created_at.desc()).all()
    run_cards = []
    for run in runs:
        parsed = _parse_run(run)
        analysis = analyze_run(parsed["profile_snapshot"], parsed["selves"])
        run_cards.append({"record": run, "analysis": analysis})
    return render_template("runs.html", run_cards=run_cards)


@main_bp.route("/runs/<int:run_id>")
@login_required
def run_detail(run_id):
    run = SimulationRun.query.filter_by(id=run_id, user_id=current_user.id).first_or_404()
    parsed = _parse_run(run)
    analysis = analyze_run(parsed["profile_snapshot"], parsed["selves"])
    return render_template(
        "run_detail.html",
        run=run,
        profile_snapshot=parsed["profile_snapshot"],
        selves=parsed["selves"],
        analysis=analysis,
    )


@main_bp.route("/runs/<int:run_id>/delete", methods=["POST"])
@login_required
def delete_run(run_id: int):
    run = SimulationRun.query.filter_by(id=run_id, user_id=current_user.id).first_or_404()
    db.session.delete(run)
    db.session.commit()
    flash("Simulation run deleted.", "info")
    return redirect(url_for("main.runs"))


@main_bp.route("/runs/<int:run_id>/report.pdf")
@login_required
def export_pdf(run_id: int):
    run = SimulationRun.query.filter_by(id=run_id, user_id=current_user.id).first_or_404()
    parsed = _parse_run(run)
    profile_snapshot = parsed["profile_snapshot"]
    selves = parsed["selves"]
    analysis = analyze_run(profile_snapshot, selves)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 60

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Parallel Self AI Simulation Report")

    y -= 24
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Run ID: {run.id}")
    y -= 14
    c.drawString(50, y, f"User: {current_user.full_name} ({current_user.email})")
    y -= 14
    c.drawString(50, y, f"Generated: {run.created_at.strftime('%Y-%m-%d %H:%M')}")
    y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Profile Snapshot")
    y -= 16
    c.setFont("Helvetica", 10)
    for key in ["introversion", "boldness", "creativity", "sleep_hours", "work_hours"]:
        c.drawString(60, y, f"{key.replace('_', ' ').title()}: {profile_snapshot[key]}")
        y -= 12

    y -= 12
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "AI Coach Summary")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(60, y, analysis["coach_summary"][:95])
    y -= 18

    for row in analysis["matrix"]:
        if y < 100:
            c.showPage()
            y = height - 60
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, row["label"])
        y -= 13
        c.setFont("Helvetica", 10)
        c.drawString(60, y, f"{row['value']} (score: {row['score']:.1f})")
        y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Recommendations")
    y -= 16
    c.setFont("Helvetica", 10)
    for note in analysis["recommendations"][:5]:
        if y < 80:
            c.showPage()
            y = height - 60
        c.drawString(60, y, f"- {note[:100]}")
        y -= 14

    c.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"parallel_self_report_run_{run.id}.pdf",
        mimetype="application/pdf",
    )


@main_bp.route("/compare/<int:run_id>")
@login_required
def compare_selves(run_id: int):
    run = SimulationRun.query.filter_by(id=run_id, user_id=current_user.id).first_or_404()
    parsed = _parse_run(run)
    analysis = analyze_run(parsed["profile_snapshot"], parsed["selves"])
    return render_template(
        "compare.html",
        run=run,
        profile_snapshot=parsed["profile_snapshot"],
        selves_json=json.dumps(parsed["selves"]),
        selves=parsed["selves"],
        analysis=analysis,
    )


@main_bp.route("/journal", methods=["GET", "POST"])
@login_required
def journal():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        mood = request.form.get("mood", "neutral").strip()

        if not title or not content:
            flash("Title and content are required.", "danger")
            return redirect(url_for("main.journal"))

        entry = JournalEntry(user_id=current_user.id, title=title, content=content, mood=mood)
        db.session.add(entry)
        db.session.commit()
        flash("Journal entry saved.", "success")
        return redirect(url_for("main.journal"))

    q = request.args.get("q", "").strip()
    mood = request.args.get("mood", "").strip()

    entries_q = JournalEntry.query.filter_by(user_id=current_user.id)
    if q:
        entries_q = entries_q.filter(JournalEntry.title.ilike(f"%{q}%") | JournalEntry.content.ilike(f"%{q}%"))
    if mood:
        entries_q = entries_q.filter_by(mood=mood)

    entries = entries_q.order_by(JournalEntry.created_at.desc()).all()
    all_entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.created_at.desc()).all()
    moods = ["neutral", "happy", "sad", "stressed", "motivated", "tired"]
    journal_ai = journal_intelligence(all_entries)
    return render_template("journal.html", entries=entries, q=q, mood=mood, moods=moods, journal_ai=journal_ai)


@main_bp.route("/journal/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_journal(entry_id: int):
    entry = JournalEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    flash("Journal entry deleted.", "info")
    return redirect(url_for("main.journal"))


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    prof = _get_profile()
    if request.method == "POST":
        prof.introversion = int(request.form.get("introversion", prof.introversion))
        prof.boldness = int(request.form.get("boldness", prof.boldness))
        prof.creativity = int(request.form.get("creativity", prof.creativity))
        prof.sleep_hours = int(request.form.get("sleep_hours", prof.sleep_hours))
        prof.work_hours = int(request.form.get("work_hours", prof.work_hours))
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("main.profile"))
    ai = dashboard_snapshot(prof, None, JournalEntry.query.filter_by(user_id=current_user.id).all())
    return render_template("profile.html", prof=prof, ai=ai)
