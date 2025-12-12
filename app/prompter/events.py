"""Socket.IO events to sync teleprompter and remote control."""
from __future__ import annotations

from flask import current_app
from flask_socketio import emit, join_room, leave_room

from ..extensions import db, socketio
from ..models import RemoteControlSession

ROOM_PREFIX = "script:"


def _room_for_token(token: str) -> str | None:
    session = RemoteControlSession.query.filter_by(control_token=token, is_active=True).first()
    if not session:
        return None
    return f"{ROOM_PREFIX}{session.script_id}"


@socketio.on("join", namespace="/control")
def control_join(data: dict[str, str | int]) -> None:
    token = str(data.get("token", ""))
    room = _room_for_token(token)
    if not room:
        emit("error", {"message": "Invalid or expired control token."})
        return

    join_room(room)
    emit("joined", {"room": room})
    current_app.logger.debug("Client joined room %s", room)


@socketio.on("leave", namespace="/control")
def control_leave(data: dict[str, str]) -> None:
    token = str(data.get("token", ""))
    room = _room_for_token(token)
    if not room:
        emit("error", {"message": "Invalid control token."})
        return

    leave_room(room)
    emit("left", {"room": room})


@socketio.on("control:update", namespace="/control")
def control_update(data: dict[str, object]) -> None:
    token = str(data.get("token", ""))
    room = _room_for_token(token)
    if not room:
        emit("error", {"message": "Invalid control token."})
        return

    payload = {
        "action": data.get("action"),
        "value": data.get("value"),
    }
    emit("teleprompter:update", payload, room=room, include_self=False)


@socketio.on("control:end", namespace="/control")
def control_end(data: dict[str, str]) -> None:
    token = str(data.get("token", ""))
    session = RemoteControlSession.query.filter_by(control_token=token, is_active=True).first()
    if not session:
        emit("error", {"message": "Invalid control token."})
        return

    session.is_active = False
    db.session.commit()
    room = f"{ROOM_PREFIX}{session.script_id}"
    emit("teleprompter:end", room=room)
    current_app.logger.info("Remote session %s ended", session.id)
