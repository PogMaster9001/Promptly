"""Teleprompter blueprint."""
from flask import Blueprint


prompter_bp = Blueprint("prompter", __name__, template_folder="../templates/prompter")

from . import routes  # noqa: E402
from . import events  # noqa: E402
