"""Google Drive config validation and mocked upload tests."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.storage.google_drive_uploader import GoogleDriveUploader
from src.types.exceptions import ReportingError
from src.types.schemas import AppConfig, GoogleDriveConfig


def test_google_drive_config_disabled_allows_empty_folder_id() -> None:
    cfg = GoogleDriveConfig(enabled=False, folder_id="")
    assert cfg.folder_id == ""


def test_google_drive_config_enabled_requires_folder_id() -> None:
    with pytest.raises(ValidationError, match="folder_id"):
        GoogleDriveConfig(enabled=True, folder_id="")


def test_google_drive_config_enabled_accepts_folder_id() -> None:
    cfg = GoogleDriveConfig(enabled=True, folder_id="abc123")
    assert cfg.folder_id == "abc123"


def test_app_config_parses_google_drive_block() -> None:
    data = {
        "linkedin": {"username": "u", "password": "p"},
        "discord": {"webhook_url": "https://example.com/hook"},
        "search": {
            "keywords": ["k"],
            "experience_levels": ["Entry level"],
            "locations": ["Remote"],
        },
        "google_drive": {"enabled": True, "folder_id": "folder1"},
    }
    app = AppConfig.model_validate(data)
    assert app.google_drive.enabled is True
    assert app.google_drive.folder_id == "folder1"


def test_uploader_upload_file_deletes_same_name_then_creates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same basename: list, delete ids, then create."""
    monkeypatch.delenv("GOOGLE_DRIVE_OAUTH_TOKEN_FILE", raising=False)
    sa_path = tmp_path / "sa.json"
    sa_path.write_text("{}", encoding="utf-8")
    csv_path = tmp_path / "jobs-2026-04-02.csv"
    csv_path.write_text("a,b\n", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(sa_path))

    list_execute = MagicMock(
        return_value={"files": [{"id": "old1", "name": csv_path.name}]}
    )
    delete_execute = MagicMock(return_value=None)
    create_execute = MagicMock(return_value={"id": "newid"})

    list_req = MagicMock()
    list_req.execute = list_execute
    delete_req = MagicMock()
    delete_req.execute = delete_execute
    create_req = MagicMock()
    create_req.execute = create_execute

    files_api = MagicMock()
    files_api.list.return_value = list_req
    files_api.delete.return_value = delete_req
    files_api.create.return_value = create_req

    service = MagicMock()
    service.files.return_value = files_api

    creds = MagicMock()

    with patch(
        "src.storage.google_drive_uploader.service_account.Credentials.from_service_account_file",
        return_value=creds,
    ):
        with patch("src.storage.google_drive_uploader.build", return_value=service):
            uploader = GoogleDriveUploader("parent_folder_id")
            file_id = uploader.upload_file(str(csv_path))

    assert file_id == "newid"
    files_api.delete.assert_called_once()
    files_api.create.assert_called_once()


def test_uploader_raises_when_credentials_path_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_OAUTH_TOKEN_FILE", raising=False)
    with pytest.raises(ReportingError, match="GOOGLE_DRIVE_OAUTH_TOKEN_FILE"):
        GoogleDriveUploader("folder")


def test_uploader_prefers_oauth_token_over_service_account(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When GOOGLE_DRIVE_OAUTH_TOKEN_FILE is set, service account is not used."""
    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    sa_path = tmp_path / "sa.json"
    sa_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_DRIVE_OAUTH_TOKEN_FILE", str(token_path))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(sa_path))

    user_creds = MagicMock()
    user_creds.expired = False
    user_creds.valid = True

    with patch(
        "src.storage.google_drive_uploader.UserCredentials.from_authorized_user_file",
        return_value=user_creds,
    ) as load_oauth:
        with patch("src.storage.google_drive_uploader.build", return_value=MagicMock()):
            GoogleDriveUploader("fid")

    load_oauth.assert_called_once()
