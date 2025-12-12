"""Routes for the main dashboard."""
from __future__ import annotations

from flask import abort, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import ImportScriptForm, ScriptForm
from ..models import RemoteControlSession, Script
from ..organizations.utils import get_active_organization
from ..services.google_drive import GoogleDriveService
from ..services.nextcloud import NextcloudService
from . import dashboard_bp


def _load_script(script_id: int, *, require_edit: bool = False) -> Script:
    script = Script.query.get_or_404(script_id)

    if not current_user.can_access_script(script):
        abort(404)

    active_org = get_active_organization()
    if active_org:
        if script.organization_id != active_org.id:
            abort(404)
    else:
        if script.organization_id is not None:
            abort(404)

    if require_edit and script.owner_id != current_user.id:
        if not script.organization_id or not current_user.is_org_admin(script.organization_id):
            abort(403)

    return script


def _update_script_settings(script: Script, form: ScriptForm) -> None:
    script.title = form.title.data
    script.content = form.content.data
    script.scroll_speed = float(form.scroll_speed.data or current_app.config["DEFAULT_SCROLL_SPEED"])
    script.theme = form.theme.data


@dashboard_bp.route("/")
@login_required
def index():
    active_org = get_active_organization()
    if active_org:
        scripts = (
            Script.query.filter_by(organization_id=active_org.id)
            .order_by(Script.updated_at.desc())
            .all()
        )
    else:
        scripts = (
            Script.query.filter_by(owner_id=current_user.id, organization_id=None)
            .order_by(Script.updated_at.desc())
            .all()
        )

    editable_script_ids = {
        script.id
        for script in scripts
        if script.owner_id == current_user.id
        or (script.organization_id and current_user.is_org_admin(script.organization_id))
    }

    return render_template(
        "dashboard/index.html",
        scripts=scripts,
        active_org=active_org,
        editable_script_ids=editable_script_ids,
    )


@dashboard_bp.route("/scripts/new", methods=["GET", "POST"])
@login_required
def create_script():
    form = ScriptForm()
    if not form.is_submitted():
        default_theme = current_user.theme_preference if current_user.is_authenticated else None
        default_theme = default_theme or current_app.config.get("DEFAULT_THEME", "light")
        if default_theme in dict(form.theme.choices):
            form.theme.data = default_theme
    if form.validate_on_submit():
        active_org = get_active_organization()
        script = Script(
            title=form.title.data,
            content=form.content.data,
            owner_id=current_user.id,
            organization_id=active_org.id if active_org else None,
            scroll_speed=float(form.scroll_speed.data or current_app.config["DEFAULT_SCROLL_SPEED"]),
            theme=form.theme.data,
        )
        db.session.add(script)
        db.session.commit()
        flash("Script created.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("dashboard/editor.html", form=form, script=None)


@dashboard_bp.route("/scripts/<int:script_id>/edit", methods=["GET", "POST"])
@login_required
def edit_script(script_id: int):
    script = _load_script(script_id, require_edit=True)
    form = ScriptForm(obj=script)
    if form.validate_on_submit():
        _update_script_settings(script, form)
        db.session.commit()
        flash("Script updated.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("dashboard/editor.html", form=form, script=script)


@dashboard_bp.route("/scripts/<int:script_id>/delete", methods=["POST"])
@login_required
def delete_script(script_id: int):
    script = _load_script(script_id, require_edit=True)
    db.session.delete(script)
    db.session.commit()
    flash("Script removed.", "info")
    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/scripts/import", methods=["GET", "POST"])
@login_required
def import_script():
    form = ImportScriptForm()
    if form.validate_on_submit():
        provider = form.provider.data
        resource_id = form.resource_id.data
        convert = form.convert_to_plaintext.data

        try:
            if provider == "google_drive":
                service = GoogleDriveService(current_user)
            else:
                service = NextcloudService(current_user)

            imported = service.fetch_script(resource_id, convert_to_plaintext=convert)
            active_org = get_active_organization()
            script = Script(
                title=imported.title,
                content=imported.content,
                owner_id=current_user.id,
                organization_id=active_org.id if active_org else None,
                source=provider,
                source_identifier=resource_id,
                scroll_speed=current_app.config["DEFAULT_SCROLL_SPEED"],
                theme=current_app.config["DEFAULT_THEME"],
            )
            db.session.add(script)
            db.session.commit()
            flash("Script imported successfully.", "success")
            return redirect(url_for("dashboard.index"))
        except Exception as exc:  # noqa: BLE001
            current_app.logger.exception("Import failed: %s", exc)
            flash("Unable to import script. Check provider settings.", "danger")

    return render_template("dashboard/import.html", form=form)


@dashboard_bp.route("/scripts/<int:script_id>/remote", methods=["POST"])
@login_required
def create_remote_session(script_id: int):
    script = _load_script(script_id, require_edit=True)
    if script.control_session and script.control_session.is_active:
        flash("Remote session already active.", "info")
        return redirect(url_for("dashboard.index"))

    token = RemoteControlSession.issue_token()
    session = RemoteControlSession(script_id=script.id, control_token=token)
    db.session.add(session)
    db.session.commit()
    flash("Remote control session created.", "success")
    return redirect(url_for("control.remote", token=token))
