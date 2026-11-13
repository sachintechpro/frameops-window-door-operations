# FrameOps — Test and deployment verification

This repository contains HTTP integration smoke tests for the **fictional-data public demo**.

## Run tests locally

```bash
python -m unittest discover -s tests -v
```

The tests automatically start the local Python server with `PUBLIC_DEMO=1`, use a temporary SQLite database, and verify static assets, health, seeded example jobs, role handoffs, stage blockers, and restrictions on public demo uploads. They do not modify the normal app database.

## GitHub Actions

`.github/workflows/test.yml` runs the same tests on pushes to `main` and pull requests.

## Render configuration

See `render.yaml` and `RENDER_SETUP.md` for a free Render Python web service with build command `echo "No dependencies to install"`, start command `python server.py`, health check `/health`, and `PUBLIC_DEMO=1`. Enable automatic deployments from the `main` branch after the GitHub repository exists.

## Production disclaimer

These tests are not a security assessment and do not constitute end-to-end verification of all business rules. The publicly accessible application has shared demo state without real authentication. Only fictional sample information may be entered.
