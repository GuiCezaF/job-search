# Job Search

Automation that searches **LinkedIn** jobs using keywords, locations, and experience levels from `config.yaml`, writes results to **CSV** under `output/`, and posts a summary to **Discord** via webhook.

## Requirements

- **Python 3.12+**
- A valid LinkedIn account (you are responsible for compliance and risk; see [Limitations](#limitations))
- A Discord webhook URL (channel or thread)

## Installation

```bash
# Virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Linux/macOS

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

### 1. Environment variables (`.env`)

Copy the template and fill in secrets:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `LINKEDIN_USERNAME` | LinkedIn email or username |
| `LINKEDIN_PASSWORD` | Password |
| `DISCORD_WEBHOOK_URL` | Full webhook URL |
| `APP_ENV` | Optional. `production`, `prod`, or `prd` suppresses **INFO** logs (keeps **WARNING** as plain text and **ERROR+** as JSON) |
| `HEADLESS` | Optional. `true` (default) or `false` to show the browser (useful on desktop) |

Environment secrets **override** matching keys in YAML when both are set.

### 2. `config.yaml`

Shape expected by the Pydantic validator:

```yaml
linkedin:
  username: "optional-if-using-env"
  password: "optional-if-using-env"

discord:
  webhook_url: "optional-if-using-env"

search:
  schedule: "0 12 * * *"          # cron (APScheduler)
  max_jobs_per_query: 32          # optional; default 32; range 1–200
  keywords: ["Python Developer"]
  experience_levels: ["Entry level", "Mid-Senior level"]
  locations: ["Remote"]
```

Allowed `experience_levels` values (internal mapping): `Internship`, `Entry level`, `Associate`, `Mid-Senior level`, `Director`, `Executive`.

Extra YAML keys (e.g. `google_drive`) are ignored by the current schema.

## Usage

### Single run

Runs one full cycle (login, search, CSV, Discord) and exits:

```bash
python main.py --now
# or
uv run python main.py --now
```

### Scheduled mode (service)

Without `--now`, the process stays up and runs the job on the **cron** in `search.schedule`:

```bash
python main.py
```

Stop with `Ctrl+C`.

## Docker

```bash
docker compose build
docker compose up -d
```

Mounts `config.yaml`, `.env`, `output/`, and `logs/`. For a one-shot run on start, uncomment `command: ["--now"]` in `docker-compose.yaml`.

The `Dockerfile` base image (`mcr.microsoft.com/playwright/python`) should **match the Playwright version** in `requirements.txt` (e.g. tag `v1.xx.x-jammy` or equivalent) so the runtime matches the installed browsers.

## Tests

```bash
pytest tests/
# or
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
main.py                 # CLI and orchestration
config.yaml             # Search parameters and schedule
src/
  scraper/              # Playwright / LinkedIn
  notifier/             # Discord (async httpx)
  storage/              # CSV
  utils/                # config, logging
  types/                # Pydantic models and exceptions
  scheduler.py          # APScheduler (cron)
tests/
```

## Limitations

- LinkedIn may show **CAPTCHA**, change the UI, or throttle automated accounts; continuous operation is not guaranteed.
- Automation may conflict with LinkedIn’s **terms of use**; use only in a lawful and responsible way.
- CSS selectors depend on the current UI; site changes may require updates in `linkedin_scraper.py`.
