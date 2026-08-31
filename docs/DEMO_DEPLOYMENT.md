# Free Public Demo on Render

A zero-cost, always-on public demo of LuminaRecs for portfolios/interviews.
Uses the same codebase with a **lightweight demo profile**:

| | Production (ClawCloud) | Demo (Render free) |
|---|---|---|
| Database | Managed MySQL | SQLite (seeded on boot) |
| Cache/Rate-limit | Redis | locmem (in-process) |
| Semantic search | FAISS + sentence-transformers | TF-IDF fallback (`similarity.pkl`) |
| Image size / RAM | ~3 GB / 4 GB | ~600 MB / 512 MB |
| Cost | ~$10–16/mo | **$0** |

## Deploy (one click)

1. Go to **render.com** → **Sign in with GitHub** (no credit card).
2. Authorize Render for the `luminarecs` repo when prompted.
3. **New → Blueprint** → select `luminarecs` → Render reads `render.yaml`
   (points at `Dockerfile.demo`) → **Apply**.
4. Build takes ~5–8 minutes (no torch to download). Your site appears at
   `https://luminarecs-demo.onrender.com`.

Everything is auto-configured by `entrypoint_demo.sh`: production security
flags, `ALLOWED_HOSTS`/`CSRF` from Render's assigned domain, SQLite
migrations, and movie seeding via `python manage.py seed_demo`
(from the committed `platform_engine/fixtures/demo_movies.json`).

## Free-tier caveats (expected behaviour)

- **Spin-down:** after ~15 minutes without visitors the container sleeps;
  the next visit wakes it in ~30–60 s (renders the login page slowly once).
- **Ephemeral disk:** signups/wishlist/watch-history reset whenever Render
  redeploys or restarts the container — the movie catalog is re-seeded
  automatically on boot. OAuth and password emails are disabled
  (mail prints to container logs).
- **Recommendations:** hybrid + TF-IDF recommendations work; transformer
  ("semantic") results are approximated by the TF-IDF cosine model.

## Updating the demo catalog

The fixture is a snapshot of the local MySQL catalog:
```bash
brew services start mysql
venv/bin/python manage.py dumpdata platform_engine.Genre platform_engine.Movie \
  --indent 1 -o platform_engine/fixtures/demo_movies.json
# compact it, then commit + push (CI rebuilds nothing; Render auto-deploys)
```
Regenerating the ML artifacts for new movies is only needed for the
production deployment, not the demo.
