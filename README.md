LoopIn - Frontend build & Redis setup

LoopIn (refactor/api-blueprints)
=================================

This repository contains a small Flask app (LoopIn) and a refactor branch `refactor/api-blueprints` that adds a simple API, rate-limiting fallbacks, CI asset build, and basic health/metrics endpoints.

Quick start (local)
-------------------
1. Create and activate a Python virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install runtime deps:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. (Optional) Install dev/test deps (fakeredis) from `requirements-dev.txt`:

```powershell
pip install -r requirements-dev.txt
```

4. Run the app (set DATABASE_URL to a local sqlite for quick dev):

```powershell
$env:DATABASE_URL = "sqlite:///dev.db"
flask run
```

Running tests
-------------
Run the full test suite using the project's virtualenv Python:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Build CSS (Tailwind)
--------------------
A small Tailwind pipeline is included (source in `assets/css/tailwind.css`) and `package.json` contains `build:css`.

If you have Node installed locally:

```powershell
npm ci
npm run build:css
```

This writes the built stylesheet to `static/dist/styles.css`. The Flask app will prefer that file in templates when present.

CI and asset deployment
-----------------------
The GitHub Actions workflow `.github/workflows/ci.yml`:
- Installs runtime (and optional dev) dependencies
- Builds CSS if `package.json` is present
- Uploads `static/dist/styles.css` as an artifact named `built-css`
- Runs the test suite
- Optional `deploy-assets` job (runs only on `master`) downloads the artifact and publishes `static/dist` to GitHub Pages when the artifact exists. It uses `GITHUB_TOKEN` to push via `peaceiris/actions-gh-pages`.

If you prefer SSH deploy keys instead, you can switch the deploy step to use an SSH `DEPLOY_KEY` secret.

Health & metrics
----------------
- `/health` — combined health check returning DB status and Redis status (if Redis is configured).
- `/api/health/redis` — Redis connectivity check (200 OK when reachable, 503 otherwise).
- `/metrics` — a tiny Prometheus-style plaintext endpoint that returns `app_uptime_seconds` and `updates_total` and `redis_up`.

If you want richer Prometheus integration, install `prometheus_client` and I can wire up proper collectors.

Dev extras
----------
- `requirements-dev.txt` and `setup.cfg` define dev/test extras (e.g. `fakeredis`) to keep test-only deps separate from production `requirements.txt`.

Environment variables
---------------------
- `DATABASE_URL` — required. e.g. `sqlite:///dev.db` or a Postgres DSN.
- `API_WRITE_KEY` — API key used by the write endpoint when not posting as an authenticated session.
- `REDIS_URL` — if set, the app will attempt Redis-backed rate limiting.
- `API_RATE_LIMIT`, `API_RATE_WINDOW` — optional numeric env vars to tune rate limits.
- `FLASK_SECRET_KEY` — secret key; if not set, a default placeholder is used (replace in production).

Next steps you can ask me to perform
-----------------------------------
- Wire Prometheus client metrics (install `prometheus_client` and expose proper metrics).
- Add automatic asset publishing to an S3 bucket instead of GitHub Pages.
- Add monitoring/alerting hooks (PagerDuty/Webhook) for health failures.

S3 asset publishing (CI)
------------------------
The CI job `deploy-s3` will sync `static/dist` to an S3 bucket when on `master` if you set the following repository secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET`

It uses `aws s3 sync` and sets objects to `public-read`.

Health alerts
-------------
Set `HEALTH_ALERT_URL` to a webhook URL (PagerDuty, Slack incoming webhook, etc.). You can trigger an alert manually via POST to `/health/alert` and the app will forward the current `/health` payload.

---

If you want me to proceed with any of the next steps above, say which one and I'll implement it (update code, CI, and tests where applicable).
