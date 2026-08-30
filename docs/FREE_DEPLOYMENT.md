# Deploying LuminaRecs for Free (no credit card required)

This guide deploys the **full app** — Django + MySQL + the PyTorch/FAISS
recommendation engine — at zero cost, using only services that (a) have a real
free tier and (b) never ask for a credit card.

## Why most "free" options don't work here

Your app needs **~2–3 GB of RAM** just for the ML stack (PyTorch +
sentence-transformers + FAISS), a MySQL database, and outbound HTTPS for
OAuth/email. That rules out most free tiers:

| Service | Free tier | Why it fails for this project |
|---|---|---|
| Render free web service | 512 MB RAM | OOM with torch; no free MySQL; sleeps after 15 min |
| Koyeb free | 512 MB RAM | Same OOM problem |
| Railway | ~$5 one-time trial | No real free tier anymore |
| Heroku / Fly.io | — | Paid; card required |
| Oracle Cloud Always Free | 4 ARM cores / 24 GB | **Best free VM anywhere, but requires a credit card at signup** |
| Vercel / Netlify | static/serverless | Can't run Django + ML |
| PythonAnywhere free | 512 MB, SQLite only | No MySQL/Redis, ML RAM fails |

**Hugging Face Spaces (Docker SDK)** is the exception: free forever, no card,
2 vCPU / **16 GB RAM**, automatic HTTPS on `*.hf.space`, and it runs your
existing `Dockerfile` unmodified.

## Recommended stack

| Piece | Service | Free limits | Card? |
|---|---|---|---|
| App host | Hugging Face Space (Docker) | 2 vCPU / 16 GB RAM / 50 GB disk | No |
| Database | TiDB Cloud Starter (MySQL-compatible) | 5 GiB storage, ~50M RUs/month | No |
| Cache | none — `CACHE_BACKEND=locmem` | — | No |
| Email | Gmail SMTP + App Password | ~500 mails/day | No |
| OAuth | Google + GitHub (free) | — | No |

Notes:

- **Redis is optional here.** Celery has no tasks registered and Django
  sessions are DB-backed, so the only Redis use is the cache — which the new
  `CACHE_BACKEND=locmem` setting replaces with an in-process cache. (If you
  prefer shared caching, Upstash or Redis Cloud both have free, card-less
  tiers — set `REDIS_URL` instead.)
- **TiDB Cloud Starter** speaks the MySQL wire protocol; Django connects with
  the stock `django.db.backends.mysql` engine over TLS (see `DB_SSL_CA`
  below). Port is **4000**, not 3306.

## One-time repo changes already made

1. **`Dockerfile`** — build-time `collectstatic` now runs with `DEBUG=1`
   (scoped to that single step). Previously the production boot guard in
   `core/settings.py` refused to run because `.env` is excluded from the
   Docker build context.
2. **`.dockerignore`** — re-includes `platform_engine/ml_engine/model_data/`
   (~16 MB of trained FAISS/TF-IDF artifacts) so the deployed image serves
   working recommendations immediately.
3. **`core/settings.py`** — two new optional env vars:
   - `DB_SSL_CA=/path/to/ca-bundle` → enables TLS to managed MySQL.

## Step-by-step (~30 minutes)

### 1. Create the free MySQL database (TiDB Cloud Starter)

1. Sign up at <https://tidbcloud.com> with Google/GitHub — **no card asked**.
2. Create a **Starter (free)** cluster in any region.
3. Open **Connect** → copy the host (e.g. `gateway01.xxx.prod.aws.tidbcloud.com`),
   port `4000`, username, password.
