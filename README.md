# LuminaRecs 🎬

AI-powered movie recommendation platform — Django + MySQL + FAISS semantic search,
with OAuth sign-in (Google/GitHub) and a staff analytics dashboard.

## Project structure

```
luminarecs/
├── core/               # Django project: settings, urls, wsgi
├── platform_engine/    # Main app: views, models, ML/AI engine, API
│   ├── ml_engine/      # Hybrid recommender + FAISS semantic search
│   ├── ai/             # Taste-profile engine
│   └── utils/          # Security & logging middleware
├── templates/          # HTML templates (cinematic UI)
├── static/             # CSS, JS, videos, posters
├── docs/               # Architecture, deployment & production guides
├── scripts/            # One-off maintenance/diagnostic scripts
├── certs/              # Local HTTPS dev certificates (run_https.sh)
├── logs/               # Runtime logs (rotating)
└── .github/workflows/  # CI
```

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then fill in secrets
python manage.py migrate
python manage.py runserver      # http://localhost:8000
./run_https.sh                  # optional: local HTTPS dev server
```

## Key URLs

| Path | Description |
|---|---|
| `/` | Landing / lockscreen |
| `/login/`, `/signup/` | Auth (credentials + OAuth) |
| `/homepage/` | Personalized movie feed |
| `/analytics/` | Staff-only analytics dashboard |

## Documentation

See [`docs/`](docs/) — start with `ARCHITECTURE.md`, then
`QUICK_START_PRODUCTION.md` when deploying.
