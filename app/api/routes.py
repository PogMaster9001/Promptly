"""REST endpoints exposed by the application."""
from __future__ import annotations

from flask import abort, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Script
from . import api_bp


def _get_owned_script(script_id: int) -> Script:
    script = Script.query.get_or_404(script_id)
    if script.owner_id != current_user.id:
        abort(403)
    return script


@api_bp.get("/scripts/<int:script_id>")
@login_required
def get_script(script_id: int):
    script = _get_owned_script(script_id)
    return jsonify(script.to_dict())


@api_bp.patch("/scripts/<int:script_id>")
@login_required
def update_script(script_id: int):
    script = _get_owned_script(script_id)
    payload = request.get_json(silent=True) or {}

    if "scroll_speed" in payload:
        script.scroll_speed = float(payload["scroll_speed"])
    if "theme" in payload:
        script.theme = payload["theme"]
    if "content" in payload:
        script.content = payload["content"]

    db.session.commit()

    return jsonify(script.to_dict())
