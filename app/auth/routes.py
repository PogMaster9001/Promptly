"""Authentication related routes."""
from __future__ import annotations

from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..forms import LoginForm, RegistrationForm
from ..models import User
from . import auth_bp


@auth_bp.route("/auth/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_url = request.args.get("next")
            if next_url and urlparse(next_url).netloc:
                next_url = None
            return redirect(next_url or url_for("dashboard.index"))

        flash("Invalid email or password", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/auth/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/auth/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated and not current_user.is_admin:
        return redirect(url_for("dashboard.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("That email is already registered.", "warning")
        else:
            user = User(
                email=form.email.data.lower(),
                name=form.name.data,
                organization=form.organization.data or None,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Account created. You can sign in now.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)
