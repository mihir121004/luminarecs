# Deploying LuminaRecs on ClawCloud Run (24/7)

ClawCloud Run runs your Docker container in their cloud, so the site stays
online **even when your Mac is off** — unlike the Cloudflare quick tunnel,
which only proxies traffic back to a `cloudflared` process running on your
machine and dies the moment your Mac sleeps.

```
BEFORE (dies when Mac sleeps):     Visitors → Cloudflare → cloudflared on your Mac
AFTER  (always on):                Visitors → ClawCloud public URL → container (MySQL/Redis alongside)
```

## 0. Prerequisites

- Repo pushed to GitHub (the image is built **by GitHub Actions**, not locally —
  no Docker install needed). See §1.
- ClawCloud account: sign up at **console.run.claw.cloud** with GitHub.
  GitHub accounts older than 180 days get **$5/month free credit**.
- Expected cost with the sizing below: roughly **$10–16/month** minus the
  free credit (24/7 CPU+RAM is what ClawCloud charges for).

## 1. Build the image with GitHub Actions

`.github/workflows/docker-publish.yml` (already in this repo) builds and
publishes on every push to `master`:

1. Create a GitHub repo and push:
   ```bash
   git remote add origin git@github.com:<your-username>/luminarecs.git
   git push -u origin master
   ```
2. Watch the **Docker Publish** workflow finish (Actions tab — first run
   takes ~15–25 min because torch/faiss-cpu wheels are large; later runs
   are much faster via layer cache).
3. The image appears at `ghcr.io/<your-username>/luminarecs:latest`.
4. **Make it pullable:** GitHub → your profile → **Packages** → `luminarecs`
   → Package settings → **Change visibility → Public**
   (alternative: keep it private and enter a pull secret instead — §3.1).

## 2. Create MySQL and Redis in ClawCloud (Databases section)

### 2.1 MySQL
Databases → **Create Database** → type `MySQL`, version **8.0**, name
`luminarecs-db`, 1 replica, 1 vCPU / 1 GB / 5 GB storage.

Before creating, open **advanced settings** and set:
- Database name: `luminarecs_db`
- Username: `luminarecs`
- Password: generate a long one (≥ 16 chars)

After creation, the panel shows the **internal connection string**, e.g.
`mysql://luminarecs:<pw>@mysql-xxxx-mysql.ns-xxxx.svc.cluster.local:3306/luminarecs_db`.
Copy the host part — you'll need it as `DB_HOST`.

### 2.2 Redis
Databases → **Create Database** → type `Redis`, version 7, 0.5 vCPU / 512 MB.
Copy the internal host and password.

> Internal cluster hostnames only resolve **inside** ClawCloud — that's why
> there are no publicly exposed DB ports, same security model as the
> `docker-compose.yml` backend network.

## 3. Create the app (App Launchpad)

App Launchpad → **Create Application**:

### 3.1 Image
- Image: `ghcr.io/<your-username>/luminarecs:latest`
- (private package instead: add an image **pull secret** — GitHub username +
  a PAT with `read:packages` — in the image section)
- Replicas: **1** (migrations run on boot; keep 1 unless you remove
  migrate-on-boot from `entrypoint.sh`)
- CPU: **1 vCPU** · Memory: **4 GB** (torch + faiss model loading needs the
  headroom; `docker-compose.yml` caps web at 3 GB)

### 3.2 Networking
- Container port: **8000** → **Enable Internet Access**
- ClawCloud assigns a public domain (or attach your own custom domain here
  later). Copy it — it goes into `ALLOWED_HOSTS`.

### 3.3 Advanced → Environment variables

| Key | Value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `core.settings` |
| `SECRET_KEY` | long random string — `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `<your-app>.<region>.run.claw.cloud` (domain from §3.2) |
| `TRUST_PROXY` | `True` |
| `FORWARDED_ALLOW_IPS` | `10.0.0.0/8,172.16.0.0/12` |
| `DB_ENGINE` | `django.db.backends.mysql` |
| `DB_NAME` | `luminarecs_db` |
| `DB_USER` | `luminarecs` |
| `DB_PASSWORD` | MySQL password from §2.1 |
| `DB_HOST` | MySQL internal host from §2.1 |
| `DB_PORT` | `3306` |
| `REDIS_URL` | `redis://:<redis-pw>@<redis-host>:6379/1` |
| `CACHE_TTL` | `3600` |
| `CSRF_TRUSTED_ORIGINS` | `https://<your-app>.<region>.run.claw.cloud` |
| `SECURE_SSL_REDIRECT` | `True` |
| `PASSWORD_RESET_LINK_PROTOCOL` | `https` |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp.gmail.com` (or your provider) |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP creds (Gmail: App Password) |
| `GUNICORN_WORKERS` | `2` |
| `GUNICORN_THREADS` | `4` |

Optional: Google/GitHub OAuth keys — then update each provider's redirect URI
to `https://<your-domain>/oauth/complete/google/` (resp. `.../github/`).

### 3.4 Advanced → Mount storage
Add a persistent volume so uploads survive redeploys:
mount path `/app/media`, size 2–5 GB.

### 3.5 Deploy & verify
Click **Deploy**, then open **Logs**: you should see
`Running migrations...` → `Collecting static files...` → gunicorn
`Listening at: http://0.0.0.0:8000`. The container healthchecks
`http://127.0.0.1:8000/` (Dockerfile `HEALTHCHECK`). Open the public URL.

## 4. Deploying updates

```bash
git push origin master          # CI rebuilds ghcr.io/...:latest (~2-5 min cached)
```
App Launchpad → your app → **Redeploy/Restart** (pulls the new `:latest`).
For guaranteed pinning, deploy the `:sha-<commit>` tag the workflow also
publishes.

## 5. Optional: your own domain / Cloudflare in front

1. App Launchpad → your app → Networking → add custom domain
   (create the CNAME to the ClawCloud public URL at your DNS provider).
2. Add the domain to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`, redeploy.
3. Using Cloudflare DNS: set SSL mode to **Full (strict)** so Cloudflare
   talks HTTPS to ClawCloud's ingress.

## 6. Migrating your local data (optional)

Your local MySQL data stays untouched. To move it, export first and import
via Django fixtures / a temporary public endpoint in the ClawCloud database
panel (internal hosts aren't reachable from your Mac):
```bash
brew services start mysql
mysqldump -u root -p luminarecs_db > dump.sql
```

## 7. Local dev afterwards

Nothing changes locally:
```bash
brew services start redis mysql
./scripts/free_deploy.sh        # temporary public URL via Cloudflare quick tunnel
```


