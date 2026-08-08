"""Explicit, least-privilege Google Drive backup support.

Constructing this class never opens a browser, refreshes a token, or changes
remote state. The operator must call ``connect`` and then an upload method.
"""

from __future__ import annotations

import csv
import io
import logging
import mimetypes
import os
from typing import Any, Dict, Optional

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TOKEN_PATH = os.environ.get("NLVE_GOOGLE_TOKEN_PATH", os.path.join(DATA_DIR, "google_token.json"))
CLIENT_SECRET_PATH = os.environ.get(
    "NLVE_GOOGLE_CLIENT_SECRET_PATH",
    os.path.join(DATA_DIR, "google_credentials.json"),
)


class GoogleDriveManager:
    """Manage app-created Drive files after explicit operator authorization."""

    def __init__(
        self,
        token_path: str = TOKEN_PATH,
        client_secret_path: str = CLIENT_SECRET_PATH,
        folder_name: str = "NLvoorelkaar Reachout Backups",
    ) -> None:
        self.token_path = os.path.abspath(token_path)
        self.client_secret_path = os.path.abspath(client_secret_path)
        self.folder_name = folder_name
        self.creds: Optional[Credentials] = None
        self.service = None
        self.folder_id: Optional[str] = None

    def status(self) -> Dict[str, Any]:
        return {
            "connected": bool(self.service and self.creds and self.creds.valid),
            "client_secret_present": os.path.isfile(self.client_secret_path),
            "token_present": os.path.isfile(self.token_path),
            "scope": SCOPES[0],
            "remote_changes": "Only explicit upload/download actions change or read Drive files.",
        }

    def connect(self, interactive: bool = False) -> Dict[str, Any]:
        """Connect to Drive; browser consent is allowed only when explicitly requested."""
        creds: Optional[Credentials] = None
        if os.path.isfile(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except (OSError, ValueError, TypeError) as exc:
                logger.warning("Google token could not be read: %s", type(exc).__name__)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except (RefreshError, OSError, RuntimeError, ValueError) as exc:
                logger.warning("Google token refresh failed: %s", type(exc).__name__)
                creds = None

        if (not creds or not creds.valid) and interactive:
            creds = self.get_new_credentials()

        if not creds or not creds.valid:
            self.creds = None
            self.service = None
            return self.status()

        self.creds = creds
        self.service = build("drive", "v3", cache_discovery=False, credentials=creds)
        self._store_token(creds)
        return self.status()

    def disconnect(self) -> None:
        """Drop the in-memory provider session without deleting local authorization."""
        self.creds = None
        self.service = None
        self.folder_id = None

    def revoke_local_token(self) -> bool:
        """Delete only the local token; provider-side revocation remains an account action."""
        self.disconnect()
        if not os.path.exists(self.token_path):
            return False
        os.remove(self.token_path)
        return True

    def _store_token(self, creds: Credentials) -> None:
        os.makedirs(os.path.dirname(self.token_path), mode=0o700, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
        try:
            os.chmod(self.token_path, 0o600)
        except OSError:
            logger.debug("Could not set private token permissions on this platform")

    def get_new_credentials(self) -> Credentials:
        if not os.path.isfile(self.client_secret_path):
            raise FileNotFoundError(
                f"Google OAuth client secret not found at {self.client_secret_path}. "
                "Set NLVE_GOOGLE_CLIENT_SECRET_PATH to a private file."
            )
        flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, SCOPES)
        return flow.run_local_server(port=0)

    def _require_service(self):
        if not self.service:
            raise RuntimeError("Google Drive is not connected. Run an explicit connect action first.")
        return self.service

    @staticmethod
    def _escape_query_value(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def get_folder_id_by_name(self, folder_name: str) -> Optional[str]:
        service = self._require_service()
        escaped = self._escape_query_value(folder_name)
        query = (
            f"name='{escaped}' and mimeType='application/vnd.google-apps.folder' "
            "and trashed=false"
        )
        result = service.files().list(q=query, spaces="drive", fields="files(id,name)").execute()
        files = result.get("files", [])
        return files[0].get("id") if files else None

    def _ensure_folder(self) -> str:
        service = self._require_service()
        if self.folder_id:
            return self.folder_id
        self.folder_id = self.get_folder_id_by_name(self.folder_name)
        if not self.folder_id:
            metadata = {
                "name": self.folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            created = service.files().create(body=metadata, fields="id").execute()
            self.folder_id = created["id"]
        return self.folder_id

    def find_file_by_name(self, file_name: str) -> Optional[Dict[str, str]]:
        service = self._require_service()
        folder_id = self._ensure_folder()
        escaped = self._escape_query_value(os.path.basename(file_name))
        query = f"name='{escaped}' and '{folder_id}' in parents and trashed=false"
        result = service.files().list(q=query, spaces="drive", fields="files(id,name)").execute()
        files = result.get("files", [])
        return files[0] if files else None

    def find_file_id_by_name(self, file_name: str) -> Optional[str]:
        found = self.find_file_by_name(file_name)
        return found.get("id") if found else None

    def upload_file(self, local_file_path: str, drive_file_name: Optional[str] = None) -> str:
        service = self._require_service()
        source = os.path.abspath(local_file_path)
        if not os.path.isfile(source):
            raise FileNotFoundError(source)
        remote_name = os.path.basename(drive_file_name or source)
        mime_type = mimetypes.guess_type(remote_name)[0] or "application/octet-stream"
        with open(source, "rb") as stream:
            media = MediaIoBaseUpload(stream, mimetype=mime_type, resumable=True)
            return self._upsert(remote_name, media)

    def upload_file_content(
        self,
        file_content: bytes,
        drive_file_name: str,
        mime_type: str = "text/csv",
    ) -> Dict[str, str]:
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type, resumable=True)
        file_id = self._upsert(os.path.basename(drive_file_name), media)
        return {"id": file_id, "name": os.path.basename(drive_file_name)}

    def _upsert(self, remote_name: str, media: MediaIoBaseUpload) -> str:
        service = self._require_service()
        folder_id = self._ensure_folder()
        existing = self.find_file_by_name(remote_name)
        if existing:
            updated = service.files().update(
                fileId=existing["id"],
                media_body=media,
                fields="id",
            ).execute()
            return updated["id"]
        created = service.files().create(
            body={"name": remote_name, "parents": [folder_id]},
            media_body=media,
            fields="id",
        ).execute()
        return created["id"]

    def download_file_content(self, file_id: str) -> bytes:
        request = self._require_service().files().get_media(fileId=file_id)
        output = io.BytesIO()
        downloader = MediaIoBaseDownload(output, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return output.getvalue()

    def download_file(self, file_id: str, local_file_path: str) -> str:
        destination = os.path.abspath(local_file_path)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, "wb") as output:
            request = self._require_service().files().get_media(fileId=file_id)
            downloader = MediaIoBaseDownload(output, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return destination

    def write_frequency_data(self, reminder_frequency: str, reminder_message: str) -> Dict[str, str]:
        with io.StringIO() as content:
            csv.writer(content).writerow([reminder_frequency, reminder_message])
            return self.upload_file_content(content.getvalue().encode("utf-8"), "reminder_data.csv")

    def read_frequency_data(self):
        file_id = self.find_file_id_by_name("reminder_data.csv")
        if not file_id:
            return None, None
        with io.StringIO(self.download_file_content(file_id).decode("utf-8")) as content:
            row = next(csv.reader(content), None)
        return (row[0], row[1]) if row and len(row) >= 2 else (None, None)


__all__ = ["GoogleDriveManager", "SCOPES"]
