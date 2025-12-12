"""Organization management blueprint."""
from flask import Blueprint


organizations_bp = Blueprint("organizations", __name__, template_folder="../templates/organizations")

from . import routes  # noqa: E402
