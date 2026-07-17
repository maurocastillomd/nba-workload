# Deploy to Streamlit Community Cloud (free, ~5 minutes)

The repo is deploy-ready: the app reads the committed data snapshot, so the
cloud box never needs to reach stats.nba.com.

1. **Create the GitHub repo** (public — Community Cloud needs public repos on
   the free tier):
   ```bash
   cd ~/nba-workload
   git remote add origin https://github.com/<your-username>/nba-workload.git
   git push -u origin main
   ```
   (Create the empty repo first at github.com/new — name it `nba-workload`,
   no README, since we already have one.)

2. **Connect Streamlit Cloud**: go to https://share.streamlit.io, sign in with
   GitHub, click **Create app → Deploy a public app from GitHub**.
   - Repository: `<your-username>/nba-workload`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: pick something like `nba-workload-monitor`

3. Click **Deploy**. First build takes 2–3 minutes. Done — the URL is public
   and shareable.

## Updating the data later

```bash
.venv/bin/python scripts/refresh_data.py 2025-26   # or the new season
git add data/ && git commit -m "Refresh data" && git push
```

Streamlit Cloud redeploys automatically on push.

## Where the link goes

- maurocastillomd.com portfolio, next to the readiness engine
- LinkedIn Featured section
- USTA / Ball State follow-up emails ("a live tool I built, open it on your phone")
