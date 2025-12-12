"""User settings routes for appearance and integrations."""
from __future__ import annotations

import os

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import NextcloudSettingsForm, ThemeSettingsForm
from ..models import UserIntegration
from . import settings_bp


def _active_theme() -> str:
    configured = current_user.theme_preference or current_app.config.get("DEFAULT_THEME", "light")
    normalized = (configured or "light").lower()
    return normalized if normalized in {"light", "dark", "system"} else "light"


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def index():
    theme_form = ThemeSettingsForm()
    nextcloud_form = NextcloudSettingsForm()

    if request.method == "GET":
        theme_form.theme.data = _active_theme()
        nextcloud_form.base_url.data = current_user.nextcloud_base_url or ""
        nextcloud_form.username.data = current_user.nextcloud_username or ""
    else:
        if "theme_submit" in request.form and theme_form.validate():
            chosen = (theme_form.theme.data or "light").lower()
            if chosen not in {"light", "dark", "system"}:
                chosen = "light"
            current_user.theme_preference = chosen
            db.session.commit()
            flash("Appearance preferences updated.", "success")
            return redirect(url_for("settings.index"))

        if "nextcloud_disconnect" in request.form:
            current_user.nextcloud_base_url = None
            current_user.nextcloud_username = None
            current_user.nextcloud_app_password = None
            db.session.commit()
            flash("Nextcloud integration removed.", "info")
            return redirect(url_for("settings.index"))

        if "nextcloud_submit" in request.form and nextcloud_form.validate():
            current_user.nextcloud_base_url = (nextcloud_form.base_url.data or '').strip() or None
            current_user.nextcloud_username = (nextcloud_form.username.data or '').strip() or None
            if nextcloud_form.app_password.data:
                current_user.nextcloud_app_password = nextcloud_form.app_password.data
            elif not current_user.nextcloud_base_url or not current_user.nextcloud_username:
                current_user.nextcloud_app_password = None
            db.session.commit()
            flash("Nextcloud settings saved.", "success")
            return redirect(url_for("settings.index"))

    drive_integration = current_user.get_integration("google_drive")
    integrations = {
        "google_drive": {
            "connected": bool(drive_integration),
            "expires_at": getattr(drive_integration, "expires_at", None),
        },
        "nextcloud": {
            "connected": bool(
                current_user.nextcloud_base_url
                and current_user.nextcloud_username
                and current_user.nextcloud_app_password
            )
        },
    }

    return render_template(
        "settings/index.html",
        theme_form=theme_form,
        nextcloud_form=nextcloud_form,
        integrations=integrations,
    )


@settings_bp.route("/settings/integrations/google/start")
@login_required
def google_drive_start():
    try:
        from google_auth_oauthlib.flow import Flow
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency issue
        current_app.logger.exception("Google OAuth libraries missing: %s", exc)
        flash("Google OAuth libraries are not installed.", "danger")
        return redirect(url_for("settings.index"))

    secrets_path = current_app.config.get("GOOGLE_CLIENT_SECRETS_FILE")
    if not secrets_path or not os.path.exists(secrets_path):
        flash("Google client secrets file is not configured.", "danger")
        return redirect(url_for("settings.index"))

    flow = Flow.from_client_secrets_file(
        secrets_path,
        scopes=current_app.config.get("GOOGLE_DRIVE_SCOPES", []),
        redirect_uri=url_for("settings.google_drive_callback", _external=True),
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["google_oauth_state"] = state
    return redirect(authorization_url)


@settings_bp.route("/settings/integrations/google/callback")
@login_required
def google_drive_callback():
    try:
        from google_auth_oauthlib.flow import Flow
    except ModuleNotFoundError as exc:  # pragma: no cover
        current_app.logger.exception("Google OAuth libraries missing: %s", exc)
        flash("Google OAuth libraries are not installed.", "danger")
        return redirect(url_for("settings.index"))

    state = session.pop("google_oauth_state", None)
    if not state or state != request.args.get("state"):
        flash("OAuth state mismatch. Please try again.", "danger")
        return redirect(url_for("settings.index"))

    secrets_path = current_app.config.get("GOOGLE_CLIENT_SECRETS_FILE")
    if not secrets_path or not os.path.exists(secrets_path):
        flash("Google client secrets file is not configured.", "danger")
        return redirect(url_for("settings.index"))

    flow = Flow.from_client_secrets_file(
        secrets_path,
        scopes=current_app.config.get("GOOGLE_DRIVE_SCOPES", []),
        state=state,
        redirect_uri=url_for("settings.google_drive_callback", _external=True),
    )
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Failed to fetch Google OAuth token: %s", exc)
        flash("Unable to complete Google Drive authorization.", "danger")
        return redirect(url_for("settings.index"))

    credentials = flow.credentials
    integration = current_user.get_integration("google_drive")
    if not integration:
        integration = UserIntegration(user_id=current_user.id, provider="google_drive")
        db.session.add(integration)

    integration.update_from_credentials(credentials)
    db.session.commit()

    flash("Google Drive connected successfully.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/settings/integrations/google/disconnect", methods=["POST"])
@login_required
def google_drive_disconnect():
    integration = current_user.get_integration("google_drive")
    if integration:
        db.session.delete(integration)
        db.session.commit()
        flash("Google Drive disconnected.", "info")
    else:
        flash("Google Drive was not connected.", "info")
    return redirect(url_for("settings.index"))
