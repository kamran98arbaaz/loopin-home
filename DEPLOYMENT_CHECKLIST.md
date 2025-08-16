Deployment checklist (refactor/api-blueprints)
=============================================

1. Merge PR to `master` (or rebase and fast-forward).
2. Ensure repository secrets are set if you want to publish assets:
   - For GitHub Pages deploy (optional): `GITHUB_TOKEN` is used automatically.
   - For S3 deploy (optional): set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET`.
3. CI will build CSS and upload as artifact `built-css`. If `deploy-assets` runs, it will publish to gh-pages; if `deploy-s3` runs it will sync to S3.
4. After deploy, call the health alert endpoint (CI can POST to `/health/alert` if `HEALTH_ALERT_URL` is configured):
   - The endpoint sends current `/health` payload to the webhook and returns the webhook response code.
5. Smoke test the public site and the API endpoints (`/api/updates`, `/metrics`, `/health`).
6. Monitor logs and metrics in your monitoring system.

Rollback
--------
- If issues occur, revert the PR or restore the previous deployment of static assets.

Notes
-----
- The app prefers built CSS at `static/dist/styles.css` when present; otherwise it uses a Tailwind CDN fallback.
- For production, prefer building and serving static assets from S3/CDN.
