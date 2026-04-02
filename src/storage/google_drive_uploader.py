import json
import os
from pathlib import Path
from typing import Any, List

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from src.types.exceptions import ReportingError
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)

_DRIVE_SCOPE = ("https://www.googleapis.com/auth/drive",)

# Repository root (job-search/) for resolving relative paths in environment variables.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_credentials_path(env_value: str) -> Path:
    """Return an absolute path; relative values are resolved from the repository root."""
    path = Path(env_value.strip())
    if path.is_absolute():
        return path
    return (_REPO_ROOT / path).resolve()


def _escape_drive_query_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _load_drive_credentials() -> Any:
    """
    Drive API credentials: user OAuth (personal Drive) or service account JSON.

    Precedence: GOOGLE_DRIVE_OAUTH_TOKEN_FILE, then GOOGLE_APPLICATION_CREDENTIALS.
    """
    token_path_raw = os.getenv("GOOGLE_DRIVE_OAUTH_TOKEN_FILE", "").strip()
    if token_path_raw:
        token_path = _resolve_credentials_path(token_path_raw)
        if not token_path.is_file():
            raise ReportingError(f"OAuth token file not found: {token_path_raw}")
        try:
            creds = UserCredentials.from_authorized_user_file(
                str(token_path),
                scopes=list(_DRIVE_SCOPE),
            )
        except (GoogleAuthError, OSError, ValueError, json.JSONDecodeError) as err:
            raise ReportingError(f"Invalid Google Drive OAuth token file: {err}") from err

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
            except GoogleAuthError as err:
                raise ReportingError(f"Failed to refresh Google Drive OAuth token: {err}") from err
        elif not creds.valid:
            raise ReportingError(
                "Google Drive OAuth token is invalid or missing refresh_token; "
                "run scripts/setup_google_drive_oauth.py again."
            )
        return creds

    sa_path_raw = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not sa_path_raw:
        raise ReportingError(
            "Set GOOGLE_DRIVE_OAUTH_TOKEN_FILE (personal Google account) or "
            "GOOGLE_APPLICATION_CREDENTIALS (service account; requires Workspace Shared Drive)."
        )
    sa_path = _resolve_credentials_path(sa_path_raw)
    if not sa_path.is_file():
        raise ReportingError(f"Service account file not found: {sa_path_raw}")

    try:
        return service_account.Credentials.from_service_account_file(
            str(sa_path),
            scopes=_DRIVE_SCOPE,
        )
    except (GoogleAuthError, OSError, ValueError) as err:
        raise ReportingError(f"Invalid service account credentials: {err}") from err


class GoogleDriveUploader:
    """Upload files into a Drive folder using user OAuth or a service account."""

    def __init__(self, folder_id: str) -> None:
        fid = folder_id.strip()
        if not fid:
            raise ReportingError("Google Drive folder_id is empty")

        credentials = _load_drive_credentials()

        self._folder_id = fid
        self._service: Any = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def _list_ids_by_name(self, filename: str) -> List[str]:
        safe_name = _escape_drive_query_literal(filename)
        query = (
            f"'{self._folder_id}' in parents and name = '{safe_name}' "
            "and trashed = false"
        )
        response = (
            self._service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        return [f["id"] for f in response.get("files", [])]

    def _delete_file_ids(self, file_ids: List[str]) -> None:
        for file_id in file_ids:
            self._service.files().delete(
                fileId=file_id,
                supportsAllDrives=True,
            ).execute()

    def upload_file(self, local_path: str) -> str:
        """
        Upload ``local_path`` into the configured folder.

        Deletes any existing file with the same basename in that folder first.

        Returns the new Drive file id.
        """
        path = Path(local_path)
        if not path.is_file():
            raise ReportingError(f"Local file does not exist: {local_path}")

        filename = path.name
        existing = self._list_ids_by_name(filename)
        if existing:
            self._delete_file_ids(existing)
            logger.info(
                "Removed previous Drive file(s) with same name",
                extra={"extra_fields": {"name": filename, "count": len(existing)}},
            )

        media = MediaFileUpload(
            str(path),
            mimetype="text/csv",
            resumable=True,
        )
        body: dict[str, Any] = {
            "name": filename,
            "parents": [self._folder_id],
        }

        try:
            created = (
                self._service.files()
                .create(
                    body=body,
                    media_body=media,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except HttpError as err:
            status = getattr(getattr(err, "resp", None), "status", None)
            reason = str(err)
            extra: dict[str, Any] = {"status": status, "reason": reason}
            if status == 403 and (
                "storageQuotaExceeded" in reason
                or "Service Accounts do not have storage quota" in reason
            ):
                extra["hint"] = (
                    "Service accounts have no storage quota on personal My Drive. "
                    "Use OAuth: GOOGLE_DRIVE_OAUTH_TOKEN_FILE and "
                    "scripts/setup_google_drive_oauth.py, or a Google Workspace "
                    "Shared Drive with the service account as a member."
                )
            logger.error(
                "Google Drive API error",
                extra={"extra_fields": extra},
            )
            raise ReportingError("Google Drive upload failed") from err

        file_id = str(created.get("id", ""))
        logger.info(
            "Uploaded file to Google Drive",
            extra={"extra_fields": {"file_id": file_id, "name": filename}},
        )
        return file_id
