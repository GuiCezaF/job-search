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
```

`schedule` uses cron syntax (APScheduler). `max_jobs_per_query` defaults to 32 if omitted (allowed range 1–200).

Allowed `experience_levels` values (internal mapping): `Internship`, `Entry level`, `Associate`, `Mid-Senior level`, `Director`, `Executive`.

Extra YAML keys (e.g. `google_drive`) are ignored by the current schema.

## Usage

### Single run

Runs one full cycle (login, search, CSV, Discord) and exits:

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

Mounts `config.yaml`, `output/`, and `logs/`. Environment variables come from `.env.production` (not `.env.dev`).

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
