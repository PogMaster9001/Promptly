"""Application factory for the teleprompter SaaS platform."""
from flask import Flask
from flask_wtf.csrf import generate_csrf
from .config import get_config
from .extensions import csrf, db, login_manager, migrate, socketio


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


def register_blueprints(app: Flask) -> None:
    """Register application blueprints."""
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    from .prompter.routes import prompter_bp
    from .control.routes import control_bp
    from .api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(prompter_bp)
    app.register_blueprint(control_bp)
    app.register_blueprint(api_bp, url_prefix="/api")


def register_cli(app: Flask) -> None:
    """Add helpful CLI commands."""
    from .models import Script, User

    @app.shell_context_processor
    def shell_context() -> dict[str, object]:
        return {"db": db, "User": User, "Script": Script}


def register_template_filters(app: Flask) -> None:
    """Register custom Jinja filters used in templates."""
    from .markup import render_script

    app.jinja_env.filters["teleprompter_markup"] = render_script
