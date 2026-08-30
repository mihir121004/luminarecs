# Deploying LuminaRecs for Free (no credit card required)

> **Reality check (tested live on 2026-08-30):** Hugging Face changed its
> policy — **Docker Spaces now require a paid PRO subscription** (creating one
> on a free account returns `402 Payment Required`; only *static* Spaces are
> free). Render/Koyeb free tiers are 512 MB (the ML stack needs ~2–3 GB), and
> Railway/Heroku/Fly/Oracle all want a card. The one path that is **genuinely
> free, needs no card, and runs the full ML stack** is your own machine +
> a Cloudflare tunnel — it is what this guide deploys, verified end-to-end.

## The working recipe (proven live)

```
internet ──HTTPS──> Cloudflare edge (free TLS)
                        │  quick tunnel (cloudflared, no account needed)
                        ▼
        gunicorn :8010 on your Mac (DEBUG=False, boot guard on)
                        │
             local MySQL :3306 + Redis :6379
```

Cost: **$0**. Accounts needed: **none**. Full ML features included.

### One-command deploy

```bash
./scripts/free_deploy.sh          # starts tunnel + gunicorn, prints public URL
./scripts/free_deploy.sh stop     # stop everything
```

What `scripts/free_deploy.sh` does:

1. Starts `cloudflared` first and captures the generated
   `https://<random>.trycloudflare.com` URL.
2. Starts **gunicorn** on port 8010 with `DEBUG=False`, `TRUST_PROXY=True`,
   `SECURE_HSTS_SECONDS=31536000` and that exact URL in `ALLOWED_HOSTS`
   (the production boot guard in `core/settings.py` enforces all of this —
   wildcards, dev secrets and HSTS=0 are refused).
3. Health-checks the app (`HTTP 200`) and prints the URL. A dev server on
   :8000 keeps running untouched.

First run needs the binary once:

```bash
curl -sL -o /tmp/cloudflared.tgz \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz \
  && tar -xzf /tmp/cloudflared.tgz -C /tmp && chmod +x /tmp/cloudflared
# (or `brew install cloudflared` once the mongodb tap warning is resolved)
```

### Important caveats

- **Your Mac must stay on** (and awake) while the URL should work. Run
  `caffeinate -dims &` during long demo sessions.
- **Quick-tunnel URLs rotate on every restart.** Stable alternatives:
  - *ngrok* free tier: one **static domain** per account, no card.
  - *Named Cloudflare tunnel*: stable, but needs a domain you own (costs
    money, so outside the fully-free constraint).
- **OAuth + email on a rotating URL:** OAuth redirect URIs and email links
  want a fixed domain — on a quick tunnel use **email/password login**.
  With a stable URL, register it in the OAuth consoles and set a real SMTP
  provider (a Gmail App Password is free).
- Data, trained models and recommendations are exactly your local
  environment's — nothing to re-seed.

## Free cloud MySQL (optional, already created): TiDB Cloud Starter

The TiDB Cloud Starter cluster created during this deployment is free forever
(no card, 5 GiB, ~50M RUs/month). Keep it as the cloud database for a future
hosted deployment (e.g. a PRO Space or a VM once a card is acceptable):

```bash
# from the repo, against TiDB (TLS via the DB_SSL_CA setting)
export DB_HOST=gateway01.<region>.prod.aws.tidbcloud.com DB_PORT=4000 \
       DB_NAME=luminarecs_db DB_USER=<user> DB_PASSWORD=<pass> \
       DB_SSL_CA="$(venv/bin/python -c 'import certifi; print(certifi.where())')" \
       SECRET_KEY=anything DEBUG=True TMDB_API_KEY=<free key from themoviedb.org>

venv/bin/python manage.py migrate
venv/bin/python manage.py seed_movies      # bulk-import the catalog
```

Connection notes: port is **4000** (not 3306) and TLS is mandatory — handled
by the `DB_SSL_CA` option added to `core/settings.py`.

## Repo changes that enable all of this

1. **`Dockerfile`** — build-time `collectstatic` now runs with `DEBUG=true`
   (scoped to that step); the production boot guard previously rejected
   `.env`-less Docker builds.
2. **`.dockerignore` / `.gitignore`** — ship the ~16 MB of trained ML
   artifacts (`platform_engine/ml_engine/model_data/`) in images/repos.
3. **`core/settings.py`** — `DB_SSL_CA` (TLS to managed MySQL) and
   `CACHE_BACKEND=locmem` (run without Redis; sessions are DB-backed and
   Celery registers no tasks).
4. **`scripts/free_deploy.sh`** — the one-command tunnel deployment.

## Alternatives at a glance

| Option | Free? | Card? | Verdict for this app |
|---|---|---|---|
| Own machine + Cloudflare tunnel | yes, forever | no | **works fully — deployed live** |
| GitHub Codespaces (60 h/mo) | yes | no | works, but ephemeral + time-boxed |
| HF Spaces Docker | no (PRO) | — | was ideal, now paid |
| Render / Koyeb free | 512 MB | no | torch OOMs |
| Railway / Heroku / Fly | no | yes | out |
| Oracle Cloud Always Free (24 GB ARM) | yes | **required** | best value once a card is acceptable |
