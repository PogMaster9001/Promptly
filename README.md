# Promptly Teleprompter SaaS

Promptly is a Flask-based teleprompter platform tailored for SaaS use. It enables presenters to craft, import, and deliver scripts with premium formatting controls, while providing mobile-ready remote control and integrations with Google Drive and Nextcloud.

## Features

- **SaaS-ready user system** powered by Flask-Login, SQLAlchemy, and secure account flows.
- **Cloud script ingestion** from Google Drive and Nextcloud, with HTML-to-teleprompter conversion helpers.
- **Rich teleprompter controls** including scroll speed, mirroring, line spacing, uppercase, and guidelines.
- **Responsive remote control** page designed for phones, synchronized via Socket.IO.
- **REST API** endpoints for script data, supporting future integrations.

## Getting Started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**

   - Copy `.env.example` to `.env` (or configure environment variables another way).
   - Provide a `SECRET_KEY` and database URL (SQLite by default).
   - Supply Google Drive OAuth credentials and Nextcloud connection details.

3. **Initialize the database**

   ```bash
   flask --app manage.py db init
   flask --app manage.py db migrate -m "Initial tables"
   flask --app manage.py db upgrade
   ```

4. **Run the development server**

   ```bash
   python manage.py
   ```

   The app becomes available at `http://127.0.0.1:5000/` and the remote control channel listens on the same host.

## Google Drive Integration

- Store user OAuth tokens securely (database or secrets manager) and implement the placeholder `GoogleDriveService._load_user_credentials` to retrieve them.
- Ensure the OAuth client has the `drive.readonly` and `documents.readonly` scopes.
- The helper converts Google Docs exports to simplified plain text for teleprompter use.

## Nextcloud Integration

- Configure a dedicated app password for each user.
- Imported files use the WebDAV endpoint (`remote.php/dav/files`).
- HTML files reuse the Google Drive HTML-to-text converter; Markdown and plain text contents are handled as-is.

## Remote Control Channel

- Remote sessions are issued from the dashboard, producing a one-time token.
- The teleprompter view and the remote control page join the same Socket.IO room to synchronize play state and formatting.

## Roadmap Ideas

- Persist teleprompter preferences per user or per script.
- Add subscription plans, billing, and team management.
- Expand providers (Dropbox, OneDrive) through the service layer.
- Implement full OAuth token storage and refresh handling.

## Development Notes

- Avoid committing real secrets; use environment variables or an external secret store.
- Tests, linting, and CI hooks are not yet configured—set up before deploying to production.
