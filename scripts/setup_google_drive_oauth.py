#!/usr/bin/env python3
"""
Fluxo único (navegador) para gerar token OAuth e usar o Drive com conta Google pessoal.

Uso típico:
  uv run python scripts/setup_google_drive_oauth.py \\
    --client-secrets ~/Downloads/client_secret_....json \\
    --output ./google_drive_token.json

Depois defina GOOGLE_DRIVE_OAUTH_TOKEN_FILE com o caminho do arquivo gerado.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

_SCOPES = ("https://www.googleapis.com/auth/drive",)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera arquivo de token OAuth para upload no Google Drive (conta de usuário)."
    )
    parser.add_argument(
        "--client-secrets",
        required=True,
        type=Path,
        help="JSON 'OAuth 2.0 Client ID' tipo Desktop, baixado do Google Cloud Console.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("google_drive_token.json"),
        help="Arquivo de saída (não versionar; adicione ao .gitignore).",
    )
    args = parser.parse_args()

    if not args.client_secrets.is_file():
        print(f"Arquivo não encontrado: {args.client_secrets}", file=sys.stderr)
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
    print(f"Token salvo em: {args.output.resolve()}")
    print("Defina no .env: GOOGLE_DRIVE_OAUTH_TOKEN_FILE=<caminho absoluto>")
    print("Não use GOOGLE_APPLICATION_CREDENTIALS da service account para este modo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
