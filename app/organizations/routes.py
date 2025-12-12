"""Views for managing organizations and memberships."""
from __future__ import annotations

from typing import Tuple

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import OrganizationCreateForm, OrganizationInviteForm, OrganizationJoinForm
from ..models import Organization, OrganizationInvite, OrgMembership
from . import organizations_bp
from .utils import get_active_organization, set_active_organization


def _get_membership_or_403(org_id: int) -> Tuple[Organization, OrgMembership]:
    organization = db.session.get(Organization, org_id)
    if not organization:
        abort(404)

    membership = current_user.get_membership(organization)
    if not membership:
        abort(403)

    return organization, membership


@organizations_bp.route("/organizations", methods=["GET", "POST"])
@login_required
def index():
    active_org = get_active_organization()
    create_form = OrganizationCreateForm(prefix="create")
    join_form = OrganizationJoinForm(prefix="join")
    invite_form = OrganizationInviteForm(prefix="invite")

    if create_form.create_submit.data and create_form.validate_on_submit():
        name = create_form.name.data.strip()
        slug_base = Organization.generate_slug(name)
        slug = slug_base
        counter = 1
        while Organization.query.filter_by(slug=slug).first():
            slug = f"{slug_base}-{counter}"
            counter += 1

        organization = Organization(name=name, slug=slug, created_by=current_user)
        db.session.add(organization)
        db.session.flush()

        membership = OrgMembership(organization_id=organization.id, user_id=current_user.id, role="admin")
        db.session.add(membership)
        db.session.commit()

        set_active_organization(organization)
        flash("Organization created. You're the admin!", "success")
        return redirect(url_for("organizations.index"))

    if join_form.join_submit.data and join_form.validate_on_submit():
        code = join_form.code.data.strip()
        invite = OrganizationInvite.query.filter_by(code=code).first()
        if not invite or not invite.is_valid():
            flash("That invite code is no longer valid.", "danger")
        else:
            existing = current_user.get_membership(invite.organization_id)
            if existing:
                set_active_organization(invite.organization_id)
                flash("You're already a member of that organization.", "info")
                return redirect(url_for("organizations.index"))

            membership = OrgMembership(
                organization_id=invite.organization_id,
                user_id=current_user.id,
                role=invite.role,
            )
            db.session.add(membership)
            db.session.commit()

            set_active_organization(invite.organization_id)
            flash("Joined organization successfully.", "success")
            return redirect(url_for("dashboard.index"))

    memberships = sorted(current_user.memberships, key=lambda m: m.organization.name.lower())
    active_invites = []
    if active_org and current_user.is_org_admin(active_org):
        active_invites = [invite for invite in active_org.invites if invite.is_valid()]

    return render_template(
        "organizations/index.html",
        memberships=memberships,
        create_form=create_form,
        join_form=join_form,
        invite_form=invite_form,
        active_org=active_org,
        active_invites=active_invites,
    )


@organizations_bp.route("/organizations/<int:org_id>/switch", methods=["GET", "POST"])
@login_required
def switch(org_id: int):
    organization, _ = _get_membership_or_403(org_id)
    set_active_organization(organization)
    flash(f"Switched to {organization.name}.", "success")
    next_url = request.args.get("next") or url_for("dashboard.index")
    return redirect(next_url)


@organizations_bp.route("/organizations/personal", methods=["POST"])
@login_required
def switch_personal():
    set_active_organization(None)
    flash("Switched to your personal workspace.", "success")
    next_url = request.args.get("next") or url_for("dashboard.index")
    return redirect(next_url)


@organizations_bp.route("/organizations/<int:org_id>/invites", methods=["POST"])
@login_required
def create_invite(org_id: int):
    organization, membership = _get_membership_or_403(org_id)
    if not membership.is_admin():
        abort(403)

    invite_form = OrganizationInviteForm(prefix="invite")
    if invite_form.validate_on_submit():
        invite = OrganizationInvite(
            organization_id=organization.id,
            code=OrganizationInvite.issue_code(),
            role=invite_form.role.data,
            created_by=current_user,
        )
        db.session.add(invite)
        db.session.commit()
        flash("Invite code generated.", "success")
    else:
        flash("Unable to generate invite. Check the form inputs.", "danger")

    return redirect(url_for("organizations.index"))


@organizations_bp.route("/organizations/<int:org_id>/invites/<int:invite_id>/revoke", methods=["POST"])
@login_required
def revoke_invite(org_id: int, invite_id: int):
    organization, membership = _get_membership_or_403(org_id)
    if not membership.is_admin():
        abort(403)

    invite = OrganizationInvite.query.filter_by(id=invite_id, organization_id=organization.id).first()
    if not invite:
        abort(404)

    invite.is_active = False
    db.session.commit()
    flash("Invite revoked.", "info")
    return redirect(url_for("organizations.index"))
