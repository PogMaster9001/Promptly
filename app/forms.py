"""Flask-WTF forms used across the application."""
from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class RegistrationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    organization = StringField("Organization", validators=[Optional(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")


class ScriptForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    content = TextAreaField("Content", validators=[DataRequired()])
    scroll_speed = DecimalField(
        "Scroll speed",
        validators=[NumberRange(min=0.2, max=4.0)],
        default=1.0,
        places=1,
    )
    theme = SelectField(
        "Theme",
        choices=[("light", "Light"), ("dark", "Dark"), ("contrast", "High contrast")],
        default="light",
    )
    submit = SubmitField("Save script")


class ImportScriptForm(FlaskForm):
    provider = SelectField(
        "Provider",
        choices=[("google_drive", "Google Drive"), ("nextcloud", "Nextcloud")],
    )
    resource_id = StringField("Resource identifier", validators=[DataRequired(), Length(max=255)])
    convert_to_plaintext = BooleanField("Convert rich formatting to teleprompter-friendly markup", default=True)
    submit = SubmitField("Import")
