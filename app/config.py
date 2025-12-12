"""Application configuration for different environments."""
from __future__ import annotations

import os
from typing import Type


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///teleprompter.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")
    GOOGLE_CLIENT_SECRETS_FILE = os.getenv(
        "GOOGLE_CLIENT_SECRETS_FILE", "instance/google_client_secrets.json"
    )
    GOOGLE_DRIVE_SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/documents.readonly",
    ]
    NEXTCLOUD_BASE_URL = os.getenv("NEXTCLOUD_BASE_URL", "")
    NEXTCLOUD_USERNAME = os.getenv("NEXTCLOUD_USERNAME", "")
    NEXTCLOUD_APP_PASSWORD = os.getenv("NEXTCLOUD_APP_PASSWORD", "")
    SCRIPT_POLL_INTERVAL = int(os.getenv("SCRIPT_POLL_INTERVAL", "30"))
    DEFAULT_SCROLL_SPEED = float(os.getenv("DEFAULT_SCROLL_SPEED", "1.0"))
    DEFAULT_THEME = os.getenv("DEFAULT_THEME", "light")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_DURATION = int(os.getenv("REMEMBER_COOKIE_DURATION", 1209600))


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SESSION_COOKIE_SECURE = False


_CONFIG_LOOKUP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    None: DevelopmentConfig,
}


def get_config(name: str | None) -> Type[BaseConfig]:
    """Return the configuration class for a given name."""
    normalized = (name or os.getenv("FLASK_ENV", "development")).lower()
    return _CONFIG_LOOKUP.get(normalized, DevelopmentConfig)
