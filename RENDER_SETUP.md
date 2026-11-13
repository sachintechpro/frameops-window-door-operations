# FrameOps — GitHub and Render setup

## Repository layout

The public repository already exists at https://github.com/sachintechpro/frameops-window-door-operations. Commit the **contents** of the project folder to the repository root, preserving filenames and directories:

```text
.gitignore
README.md
DESIGN.md
PORTFOLIO_ENTRY.md
RENDER_SETUP.md
server.py
render.yaml
public/
    index.html
    app.js
    ops_ui.js
    styles.css
assets/
    dashboard.png
    job-workspace.png
    mobile.png
    operations-dashboard.png
    operations-mobile.png
data/
    .gitkeep
tests/
    test_app.py
    test_operations.py
    browser_smoke.py
.github/
    workflows/test.yml
```

The `data/.gitkeep` placeholder is tracked so the directory exists. Do NOT commit generated SQLite files, database WAL/SHM files, uploads, or real homeowner records.

## Recommended Render setup

**Existing live service:** https://frameops-operations.onrender.com/ (Render dashboard: https://dashboard.render.com/web/srv-dbr9fitckfvc73dkdiog). Use this existing free service and repository rather than creating duplicates.

| Render setting | Exact value |
|---|---|
| Service type | Web Service |
| Name | `frameops-operations` (or an available name) |
| Repository | `https://github.com/sachintechpro/frameops-window-door-operations` |
| Branch | `main` |
| Root directory | Leave blank (files are at repository root) |
| Runtime | Python |
| Region | Oregon (or nearest available US region) |
| Instance type | Free |
| Build command | `echo "No dependencies to install"` |
| Start command | `python server.py` |
| Health check path | `/health` |
| Environment variable | `PUBLIC_DEMO=1` |
| Auto-deploy | Enabled, deploy on commit to `main` |

`server.py` listens on the `PORT` environment variable supplied by Render, defaulting locally to `10000`. Python standard library only; there is no `requirements.txt` and no package installation needed.

## Verify deployment

1. Wait for Render to report a successful deploy.
2. Open the live `https://...onrender.com` URL returned by Render and verify the dashboard loads.
3. Open `https://...onrender.com/health`; expected JSON: `{"status":"ok"}`.
4. Test a fictional homeowner job, task, and role work queue.
5. Add the **observed, verified** Render URL and GitHub repo URL to the profile/portfolio. Never guess a Render URL.

## Safety and limitations

This is a public **portfolio demonstration**, not a production system. It has no true login/role authorization, payment processing, e-signature, or lender connectivity. Do not enter real names, addresses, customer records, contracts or payment credentials. `PUBLIC_DEMO=1` disables uploaded documents but does not make the service suitable for sensitive data. SQLite storage on Render's free, ephemeral filesystem is **not durable** and may reset on restart or redeployment. A production version needs proper authentication, authorization, backups and a persistent database.

## Subsequent updates

Push changes to the same repository on `main`. Render should redeploy automatically; confirm status and open the live app after each change. Do not create another Render service for ordinary revisions.


## FrameOps 2.0 environment notes

The new backend module `operations.py` uses only Python standard library and is initialized by `server.py`. `public/ops_ui.js` supplies module navigation, guided help, appointment status forms, alerts and invoice printing. The Render settings remain unchanged. Optional `GOOGLE_REVIEW_URL` may be set to the business's **verified official Google review page**, never an invented URL; the app hides the customer review link when missing. `PUBLIC_DEMO=1` must stay enabled for this public fictional-data version.

Read [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) before handling real customer information. This version does not authenticate users, send external notifications or persist reliable production data.
