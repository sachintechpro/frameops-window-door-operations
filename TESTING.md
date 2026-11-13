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


## FrameOps 2.0 regression coverage

Run `python -m unittest discover -s tests -v` for the original HTTP smoke checks **plus** integration scenarios covering scheduling/ETA delays, cross-team notification generation, invoice creation/printing and role checks, complete fictional lead-to-warranty-and-satisfaction workflow, service tickets, and contextual guide answers.

`tests/browser_smoke.py` is an additional developer-only Playwright/Chromium DOM smoke check using self-contained HTML, CSS and JavaScript (with mocked bootstrap data) to exercise the desktop and mobile layout, navigation, storefront, modal and guide UI. It is not part of GitHub Actions because browser binaries are not provisioned there.


## FrameOps 2.3 customer storefront tests

`python -m unittest discover -s tests -v` validates the 17-product fictional catalog, supported categories, original SVG product illustrations, social-settings interface availability and existing backend workflows.

`python tests/browser_storefront_smoke.py` runs an additional developer-only Playwright/Chromium simulation. It checks product browsing, the seven social settings, invalid social domains, enabled/disabled storefront links, simulated storage-event refresh, a storefront quote inquiry, generated Front Desk/Sales notifications, and narrow mobile layout with no JavaScript errors. It uses inlined assets and API stubs because some browser test environments block local network URLs; it is *not* a claim of multi-device or production notification testing.

CI also runs Node syntax checks against the customer-facing JavaScript files.
