Title: Refactor — API blueprints, rate limiting, Redis, CI, assets, metrics

Summary
-------
This PR introduces an incremental refactor that adds:

- A dedicated API blueprint at `/api` with GET/POST for updates.
- Input validation and sanitization for write endpoints.
- Rate limiting with Redis-backed sliding/fixed-window implementations and an in-memory fallback.
- Optional API-key write auth plus session bypass for logged-in users.
- Redis helpers and a `/api/health/redis` endpoint.
- Prometheus metrics at `/metrics` (via `prometheus_client`) with a plaintext fallback.
- CI updates to build Tailwind CSS, run tests, upload built CSS as an artifact, and optional deployment to GitHub Pages or S3.
- A small frontend asset (Tailwind) build pipeline and a simple updates widget.
- Health endpoints and a `/health/alert` webhook forwarder to notify an external webhook.

Testing
-------
- Unit tests: 8 passed locally.
- Redis-paths tested with `fakeredis` (included in `requirements-dev.txt`).

Notes
-----
- CI includes a `workflow_dispatch` trigger for manual runs.
- Deploy jobs are conditional and require repository secrets for S3 or GitHub Pages push.

Release checklist
-----------------
See `DEPLOYMENT_CHECKLIST.md` for steps to publish built assets and validate health checks.
