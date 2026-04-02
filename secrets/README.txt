Secrets (local host and Docker)

Place files here (git ignores everything except this README and .gitkeep):

  google_drive_token.json
    Generated with:
      uv run python scripts/setup_google_drive_oauth.py \
        --client-secrets secrets/<your-client_secret>.json \
        --output secrets/google_drive_token.json

  client_secret_XXX.apps.googleusercontent.com.json
    Desktop OAuth 2.0 client JSON from Google Cloud Console.

  job-search-XXX.json (or any name)
    Service account key JSON (only useful with Google Workspace + Shared Drive).

Environment variables:

  Local (.env / .env.dev), paths relative to repo root, e.g.:
    GOOGLE_DRIVE_OAUTH_TOKEN_FILE=secrets/google_drive_token.json
    GOOGLE_APPLICATION_CREDENTIALS=secrets/job-search-492114-5a362c2a44cd.json

  Docker (.env.production), paths inside the container:
    GOOGLE_DRIVE_OAUTH_TOKEN_FILE=/app/secrets/google_drive_token.json

docker-compose mounts this directory as ./secrets -> /app/secrets.
