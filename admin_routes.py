from collections import Counter
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from . import db
from .auth_routes import _valid_password
from .insights import analyze_run, classify_archetype
from .models import ChatMessage, JournalEntry, PersonalityProfile, SimulationRun, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not getattr(current_user, "is_admin", False):
            flash("Admin access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return func(*args, **kwargs)

    return wrapper


@admin_bp.route("/")
@login_required
@admin_required
def index():
    users = User.query.order_by(User.created_at.desc()).all()
    runs_count = SimulationRun.query.count()
    journal_count = JournalEntry.query.count()
    chat_count = ChatMessage.query.count()

    summaries = []
    for user in users:
        profile = PersonalityProfile.query.filter_by(user_id=user.id).first()
        latest_run = SimulationRun.query.filter_by(user_id=user.id).order_by(SimulationRun.created_at.desc()).first()
        run_count = SimulationRun.query.filter_by(user_id=user.id).count()
        journal_total = JournalEntry.query.filter_by(user_id=user.id).count()
        chat_total = ChatMessage.query.filter_by(user_id=user.id).count()

        risk = None
        if latest_run:
            import json

            analysis = analyze_run(json.loads(latest_run.profile_snapshot_json), json.loads(latest_run.result_json))
            risk = round(analysis["highest_risk"]["burnout_risk"], 1)
        elif profile:
            risk = max(0, (profile.work_hours - 7) * 10 + max(0, 6 - profile.sleep_hours) * 12)

        summaries.append(
            {
                "user": user,
                "run_count": run_count,
                "journal_total": journal_total,
                "chat_total": chat_total,
                "archetype": classify_archetype(
                    {
                        "introversion": profile.introversion if profile else 50,
                        "boldness": profile.boldness if profile else 50,
                        "creativity": profile.creativity if profile else 50,
                        "sleep_hours": profile.sleep_hours if profile else 7,
                        "work_hours": profile.work_hours if profile else 6,
                    }
                ),
                "risk": round(risk, 1) if risk is not None else None,
            }
        )

    return render_template(
        "admin/index.html",
        users=users,
        runs_count=runs_count,
        journal_count=journal_count,
        chat_count=chat_count,
        summaries=summaries,
    )


@admin_bp.route("/toggle-admin/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def toggle_admin(user_id: int):
    if current_user.id == user_id:
        flash("You can't change your own admin status here.", "warning")
        return redirect(url_for("admin.index"))
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f"Updated admin status for {user.email}.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/delete-user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id: int):
    if current_user.id == user_id:
        flash("You can't delete your own account from admin.", "warning")
        return redirect(url_for("admin.index"))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "info")
    return redirect(url_for("admin.index"))


@admin_bp.route("/password", methods=["POST"])
@login_required
@admin_required
def change_admin_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_user.check_password(current_password):
        flash("Current admin password is incorrect.", "danger")
        return redirect(url_for("admin.index"))
    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("admin.index"))
    if not _valid_password(new_password):
        flash("Admin password must be at least 8 characters and include letters, numbers, and a special character.", "danger")
        return redirect(url_for("admin.index"))

    current_user.set_password(new_password)
    db.session.commit()
    flash("Admin password updated successfully.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/reset-password/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def reset_user_password(user_id: int):
    if current_user.id == user_id:
        flash("Use the admin password form to change your own password.", "warning")
        return redirect(url_for("admin.index"))
    new_password = request.form.get("new_password", "")
    if not _valid_password(new_password):
        flash("New user password must be at least 8 characters and include letters, numbers, and a special character.", "danger")
        return redirect(url_for("admin.index"))
    user = User.query.get_or_404(user_id)
    user.set_password(new_password)
    db.session.commit()
    flash(f"Password reset for {user.email}.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/analytics")
@login_required
@admin_required
def analytics():
    runs_data = (
        db.session.query(func.date(SimulationRun.created_at), func.count())
        .group_by(func.date(SimulationRun.created_at))
        .order_by(func.date(SimulationRun.created_at))
        .all()
    )
    labels = [str(row[0]) for row in runs_data]
    values = [row[1] for row in runs_data]

    active_users = db.session.query(func.count(func.distinct(SimulationRun.user_id))).scalar() or 0
    users_count = User.query.count()
    runs_count = SimulationRun.query.count()
    journals_count = JournalEntry.query.count()
    chat_count = ChatMessage.query.count()

    mood_rows = db.session.query(JournalEntry.mood, func.count()).group_by(JournalEntry.mood).all()
    mood_labels = [row[0].title() for row in mood_rows]
    mood_values = [row[1] for row in mood_rows]

    archetypes = Counter()
    risk_users = []
    for profile in PersonalityProfile.query.all():
        archetype = classify_archetype(
            {
                "introversion": profile.introversion,
                "boldness": profile.boldness,
                "creativity": profile.creativity,
                "sleep_hours": profile.sleep_hours,
                "work_hours": profile.work_hours,
            }
        )
        archetypes[archetype] += 1
        risk_score = max(0, (profile.work_hours - 7) * 10 + max(0, 6 - profile.sleep_hours) * 12)
        if risk_score >= 15:
            risk_users.append(profile.user.full_name)

    archetype_labels = list(archetypes.keys())
    archetype_values = list(archetypes.values())

    return render_template(
        "admin/analytics.html",
        labels=labels,
        values=values,
        active_users=active_users,
        users_count=users_count,
        runs_count=runs_count,
        journals_count=journals_count,
        chat_count=chat_count,
        avg_chat_per_user=round(chat_count / users_count, 1) if users_count else 0,
        mood_labels=mood_labels,
        mood_values=mood_values,
        archetype_labels=archetype_labels,
        archetype_values=archetype_values,
        at_risk_count=len(risk_users),
        avg_runs_per_user=round(runs_count / users_count, 1) if users_count else 0,
    )
