"""Remote control routes accessible via token."""
from __future__ import annotations

from flask import abort, render_template

from ..models import RemoteControlSession
from . import control_bp


@control_bp.route("/control/<string:token>")
def remote(token: str):
    session = RemoteControlSession.query.filter_by(control_token=token, is_active=True).first()
    if not session:
        abort(404)

    return render_template("control/index.html", token=token, script=session.script)