4. Download the CA certificate if prompted (TiDB also accepts standard public
   CAs — `certifi`'s bundle, which is already in your requirements, works).

### 2. Push the project to GitHub (free)

```bash
git remote add origin git@github.com:<you>/luminarecs.git
git push -u origin master
```

### 3. Create the Hugging Face Space

1. Sign up at <https://huggingface.co> — **no card asked**.
2. **New Space** → name it `luminarecs` → SDK: **Docker** → Public.
3. Push the code to the Space:

```bash
git remote add space https://huggingface.co/spaces/<YOUR_USER>/luminarecs
git push space master
```

The first build takes ~15–25 min (torch is huge). Subsequent builds are fast.

### 4. Configure the Space

Space → **Settings → Variables and secrets**.

**Secrets** (runtime only — never visible in logs/builds):

| Name | Value |
|---|---|
| `SECRET_KEY` | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DB_NAME` | `luminarecs_db` |
| `DB_USER` | your TiDB username |
| `DB_PASSWORD` | your TiDB password |
| `DB_HOST` | `gateway01.<region>.prod.aws.tidbcloud.com` |
| `DB_PORT` | `4000` |
| `EMAIL_HOST_PASSWORD` | Gmail **App Password** (16 chars, myaccount.google.com/apppasswords) |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY/SECRET` | optional |
| `SOCIAL_AUTH_GITHUB_KEY/SECRET` | optional |

**Variables** (also visible at build time — fine for non-secrets):

| Name | Value |
|---|---|
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `<YOUR_USER>-luminarecs.hf.space` |
| `CSRF_TRUSTED_ORIGINS` | `https://<YOUR_USER>-luminarecs.hf.space` |
| `TRUST_PROXY` | `True` (HF terminates TLS; avoids redirect loops) |
| `CACHE_BACKEND` | `locmem` |
| `DB_SSL_CA` | `/usr/local/lib/python3.12/site-packages/certifi/cacert.pem` |
| `EMAIL_HOST_USER` | `you@gmail.com` |
| `DEFAULT_FROM_EMAIL` | `LuminaRecs <you@gmail.com>` |
| `GUNICORN_WORKERS` | `2` (16 GB RAM is plenty for 2 workers + models) |

Saving variables triggers a rebuild/restart; the `entrypoint.sh` then runs
`migrate` + `collectstatic` automatically and gunicorn serves on port 8000
(the `app_port` in README front matter tells HF where to route).

### 5. Seed the data

Run management commands **from your laptop against the remote TiDB database**
(no shell access is needed inside the Space):

```bash
# Free key from themoviedb.org (no card)
export TMDB_API_KEY=...

export DB_HOST=gateway01.<region>.prod.aws.tidbcloud.com DB_PORT=4000 \
       DB_NAME=luminarecs_db DB_USER=<tidb-user> DB_PASSWORD=<tidb-pass> \
       DB_SSL_CA="$(venv/bin/python -c 'import certifi; print(certifi.where())')" \
       SECRET_KEY=anything DEBUG=True

venv/bin/python manage.py migrate          # idempotent, matches Space boot
venv/bin/python manage.py seed_movies      # bulk-import the catalog
venv/bin/python manage.py createsuperuser  # staff dashboard login
```

The ML artifacts (FAISS index, similarity matrix) are baked into the image via
`.dockerignore`, so recommendations work immediately after seeding.

> Tip: because the DB is remote, you can develop locally against the same
> data, reseed anytime, or regenerate artifacts with the `train_*` commands
> and commit the 16 MB folder.

### 6. OAuth redirect URIs (if you use social login)

Add these in the Google Cloud Console → OAuth client, and GitHub → Developer
settings → OAuth Apps:

```
https://<YOUR_USER>-luminarecs.hf.space/complete/google-oauth2/
https://<YOUR_USER>-luminarecs.hf.space/complete/github/
```

### 7. Know the free-tier limits

- **Sleep:** free Spaces pause after ~48 h without visits; the next visitor
  wakes them (about a minute of warm-up). A free pinger (cron-job.org,
  UptimeRobot) hitting `/` daily keeps it always warm.
- **Ephemeral disk:** anything written outside the image (e.g. user uploads
  under `MEDIA_ROOT`) is lost on rebuild. Your static posters/trailers ship
  *inside* the image, so the catalog is safe; only runtime uploads are
  affected.
- **TiDB RU quota:** the free monthly Request-Unit allowance is far more than
  a demo needs; the scheduled `retrain_ai` job in `settings.py` is inert
  (no django-crontab installed), so nothing burns quota in the background.

## Truly-free alternative: Cloudflare Tunnel from your own machine

If you'd rather use your existing `docker-compose` stack (Caddy + MySQL +
Redis) untouched:

```bash
cloudflared tunnel --url http://localhost:80   # free quick tunnel, no card
```

You get a public `https://<random>.trycloudflare.com` URL with TLS in seconds.
Caveats: your machine must stay on, and quick-tunnel URLs rotate on restart
(a *named* tunnel needs a domain you own — domains cost money). Best for
demos/interviews, not for an always-on site.

## What still costs nothing but needs your attention

- **OAuth apps** (Google/GitHub) are free but each requires registering the
  final public domain.
- **Gmail App Password** requires 2FA enabled on the Google account.
- If traffic grows: HF Space persistent storage or a CPU upgrade is paid, and
  Oracle Cloud's Always-Free ARM VM (24 GB RAM, card needed at signup) is the
  natural next step once a card is acceptable.

   - `CACHE_BACKEND=locmem` → run without Redis.
4. **`README.md`** — Space metadata front matter (`sdk: docker`,
   `app_port: 8000`). HF requires it; GitHub just renders it as a table.
