from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, User, PersonalityProfile

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _valid_password(pw: str) -> bool:
    return (
        len(pw) >= 8
        and any(c.isdigit() for c in pw)
        and any(c.isalpha() for c in pw)
        and any(not c.isalnum() for c in pw)
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not full_name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        if not _valid_password(password):
            flash("Password must be at least 8 characters and include letters, numbers, and a special character.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("Email is already registered. Please login.", "warning")
            return redirect(url_for("auth.login"))

        first_user = User.query.count() == 0
        user = User(full_name=full_name, email=email, is_admin=first_user)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        profile = PersonalityProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

        login_user(user)
        flash("Account created successfully.", "success")
        return redirect(url_for("main.onboarding"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    next_url = request.args.get("next")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        next_url = request.form.get("next") or next_url

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", next_url=next_url)

        login_user(user, remember=True)
        flash("Welcome back.", "success")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", next_url=next_url)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
