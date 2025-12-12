"""Database models for the teleprompter application."""
from __future__ import annotations

from datetime import datetime
import json
import re
from secrets import token_urlsafe

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

_slugify_pattern = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    """Create a URL-friendly slug for organizations."""
    candidate = _slugify_pattern.sub("-", value.strip().lower()).strip("-")
    if not candidate:
        candidate = f"org-{token_urlsafe(4).lower()}"
    return candidate[:80]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(db.String(255), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(db.String(120))
    organization: Mapped[str | None] = mapped_column(db.String(255))
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    theme_preference: Mapped[str] = mapped_column(db.String(20), default="light", nullable=False)
    nextcloud_base_url: Mapped[str | None] = mapped_column(db.String(255))
    nextcloud_username: Mapped[str | None] = mapped_column(db.String(255))
    nextcloud_app_password: Mapped[str | None] = mapped_column(db.String(255))

    scripts: Mapped[list[Script]] = relationship("Script", back_populates="owner", lazy="dynamic")
    integrations: Mapped[list["UserIntegration"]] = relationship(
        "UserIntegration",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    memberships: Mapped[list["OrgMembership"]] = relationship(
        "OrgMembership",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    organizations_created: Mapped[list["Organization"]] = relationship(
        "Organization",
        back_populates="created_by",
        lazy="selectin",
    )
    invites_created: Mapped[list["OrganizationInvite"]] = relationship(
        "OrganizationInvite",
        back_populates="created_by",
        lazy="selectin",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "organization": self.organization,
            "is_admin": self.is_admin,
            "theme_preference": self.theme_preference,
        }

    def get_integration(self, provider: str) -> "UserIntegration | None":
        provider_lower = provider.lower()
        for integration in self.integrations:
            if integration.provider == provider_lower:
                return integration
        return None

    def get_membership(self, organization: "Organization | int | None") -> "OrgMembership | None":
        if organization is None:
            return None
        organization_id = organization if isinstance(organization, int) else organization.id
        for membership in self.memberships:
            if membership.organization_id == organization_id:
                return membership
        return None

    def is_org_admin(self, organization: "Organization | int | None") -> bool:
        membership = self.get_membership(organization)
        return bool(membership and membership.role == "admin")

    def organization_ids(self) -> set[int]:
        return {membership.organization_id for membership in self.memberships}

    def can_access_script(self, script: "Script") -> bool:
        if script.owner_id == self.id:
            return True
        if script.organization_id and script.organization_id in self.organization_ids():
            membership = self.get_membership(script.organization_id)
            return membership is not None
        return False


class Organization(db.Model):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(120), nullable=False)
    slug: Mapped[str] = mapped_column(db.String(120), unique=True, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    created_by: Mapped[User | None] = relationship("User", back_populates="organizations_created")
    memberships: Mapped[list["OrgMembership"]] = relationship(
        "OrgMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    invites: Mapped[list["OrganizationInvite"]] = relationship(
        "OrganizationInvite",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    scripts: Mapped[list["Script"]] = relationship("Script", back_populates="organization")

    @staticmethod
    def generate_slug(name: str) -> str:
        return _slugify(name)


class OrgMembership(db.Model):
    __tablename__ = "organization_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(db.ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(db.String(20), default="member", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    organization: Mapped[Organization] = relationship("Organization", back_populates="memberships")
    user: Mapped[User] = relationship("User", back_populates="memberships")

    __table_args__ = (db.UniqueConstraint("organization_id", "user_id", name="uq_membership"),)

    def is_admin(self) -> bool:
        return self.role == "admin"


class OrganizationInvite(db.Model):
    __tablename__ = "organization_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(db.ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(db.String(64), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(db.String(20), default="member", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(db.DateTime())

    organization: Mapped[Organization] = relationship("Organization", back_populates="invites")
    created_by: Mapped[User | None] = relationship("User", back_populates="invites_created")

    @staticmethod
    def issue_code() -> str:
        return token_urlsafe(8)

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


class Script(db.Model):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    content: Mapped[str] = mapped_column(db.Text, nullable=False)
    owner_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[int | None] = mapped_column(
        db.ForeignKey("organizations.id", ondelete="SET NULL"),
        index=True,
    )
    source: Mapped[str | None] = mapped_column(db.String(50))
    source_identifier: Mapped[str | None] = mapped_column(db.String(255))
    scroll_speed: Mapped[float] = mapped_column(db.Float, default=1.0, nullable=False)
    theme: Mapped[str] = mapped_column(db.String(50), default="light", nullable=False)
    is_shared: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    owner: Mapped[User] = relationship("User", back_populates="scripts")
    organization: Mapped[Organization | None] = relationship("Organization", back_populates="scripts")
    control_session: Mapped[RemoteControlSession | None] = relationship(
        "RemoteControlSession", back_populates="script", uselist=False
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "owner_id": self.owner_id,
            "organization_id": self.organization_id,
            "source": self.source,
            "source_identifier": self.source_identifier,
            "scroll_speed": self.scroll_speed,
            "theme": self.theme,
            "is_shared": self.is_shared,
            "updated_at": self.updated_at.isoformat(),
        }


class RemoteControlSession(db.Model):
    __tablename__ = "remote_control_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    script_id: Mapped[int] = mapped_column(db.ForeignKey("scripts.id"), nullable=False, unique=True)
    control_token: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    script: Mapped[Script] = relationship("Script", back_populates="control_session")

    @staticmethod
    def issue_token() -> str:
        return token_urlsafe(16)


class UserIntegration(db.Model):
    __tablename__ = "user_integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(db.String(64), nullable=False, index=True)
    credentials_json: Mapped[str | None] = mapped_column(db.Text)
    scopes: Mapped[str | None] = mapped_column(db.Text)
    expires_at: Mapped[datetime | None] = mapped_column(db.DateTime())
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="integrations")

    __table_args__ = (db.UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    def as_credentials(self):
        from google.oauth2.credentials import Credentials

        if not self.credentials_json:
            raise RuntimeError("OAuth credentials are missing for this integration.")
        data = json.loads(self.credentials_json)
        scopes = data.get("scopes") or self.scopes
        if isinstance(scopes, str):
            scope_list = scopes.split()
        else:
            scope_list = list(scopes) if scopes else None
        return Credentials.from_authorized_user_info(data, scopes=scope_list)

    def update_from_credentials(self, credentials) -> None:
        self.credentials_json = credentials.to_json()
        scopes = credentials.scopes
        if not scopes:
            data = json.loads(self.credentials_json)
            scopes = data.get("scopes")
        if isinstance(scopes, str):
            scope_list = scopes.split()
        else:
            scope_list = list(scopes) if scopes else None
        self.scopes = " ".join(scope_list) if scope_list else None
        self.expires_at = credentials.expiry
        self.updated_at = datetime.utcnow()


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))
