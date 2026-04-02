# Job Search

Automation that searches **LinkedIn** jobs using keywords, locations, and experience levels from `config.yaml`, writes results to **CSV** under `output/`, and posts a summary to **Discord** via webhook.

## Requirements

- **Python 3.12+**
- A valid LinkedIn account (you are responsible for compliance and risk; see [Limitations](#limitations))
- A Discord webhook URL (channel or thread)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

On **Linux**, if Chromium fails due to missing system libraries:

```bash
sudo playwright install-deps chromium
```

On **Ubuntu 24.04 (Noble)**, use **Playwright ≥ 1.45** (as pinned in `requirements.txt`) to avoid older dependency names (`libicu70`, etc.).

With **uv**:

```bash
uv pip install -r requirements.txt
uv run playwright install chromium
```

## Configuration

### 1. Environment files (dev vs production)

| Context | File loaded by the app | Template |
|--------|-------------------------|----------|
| **Local** (default) | `.env.dev`, or `.env` if `.env.dev` is missing | `.env.dev.example` |
| **Docker** | `.env.production` when present in the workdir; Compose also injects vars via `env_file` | `.env.production.example` |

Detection uses `/.dockerenv` or `RUNNING_IN_DOCKER=true` (set in `docker-compose.yaml`).

```bash
cp .env.dev.example .env.dev
cp .env.production.example .env.production
```

The production file is required on the host before `docker compose up`.

Override for tests or tooling:

```bash
export DOTENV_FILE=/absolute/path/to/custom.env
```

`python-dotenv` uses `override=False`: variables already set in the process environment are not replaced by the file.

| Variable | Description |
|----------|-------------|
| `LINKEDIN_USERNAME` | LinkedIn email or username |
| `LINKEDIN_PASSWORD` | Password |
| `DISCORD_WEBHOOK_URL` | Full webhook URL |
| `APP_ENV` | Optional. `production`, `prod`, or `prd` suppresses **INFO** logs (keeps **WARNING** as plain text and **ERROR+** as JSON). Typical in `.env.production`. |
| `HEADLESS` | Optional. `true` or `false` (templates use `false` locally and `true` in production). |
| `RUNNING_IN_DOCKER` | Set by Compose; do not set manually on your laptop unless you mean to simulate Docker |
| `DOTENV_FILE` | Optional. Forces a specific env file path |
| `GOOGLE_APPLICATION_CREDENTIALS` | Optional. JSON da **service account** (só faz sentido com [Shared Drive](https://developers.google.com/workspace/drive/api/guides/about-shareddrives) no Google Workspace). |
| `GOOGLE_DRIVE_OAUTH_TOKEN_FILE` | Optional. Caminho do token OAuth de **usuário** (conta Gmail pessoal). Gere com `scripts/setup_google_drive_oauth.py`. Tem prioridade sobre `GOOGLE_APPLICATION_CREDENTIALS`. |

Environment secrets **override** matching keys in YAML when both are set.

### 2. `config.yaml`

Shape expected by the Pydantic validator (see also `config.yaml.example`):

```yaml
linkedin:
  username: "optional-if-using-env"
  password: "optional-if-using-env"

discord:
  webhook_url: "optional-if-using-env"

search:
  schedule: "0 12 * * *"
  max_jobs_per_query: 32
  keywords: ["Python Developer"]
  experience_levels: ["Entry level", "Mid-Senior level"]
  locations: ["Remote"]

google_drive:
  enabled: false
  folder_id: ""
```

`schedule` uses cron syntax (APScheduler). `max_jobs_per_query` defaults to 32 if omitted (allowed range 1–200).

Allowed `experience_levels` values (internal mapping): `Internship`, `Entry level`, `Associate`, `Mid-Senior level`, `Director`, `Executive`.

### 3. Google Drive (optional)

When `google_drive.enabled` is true, after saving the CSV locally the app uploads it to the folder whose **ID** is in `google_drive.folder_id` (from the Drive URL: `.../folders/FOLDER_ID`).

**Conta Google pessoal (Gmail):** use **OAuth de usuário**, não service account. O Google retorna **403** com mensagem do tipo *“Service Accounts do not have storage quota”* se você só compartilhar uma pasta do “Meu Drive” com a service account — [contas de serviço não têm cota própria](https://developers.google.com/drive/api/guides/about-auth) nesse cenário.

**Opção A — OAuth (recomendado para Gmail)**

1. [Google Cloud Console](https://console.cloud.google.com/): ative **Google Drive API**; em **APIs e serviços → Credenciais**, crie **ID do cliente OAuth** tipo **Aplicativo para computador** e baixe o JSON.
2. Tela de consentimento OAuth: modo **Teste** e adicione seu usuário como testador (ou publique o app se for o caso).
3. Gere o token (uma vez, abre o navegador):

   ```bash
   uv run python scripts/setup_google_drive_oauth.py \
     --client-secrets /caminho/client_secret_....json \
     --output ./google_drive_token.json
   ```

4. No `.env`: `GOOGLE_DRIVE_OAUTH_TOKEN_FILE=/caminho/absoluto/google_drive_token.json`
5. `config.yaml`: `google_drive.enabled: true` e `google_drive.folder_id` da pasta **na sua conta** (não precisa “compartilhar” com ninguém além do seu uso normal).

**Opção B — Service account + Shared Drive (Google Workspace)**

1. Ative a API, crie service account e chave JSON.
2. Crie ou use um **[Shared Drive](https://developers.google.com/workspace/drive/api/guides/about-shareddrives)** e adicione a service account como **membro** (Content manager ou similar), não basta compartilhar pasta do Meu Drive.
3. `GOOGLE_APPLICATION_CREDENTIALS` = caminho do JSON da SA.

If an upload fails, the error is logged and the run **continues** (Discord is still notified). Replacing the same filename: any existing file with that name in the folder is removed before upload (same-day CSV name stays a single file).

For Docker, mount the token or JSON as a read-only volume and set `GOOGLE_DRIVE_OAUTH_TOKEN_FILE` or `GOOGLE_APPLICATION_CREDENTIALS` to the path **inside** the container. Do not bake secrets into the image.

## Usage

### Single run

Runs one full cycle (login, search, CSV, optional Drive upload, Discord) and exits:

```bash
python main.py --now
uv run python main.py --now
```

### Scheduled mode (service)

Without `--now`, the process stays up and runs the job on the **cron** in `search.schedule`:

```bash
python main.py
```

Stop with `Ctrl+C`.

## Docker

Create `.env.production` on the host (from `.env.production.example`) before starting; Compose reads it via `env_file`.

```bash
docker compose build
docker compose up -d
```

Mounts `config.yaml`, `output/`, and `logs/`. Environment variables come from `.env.production` (not `.env.dev`). Mount the service account JSON and set `GOOGLE_APPLICATION_CREDENTIALS` if you use Drive in production.

One-shot run:

```bash
docker compose run --rm job-search --now
```

The `Dockerfile` base image (`mcr.microsoft.com/playwright/python`) should **match the Playwright version** in `requirements.txt` (e.g. tag `v1.xx.x-jammy` or equivalent) so the runtime matches the installed browsers.

## Tests

```bash
pytest tests/
uv run pytest tests/
```

`pytest.ini` sets `pythonpath = .` for `src.*` imports.

## Scraper behavior

- Up to **`max_jobs_per_query`** **accepted** jobs per keyword + location pair (after filters).
- Skips listings marked as **promoted/sponsored** and **already viewed** (heuristic based on visible text and DOM classes).
- Scrolls the LinkedIn results panel to load more cards (virtualized list).

## Output

- CSV at `output/vagas-YYYY-MM-DD.csv` by default (UTF-8 with BOM for Excel).
- Console logging: plain text for INFO/WARNING; JSON for ERROR/CRITICAL (fields such as `timestamp`, `level`, `module`, `message`, `hostname`, `extra_fields`).

## Project layout

```
main.py
config.yaml
src/
  scraper/
  notifier/
  storage/
  utils/
  types/
  scheduler.py
tests/
```

## Limitations

- LinkedIn may show **CAPTCHA**, change the UI, or throttle automated accounts; continuous operation is not guaranteed.
- Automation may conflict with LinkedIn’s **terms of use**; use only in a lawful and responsible way.
- CSS selectors depend on the current UI; site changes may require updates in `linkedin_scraper.py`.
