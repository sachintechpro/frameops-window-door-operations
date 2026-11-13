# FrameOps — GitHub and Render setup

## Repository layout

Upload the **contents** of this folder to the root of a new public GitHub repository (`sachintechpro/frameops-window-door-operations` recommended). Preserve filenames and nested directories:

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
    styles.css
assets/
    dashboard.png
    job-workspace.png
    mobile.png
data/
    .gitkeep
```

The `data/.gitkeep` placeholder is tracked so the directory exists. Do NOT commit generated SQLite files, database WAL/SHM files, uploads, or real homeowner records.

## Recommended Render setup

**Preferred:** create a Render web service from the GitHub repository using its `render.yaml` blueprint, or manually apply the settings below. Choose a **free** service.

| Render setting | Exact value |
|---|---|
| Service type | Web Service |
| Name | `frameops-operations` (or an available name) |
| Repository | `https://github.com/sachintechpro/frameops-window-door-operations` after repository creation |
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
