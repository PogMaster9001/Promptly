"""Nextcloud integration helpers."""
from __future__ import annotations

from urllib.parse import quote

import requests
from flask import current_app
from werkzeug.utils import secure_filename

from . import ImportedScript
from .google_drive import GoogleDriveService


class NextcloudService:
    """Fetch text files from a Nextcloud instance via WebDAV."""

    def __init__(self, user) -> None:
        self.user = user
        config = current_app.config
        self.base_url = (user.nextcloud_base_url or config.get("NEXTCLOUD_BASE_URL") or "").rstrip("/")
        self.username = user.nextcloud_username or config.get("NEXTCLOUD_USERNAME") or user.email
        self.app_password = user.nextcloud_app_password or config.get("NEXTCLOUD_APP_PASSWORD")
        if not all([self.base_url, self.username, self.app_password]):
            raise RuntimeError("Nextcloud credentials not configured.")

    def fetch_script(self, path: str, *, convert_to_plaintext: bool = True) -> ImportedScript:
        webdav_path = quote(path.strip("/"))
        url = f"{self.base_url}/remote.php/dav/files/{quote(self.username)}/{webdav_path}"
        response = requests.get(url, auth=(self.username, self.app_password), timeout=15)
        if response.status_code == 404:
            raise RuntimeError("Nextcloud resource not found.")
        response.raise_for_status()

        content = response.text
        if convert_to_plaintext:
            content = GoogleDriveService._to_plain_text(content)

        safe_title = secure_filename(path.split("/")[-1]) or "Imported Script"
        return ImportedScript(title=safe_title, content=content)
