"""Database models for the teleprompter application."""
from __future__ import annotations

from datetime import datetime
from secrets import token_urlsafe

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


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

    scripts: Mapped[list[Script]] = relationship("Script", back_populates="owner", lazy="dynamic")

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
        }


class Script(db.Model):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    content: Mapped[str] = mapped_column(db.Text, nullable=False)
    owner_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), nullable=False, index=True)
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
    control_session: Mapped[RemoteControlSession | None] = relationship(
        "RemoteControlSession", back_populates="script", uselist=False
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "owner_id": self.owner_id,
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


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))
