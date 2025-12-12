"""Google Drive integration helpers."""
from __future__ import annotations

import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from markupsafe import Markup
from werkzeug.utils import secure_filename

from . import ImportedScript
from ..extensions import db


class GoogleDriveService:
    """Fetch and normalize Google Drive files into teleprompter scripts."""

    def __init__(self, user) -> None:
        self.user = user
        self._integration = None
        self.credentials = self._load_user_credentials()

    def _load_user_credentials(self) -> Credentials:
        """Load OAuth credentials for the user.

        Replace this placeholder with a lookup against your persistent token store.
        The token should have Drive read-only scopes. Raise a RuntimeError if the
        credentials cannot be found so the caller can surface the issue to the user.
        """
        integration = self.user.get_integration("google_drive") if self.user else None
        if not integration:
            raise RuntimeError("Google Drive credentials not configured for this account.")

        self._integration = integration
        credentials = integration.as_credentials()
        return credentials

    def fetch_script(self, file_id: str, *, convert_to_plaintext: bool = True) -> ImportedScript:
        if not self.credentials:
            raise RuntimeError("Google Drive credentials missing.")

        if self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(Request())
            if self._integration:
                self._integration.update_from_credentials(self.credentials)
                db.session.add(self._integration)
                db.session.commit()

        try:
            service = build("drive", "v3", credentials=self.credentials, cache_discovery=False)
            metadata = service.files().get(fileId=file_id, fields="name, mimeType").execute()
            filename = metadata.get("name", "Script")
            mime_type = metadata.get("mimeType")

            if mime_type == "application/vnd.google-apps.document":
                export_mime_type = "text/html" if convert_to_plaintext else "text/plain"
                data = service.files().export(fileId=file_id, mimeType=export_mime_type).execute()
                content = data.decode("utf-8", errors="ignore")
            else:
                request = service.files().get_media(fileId=file_id)
                fh: io.BytesIO = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                content = fh.getvalue().decode("utf-8", errors="ignore")

            if convert_to_plaintext:
                content = self._to_plain_text(content)

            safe_title = secure_filename(filename) or "Imported Script"
            return ImportedScript(title=safe_title, content=content)
        except HttpError as exc:  # noqa: BLE001
            raise RuntimeError("Google Drive API error") from exc

    @staticmethod
    def _to_plain_text(payload: str) -> str:
        """Convert HTML payloads into a plain-text representation."""
        try:
            from bs4 import BeautifulSoup  # Local import to avoid hard dependency for tests
        except ModuleNotFoundError as exc:  # noqa: PERF203
            raise RuntimeError("beautifulsoup4 must be installed for HTML conversion") from exc

        soup = BeautifulSoup(payload, "html.parser")
        for unwanted in soup(["script", "style"]):
            unwanted.decompose()
        text = soup.get_text(separator="\n")
        normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return normalized

    @staticmethod
    def as_rich_text(text: str) -> Markup:
        """Provide a basic HTML rendering for scripts when rich formatting is needed."""
        try:
            import markdown  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("markdown package is required for rich text rendering") from exc

        return Markup(markdown.markdown(text))
