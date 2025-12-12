"""Routes for rendering teleprompter view."""
from __future__ import annotations

from flask import abort, current_app, render_template
from flask_login import current_user, login_required

from ..models import Script
from ..organizations.utils import get_active_organization
from . import prompter_bp


def _ensure_access(script: Script) -> None:
    if not current_user.can_access_script(script):
        abort(404)

    active_org = get_active_organization()
    if active_org:
        if script.organization_id != active_org.id:
            abort(404)
    elif script.organization_id is not None:
        abort(404)


@prompter_bp.route("/prompter/<int:script_id>")
@login_required
def view(script_id: int):
    script = Script.query.get_or_404(script_id)
    _ensure_access(script)

    return render_template(
        "prompter/view.html",
        script=script,
        default_speed=current_app.config["DEFAULT_SCROLL_SPEED"],
        default_theme=current_app.config["DEFAULT_THEME"],
        control_token=script.control_session.control_token if script.control_session else None,
    )
