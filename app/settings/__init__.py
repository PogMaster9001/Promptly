"""User settings blueprint."""
from flask import Blueprint


settings_bp = Blueprint("settings", __name__, template_folder="../templates/settings")

from . import routes  # noqa: E402
