---
title: LuminaRecs
emoji: 🎬
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# LuminaRecs 🎬

AI-powered movie recommendation platform built with Django, MySQL, and FAISS semantic search. Features OAuth sign-in (Google/GitHub), a staff analytics dashboard, and a cinematic user interface.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0-green?logo=django&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-red?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **AI-Powered Recommendations** — Hybrid recommender system combining collaborative filtering with semantic search using FAISS and sentence-transformers
- **Semantic Search** — Natural language movie search powered by transformer embeddings
- **User Authentication** — Email/password sign-up & login, plus OAuth via Google and GitHub
- **Personalized Feed** — Homepage tailored to your cinematic taste and watch history
- **Watch History** — Track movies you've watched with resume position
- **Wishlist** — Save movies for later viewing
- **Cinema Journal** — Personal movie diary and reviews
- **Discover & Browse** — Explore by genre, actor, director, or collection
- **Trailers** — Watch movie trailers from the catalog
- **Staff Analytics Dashboard** — Admin-only insights and platform metrics
- **Responsive Cinematic UI** — Dark-themed, immersive design

## 🏗️ Architecture

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

### Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 6.0, Django REST Framework |
| Database | MySQL 8.0 |
| Cache | Redis 7 |
| Task Queue | Celery 5.6 |
| ML/AI | PyTorch, FAISS, sentence-transformers, scikit-learn |
| Auth | social-auth-app-django (Google/GitHub OAuth), JWT |
| Frontend | HTML5, CSS3, JavaScript |
| Deployment | Docker Compose, Caddy, Gunicorn |
| CI/CD | GitHub Actions |

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- MySQL 8.0+
- Redis 7+

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/luminarecs.git
cd luminarecs

# Create and activate virtual environment
python -m venv venv && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env            # then fill in secrets

# Run database migrations
python manage.py migrate

# Start the development server
python manage.py runserver      # http://localhost:8000

# Optional: local HTTPS dev server
./run_https.sh
```

### Docker Deployment

```bash
# Configure environment
cp .env.example .env            # fill in production values

# Build and start all services
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

The Docker topology provides:
- **Caddy** — Auto-HTTPS reverse proxy (ports 80/443)
- **Web** — Django/Gunicorn application server
- **MySQL** — Database (internal network only)
- **Redis** — Cache and Celery broker (internal network only)

## 🔑 Key URLs

| Path | Description |
|---|---|
| `/` | Landing / lockscreen |
| `/login/`, `/signup/` | Authentication (credentials + OAuth) |
| `/homepage/` | Personalized movie feed |
| `/discover/` | Browse movies by genre, actor, director |
| `/trailers/` | Watch movie trailers |
| `/wishlist/` | Your saved movies |
| `/watch_history/` | Viewing history |
| `/search/` | AI-powered semantic search |
| `/profile/` | User profile and stats |
| `/analytics/` | Staff-only analytics dashboard |
| `/admin/` | Django admin interface |

## 📧 Local Email (Password Reset, Account Emails)

By default the app sends email to a local **MailHog** catcher so you can view reset/forgotten-password emails without configuring real SMTP credentials.

```bash
./scripts/mailhog.sh                 # start MailHog (downloads binary on first run)
```

- View captured emails at **http://127.0.0.1:8025**
- The app's SMTP backend points at `127.0.0.1:1025` (see `.env` → Email Configuration)

After changing `.env` restart the dev server. For real delivery, fill in a provider's SMTP credentials in `.env` (see the commented Gmail example there).

## 🤖 AI/ML Engine

### Recommendation System

LuminaRecs uses a hybrid recommendation approach:

1. **Collaborative Filtering** — Finds patterns across user interactions
2. **Content-Based Filtering** — Matches movie features to user preferences
3. **Semantic Search** — FAISS-powered similarity search on transformer embeddings

### Taste Profile Engine

The AI engine builds dynamic user taste profiles based on:
- Watch history and duration
- Explicit feedback (likes/dislikes/ratings)
- Implicit signals (wishlist additions, search queries)
- Genre and actor preferences

### Model Training

```bash
# Train recommendation models
python manage.py train_recommendations

# Update semantic search index
python manage.py update_faiss_index
```

## 🔐 Environment Variables

Key configuration options in `.env`:

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Allowed hosts | Required |
| `DB_NAME` | MySQL database name | `luminarecs_db` |
| `DB_USER` | MySQL username | `root` |
| `DB_PASSWORD` | MySQL password | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/1` |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY` | Google OAuth client ID | Optional |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET` | Google OAuth client secret | Optional |
| `SOCIAL_AUTH_GITHUB_KEY` | GitHub OAuth client ID | Optional |
| `SOCIAL_AUTH_GITHUB_SECRET` | GitHub OAuth client secret | Optional |

See `.env.example` for the full list of configuration options.

## 📚 Documentation

See [`docs/`](docs/) for comprehensive guides:

| Document | Description |
|---|---|
| `ARCHITECTURE.md` | System architecture and design decisions |
| `QUICK_START_PRODUCTION.md` | Production deployment quick start |
| `DEPLOYMENT_GUIDE.md` | Detailed deployment instructions |
| `PRODUCTION_READINESS.md` | Production readiness checklist |
| `PRODUCTION_REQUIREMENTS.md` | Production infrastructure requirements |
| `PRODUCTION_LAUNCH_SUMMARY.md` | Launch preparation summary |
| `PROJECT_ANALYSIS.md` | Comprehensive project analysis |

## 🧪 Running Tests

```bash
# Run all tests
python manage.py test platform_engine --verbosity 2

# Run specific test module
python manage.py test platform_engine.tests.test_recommendations
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FAISS](https://github.com/facebookresearch/faiss) — Efficient similarity search
- [sentence-transformers](https://www.sbert.net/) — Semantic embeddings
- [Django](https://www.djangoproject.com/) — Web framework
- [TMDB](https://www.themoviedb.org/) — Movie data source

---

<p align="center">Built with ❤️ by the LuminaRecs team</p>
