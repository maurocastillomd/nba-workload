# Deploy status

**Done:**
- Public repo live: https://github.com/maurocastillomd/nba-workload
- `main` pushed; the app reads the committed data snapshot, so the cloud box
  never needs to reach stats.nba.com.

**One step left (needs your browser, ~2 minutes):**

1. Go to https://share.streamlit.io and sign in **with GitHub**
   (maurocastillomd).
2. Click **Create app → Deploy a public app from GitHub**.
   - Repository: `maurocastillomd/nba-workload`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: pick `nba-workload` (gives nba-workload.streamlit.app)
3. Click **Deploy**. First build takes 2–3 minutes.

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
