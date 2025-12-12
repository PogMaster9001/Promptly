"""Routes for rendering teleprompter view."""
from __future__ import annotations

from flask import abort, current_app, render_template
from flask_login import current_user, login_required

from ..models import Script
from . import prompter_bp


def _ensure_access(script: Script) -> None:
    if script.owner_id != current_user.id and not script.is_shared:
        abort(403)


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
