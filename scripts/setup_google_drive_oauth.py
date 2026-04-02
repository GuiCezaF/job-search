#!/usr/bin/env python3
"""
One-shot browser flow to create an OAuth token for Google Drive (personal Google account).

Typical usage (client secret and token under secrets/):

  uv run python scripts/setup_google_drive_oauth.py \\
    --client-secrets secrets/client_secret_XXX.apps.googleusercontent.com.json \\
    --output secrets/google_drive_token.json

Then set GOOGLE_DRIVE_OAUTH_TOKEN_FILE=secrets/google_drive_token.json (or /app/secrets/... in Docker).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

_SCOPES = ("https://www.googleapis.com/auth/drive",)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an OAuth token file for Google Drive uploads (user account)."
    )
    parser.add_argument(
        "--client-secrets",
        required=True,
        type=Path,
        help="Desktop OAuth 2.0 client JSON from Google Cloud Console.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("secrets/google_drive_token.json"),
        help="Output path (secrets/ is gitignored).",
    )
    args = parser.parse_args()

    if not args.client_secrets.is_file():
        print(f"File not found: {args.client_secrets}", file=sys.stderr)
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(
        str(args.client_secrets),
        scopes=list(_SCOPES),
    )
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(creds.to_json(), encoding="utf-8")
    print(f"Token saved to: {args.output.resolve()}")
    print("Set GOOGLE_DRIVE_OAUTH_TOKEN_FILE=secrets/google_drive_token.json in .env")
    print("Do not set GOOGLE_APPLICATION_CREDENTIALS for this mode (service account).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
