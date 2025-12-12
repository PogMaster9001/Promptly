"""Helpers for working with the active organization context."""
from __future__ import annotations

from typing import Optional

from flask import session
from flask_login import current_user

from ..extensions import db
from ..models import Organization


def get_active_organization() -> Optional[Organization]:
    if not current_user.is_authenticated:
        return None

    org_id = session.get("active_org_id")
    if not org_id:
        return None

    organization = db.session.get(Organization, org_id)
    if not organization:
        session.pop("active_org_id", None)
        return None

    if not current_user.get_membership(organization):
        session.pop("active_org_id", None)
        return None

    return organization


def set_active_organization(organization: Organization | int | None) -> None:
    if organization is None:
        session.pop("active_org_id", None)
        return

    org_id = organization if isinstance(organization, int) else organization.id
    session["active_org_id"] = org_id
