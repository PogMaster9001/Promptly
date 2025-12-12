"""Remote control blueprint."""
from flask import Blueprint


control_bp = Blueprint("control", __name__, template_folder="../templates/control")

from . import routes  # noqa: E402
