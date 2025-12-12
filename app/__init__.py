"""Application factory for the teleprompter SaaS platform."""
from flask import Flask
from flask_login import current_user
from flask_wtf.csrf import generate_csrf
from .config import get_config
from .extensions import csrf, db, login_manager, migrate, socketio
from .organizations.utils import get_active_organization


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    config_obj = get_config(config_name)
    app.config.from_object(config_obj)

    register_extensions(app)
    register_blueprints(app)
    register_template_filters(app)
    register_cli(app)

    return app


def register_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins=app.config.get("CORS_ALLOWED_ORIGINS"))

    login_manager.login_view = "auth.login"
    login_manager.session_protection = "strong"

    @app.context_processor
    def inject_csrf_token() -> dict[str, object]:
        return {"csrf_token": generate_csrf}

    @app.context_processor
    def inject_theme_and_org() -> dict[str, object]:
        configured = app.config.get("DEFAULT_THEME", "light")
        if current_user.is_authenticated:
            configured = getattr(current_user, "theme_preference", configured) or configured
        normalized = (configured or "light").lower()
        if normalized not in {"light", "dark", "system"}:
            normalized = "light"
        active_org = get_active_organization() if current_user.is_authenticated else None
        return {"active_theme": normalized, "active_organization": active_org}


def register_blueprints(app: Flask) -> None:
    """Register application blueprints."""
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    from .prompter.routes import prompter_bp
    from .control.routes import control_bp
    from .organizations import organizations_bp
    from .settings.routes import settings_bp
    from .api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(prompter_bp)
    app.register_blueprint(control_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp, url_prefix="/api")


def register_cli(app: Flask) -> None:
    """Add helpful CLI commands."""
    from .models import (
        Organization,
        OrganizationInvite,
        OrgMembership,
        Script,
        User,
        UserIntegration,
    )

    @app.shell_context_processor
    def shell_context() -> dict[str, object]:
        return {
            "db": db,
            "User": User,
            "Script": Script,
            "UserIntegration": UserIntegration,
            "Organization": Organization,
            "OrgMembership": OrgMembership,
            "OrganizationInvite": OrganizationInvite,
        }


def register_template_filters(app: Flask) -> None:
    """Register custom Jinja filters used in templates."""
    from .markup import render_script

    app.jinja_env.filters["teleprompter_markup"] = render_script
