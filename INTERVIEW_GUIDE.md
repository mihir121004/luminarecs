# LuminaRecs - Complete Project Knowledge Guide

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Design](#architecture--design)
3. [Database Models](#database-models)
4. [AI/ML Recommendation Engine](#aiml-recommendation-engine)
5. [API Endpoints](#api-endpoints)
6. [Authentication & Security](#authentication--security)
7. [Frontend & Templates](#frontend--templates)
8. [DevOps & Deployment](#devops--deployment)
9. [Testing](#testing)
10. [Key Technical Decisions](#key-technical-decisions)
11. [Interview Questions & Answers](#interview-questions--answers)

---

## Project Overview

**LuminaRecs** is an AI-powered movie recommendation platform that uses machine learning to provide personalized movie suggestions. The platform combines multiple recommendation techniques including collaborative filtering, content-based filtering, and semantic search.

### Core Value Proposition
- Personalized movie recommendations based on user behavior
- Semantic search using natural language processing
- AI-driven taste profiling
- Cinematic user experience

### Technology Stack
| Layer | Technology |
|-------|------------|

## Architecture & Design

### Project Structure
```
luminarecs/
├── core/                    # Django project configuration
│   ├── settings.py          # Single settings module (dev/prod via env vars)
│   ├── urls.py              # Root URL configuration
│   ├── wsgi.py              # WSGI entry point
│   └── asgi.py              # ASGI entry point
├── platform_engine/         # Main application
│   ├── models.py            # Database models (20+ tables)
│   ├── views.py             # View functions (1800+ lines)
│   ├── admin.py             # Django admin configuration
│   ├── urls.py              # API URL patterns
│   ├── frontend_urls.py     # Frontend URL patterns
│   ├── signals.py           # Django signals
│   ├── ai_engine.py         # AI profile generation
│   ├── ml_engine/           # Machine learning engine
│   │   ├── hybrid_engine.py     # Hybrid recommendation engine
│   │   ├── recommender.py       # Content-based recommender
│   │   ├── embedding_engine.py  # TF-IDF embedding generation
│   │   ├── semantic_recommender.py  # FAISS semantic search
│   │   ├── train_model.py       # Model training
│   │   ├── explain_engine.py    # Explanation generation
│   │   ├── cache_engine.py      # Recommendation caching
│   │   └── model_data/          # Serialized model files
│   ├── ai/                  # AI taste profiling
│   │   ├── taste_engine.py      # User taste profile engine
│   │   └── feedback_trainer.py  # Feedback-based training
│   ├── utils/               # Utilities
│   │   ├── logging.py           # Structured logging
│   │   ├── validators.py        # Input validation
│   │   └── exceptions.py        # Custom exceptions
│   ├── migrations/          # Database migrations
│   ├── management/          # Management commands
│   ├── templates/           # HTML templates
│   └── tests.py             # Test suite
├── templates/               # Global templates
├── static/                  # Static files (CSS, JS, images)
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── certs/                   # SSL certificates
├── logs/                    # Application logs
└── .github/workflows/       # CI/CD configuration
```

### Design Patterns Used
1. **MVC/MVT Pattern** - Django's Model-View-Template architecture
2. **Repository Pattern** - Database access through Django ORM

## Database Models

### Core Models

#### Movie
- **Purpose**: Stores movie catalog data from TMDB
- **Key Fields**: tmdb_id, title, overview, genres, director, cast_data (JSON), vote_average, popularity_score, embedding (JSON)
- **Indexes**: vote_average + popularity_score, release_year
- **Relationships**: Many-to-many with Genre, One-to-many with Review, WatchHistory, Wishlist

#### Genre
- **Purpose**: Movie genre classification
- **Key Fields**: name, slug (auto-generated)
- **Relationships**: Many-to-many with Movie

#### Actor
- **Purpose**: Actor information
- **Key Fields**: tmdb_id, name, biography, profile_path, known_for_department, popularity, birth_date, death_date, place_of_birth
- **Relationships**: Many-to-many with Movie

### User Interaction Models

#### WatchHistory
- **Purpose**: Tracks movies watched by users
- **Key Fields**: user (FK), movie (FK), progress, completed, watched_at
- **Relationships**: Links User and Movie

#### Wishlist
- **Purpose**: Movies saved for later viewing
- **Key Fields**: user (FK), movie (FK), added_at

#### Review
- **Purpose**: User reviews and ratings
- **Key Fields**: user (FK), movie (FK), rating (1-10), comment, created_at

#### UserFeedback
- **Purpose**: Explicit user feedback (like/dislike/rating)
- **Key Fields**: user (FK), movie (FK), feedback_type, rating
- **Choices**: like, dislike, rating

#### InteractionTelemetry
- **Purpose**: Implicit user behavior tracking
- **Key Fields**: user (FK), movie (FK), interaction_type, watch_duration, timestamp
- **Interaction Types**: WATCH, TRAILER, CLICK, VIEW, RATING, WISHLIST

### AI/ML Models

#### UserTasteProfile
- **Purpose**: AI-generated user preferences
- **Key Fields**: user (OneToOne), favorite_genres, favorite_actors, favorite_directors, preferred_rating, personality, watching_style, preferred_experience, taste_score

#### UserGenrePreference
- **Purpose**: Calculated genre preferences per user
- **Key Fields**: user (FK), genre, score, updated_at

#### AIUserInsight
- **Purpose**: AI-generated user personality insights
- **Key Fields**: user (OneToOne), personality, ai_summary, taste_score, story_score, visual_score, emotion_score, action_score, complexity_score, movie_analyzed, accuracy

#### AIModelVersion
- **Purpose**: ML model versioning and tracking
- **Key Fields**: name, version, algorithm, accuracy, trained_movies, model_path, is_active, created_at

#### Recommendation
- **Purpose**: Stored recommendations
- **Key Fields**: user (FK), movie (FK), score, algorithm, created_at

#### RecommendationLog
- **Purpose**: Recommendation click tracking
- **Key Fields**: user (FK), movie (FK), algorithm, score, clicked, created_at

### Supporting Models

#### Profile
- **Purpose**: Extended user profile
- **Key Fields**: user (OneToOne), avatar_style, avatar_seed, bio, location, website, twitter, instagram

## AI/ML Recommendation Engine

### Hybrid Recommendation System

The recommendation engine uses a **three-pronged approach**:

#### 1. Content-Based Filtering (recommender.py)
- **Algorithm**: TF-IDF + Cosine Similarity
- **Process**:
  1. Combine movie text features (title, overview, genres, keywords, director, writer, tagline, cast, production companies)
  2. Create TF-IDF vectors (max 10,000 features)
  3. Compute cosine similarity matrix
  4. Find most similar movies to a given movie
- **Scoring**: `final_score = (similarity * 0.6) + (popularity * 0.2) + (rating * 0.2)`

#### 2. Semantic Search (semantic_recommender.py)
- **Algorithm**: Sentence Transformers + FAISS
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Process**:
  1. Encode movie text into dense vector embeddings
  2. Build FAISS index for fast similarity search
  3. Query with natural language to find semantically similar movies
- **Storage**: FAISS index file + pickle movie mapping

#### 3. Hybrid Personalized Engine (hybrid_engine.py)
- **Algorithm**: Weighted feature scoring
- **Process**:
  1. Calculate user genre preferences from:
     - Watch history (weight: +5)
     - Wishlist (weight: +8)
     - High-rated reviews (weight: +10)
     - Interaction telemetry (weights vary by type)
  2. Build candidate pool (top 500 popular movies)
  3. Score each movie based on:
     - Genre match (+50 per matching genre)
     - Director match (+20)
     - Actor match (+10)
     - Popularity score (/10)
     - Vote average (*3)
     - Preferred rating proximity
  4. Return top N recommendations

### Taste Profile Engine (taste_engine.py)
- **Purpose**: Build comprehensive user taste profiles
- **Data Sources**: Watch history, feedback, reviews, wishlist
- **Outputs**:
  - Top 5 favorite genres
  - Top 5 favorite actors
  - Top 5 favorite directors
  - Preferred rating average
  - Personality type (e.g., "Adrenaline Cinema Hunter")
  - Watching style (e.g., "High Intensity Viewer")
  - Preferred experience (e.g., "High Energy Cinematic Experience")
  - Taste score (0-100)

### Explanation Engine (explain_engine.py)
- **Purpose**: Generate human-readable reasons for recommendations
- **Logic**:
  - Match user's watched genres with recommended movie
  - Mention director if user has watched their movies
  - Highlight high ratings (>= 8)
  - Note trending status (popularity > 100)
  - Reference user's positive review history

### Caching Strategy (cache_engine.py)
- **Cache Duration**: 1 hour (3600 seconds)
- **Cache Key**: `user_recommendations_{user_id}`
- **Backend**: Django cache framework (Redis)

### Model Training Pipeline (train_model.py)
1. Fetch all movies from database
2. Extract and combine text features
3. Create TF-IDF vectors
4. Compute cosine similarity matrix
5. Save model files (tfidf.pkl, similarity.pkl, movies.pkl)
6. Update movie embeddings in database

## API Endpoints

### REST API Endpoints (api_views.py & api_views_enhanced.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/movies/` | List top movies (paginated) |
| GET | `/api/movies/<id>/` | Movie details |
| GET | `/api/movies/<id>/recommendations/` | Get movie recommendations |
| GET | `/api/search/?q=<query>` | Search movies |
| POST | `/api/track/` | Track user interaction |

### Enhanced API Features (api_views_enhanced.py)
- **Rate Limiting**: 1000/hour authenticated, 100/hour anonymous
- **Input Validation**: Dedicated validator classes
- **Error Handling**: Structured error responses with codes
- **Logging**: Request/response logging with timing
- **Pagination**: Configurable page size (max 100)

### Frontend URL Patterns (frontend_urls.py)

| URL | View | Description |
|-----|------|-------------|
| `/` | lockscreen | Landing page |
| `/landing/` | landing | Marketing landing page |
| `/login/` | login | User login |
| `/signup/` | signup | User registration |
| `/homepage/` | homepage | Personalized feed |
| `/logout/` | logout_view | Logout |
| `/movie/<id>/` | movie_details | Movie detail page |
| `/wishlist/` | wishlist | User's wishlist |
| `/profile/` | profile | User profile |
| `/discover/` | discover | Browse movies |
| `/trailers/` | trailers | Movie trailers |
| `/watch_history/` | watch_history | Viewing history |
| `/search/` | search_movies_page | Search page |
| `/recommendations/` | personalized_recommendations | AI recommendations |

## Authentication & Security

### Authentication Methods
1. **Email/Password**: Django's built-in authentication
2. **Google OAuth**: via social-auth-app-django
3. **GitHub OAuth**: via social-auth-app-django
4. **JWT Tokens**: For API authentication (djangorestframework-simplejwt)

### Security Features
- **CSRF Protection**: Django's CSRF middleware
- **Password Validation**: Minimum 12 characters, common password check, numeric password check
- **Production Boot Guard**: Refuses to start without proper SECRET_KEY and ALLOWED_HOSTS
- **Secure Cookies**: SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE in production
- **HSTS**: HTTP Strict Transport Security enabled
- **XSS Protection**: SECURE_BROWSER_XSS_FILTER, CONTENT_TYPE_NOSNIFF
- **Content Security Policy**: CSP middleware with strict directives
- **Rate Limiting**: API throttling (1000/hour authenticated, 100/hour anonymous)
- **Input Validation**: Dedicated validator classes for all user inputs
- **SQL Injection Protection**: Django ORM parameterized queries

### OAuth Configuration
```python
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", "")
SOCIAL_AUTH_GITHUB_KEY = os.getenv("SOCIAL_AUTH_GITHUB_KEY", "")
SOCIAL_AUTH_GITHUB_SECRET = os.getenv("SOCIAL_AUTH_GITHUB_SECRET", "")
```

---

## Frontend & Templates

### Template Structure
- **Base Template**: `base.html` with common layout
- **Cinematic UI**: Dark theme with gold accents
- **Responsive Design**: Mobile-first approach
- **Components**: Navigation, footer, movie cards, hero sections

### Key Templates
- `landing.html` - Marketing page
- `homepage.html` - Personalized feed
- `movie_details.html` - Movie detail view
- `profile.html` - User profile
- `wishlist.html` - Wishlist page

## DevOps & Deployment

### Docker Architecture
```
internet → Caddy (80/443) → Web (8000) → MySQL/Redis (internal)
```

**Security Features**:
- MySQL and Redis have NO published ports (internal network only)
- Web container has NO published ports (only through Caddy)
- All services run with `no-new-privileges:true`
- Memory limits enforced on all containers

### Docker Compose Services
1. **caddy**: Reverse proxy with auto-HTTPS
2. **web**: Django/Gunicorn application
3. **db**: MySQL 8.0 database
4. **redis**: Redis 7 cache

### CI/CD Pipeline (GitHub Actions)
- **Triggers**: Push/PR to main/master
- **Services**: MySQL 8.0, Redis 7
- **Steps**:
  1. Checkout code
  2. Set up Python 3.12
  3. Install dependencies
  4. Run Django system checks
  5. Run migrations
  6. Run tests

### Production Configuration
- **Web Server**: Gunicorn with Whitenoise for static files
- **SSL/TLS**: Caddy automatic HTTPS (Let's Encrypt)
- **Caching**: Redis for session and cache backend
- **Task Queue**: Celery with Redis broker
- **Monitoring**: Sentry integration (optional)
- **Logging**: Rotating file handlers (10MB max, 5 backups)

### Environment Variables
| Variable | Purpose | Required |
|----------|---------|----------|
| SECRET_KEY | Django secret key | Yes |
| DEBUG | Debug mode | No (default: False) |
| ALLOWED_HOSTS | Allowed hosts | Yes |
| DB_NAME | MySQL database name | No (default: luminarecs_db) |
| DB_USER | MySQL username | No (default: root) |
| DB_PASSWORD | MySQL password | Yes |
| REDIS_URL | Redis connection URL | No |
| SOCIAL_AUTH_GOOGLE_OAUTH2_KEY | Google OAuth | No |
| SOCIAL_AUTH_GITHUB_KEY | GitHub OAuth | No |
| SENTRY_DSN | Sentry error tracking | No |

---

## Testing

### Test Suite (tests.py)
- **InputValidatorTestCase**: Tests for validation utilities
- **MovieAPITestCase**: Tests for movie API endpoints
- **AuthenticationTestCase**: Tests for auth flows
- **AnalyticsTestCase**: Tests for analytics dashboard
- **ProfileAndWatchHistoryTestCase**: Tests for profile and history

## Key Technical Decisions

### 1. Single Settings Module
**Decision**: Use one settings.py for all environments
**Rationale**: Simpler configuration, environment-based behavior selection
**Implementation**: `TESTING` flag auto-detects test mode, `DEBUG` flag controls production guards

### 2. Hybrid Recommendation Approach
**Decision**: Combine multiple recommendation techniques
**Rationale**: No single algorithm works best for all users
**Benefits**:
- Content-based: Good for new users with some history
- Semantic: Captures nuanced preferences
- Hybrid: Balances popularity, ratings, and personal taste

### 3. FAISS for Semantic Search
**Decision**: Use Facebook's FAISS library
**Rationale**: Efficient similarity search on dense vectors
**Benefits**: Fast nearest neighbor search, scalable to millions of items

### 4. TF-IDF for Content-Based Filtering
**Decision**: Use scikit-learn's TF-IDF + Cosine Similarity
**Rationale**: Proven technique for text similarity, interpretable results
**Benefits**: Fast training, easy to update, works well with movie metadata

### 5. Redis for Caching
**Decision**: Cache recommendations for 1 hour
**Rationale**: Recommendations don't need real-time updates
**Benefits**: Reduces database load, faster response times

## Interview Questions & Answers

### Q1: What is LuminaRecs?
**A**: LuminaRecs is an AI-powered movie recommendation platform built with Django. It uses machine learning techniques including collaborative filtering, content-based filtering, and semantic search to provide personalized movie recommendations. The platform features OAuth authentication, a cinematic user interface, and a staff analytics dashboard.

### Q2: Explain the recommendation engine architecture.
**A**: The recommendation engine uses a hybrid approach with three main components:
1. **Content-Based Filtering**: Uses TF-IDF vectorization on movie metadata (title, overview, genres, director, cast) and cosine similarity to find similar movies.
2. **Semantic Search**: Uses sentence transformers to create dense vector embeddings and FAISS for fast similarity search, enabling natural language queries.
3. **Hybrid Personalized Engine**: Calculates user genre preferences from watch history, wishlist, reviews, and interaction telemetry, then scores movies based on genre match, director/actor match, popularity, and ratings.

### Q3: How do you handle the cold start problem?
**A**: The cold start problem is addressed through:
1. **Popularity-based fallback**: New users see popular movies initially
2. **Onboarding**: Collect preferences during signup
3. **Multiple signals**: Even minimal interactions (clicks, views) contribute to recommendations
4. **Candidate pool limitation**: Focus on top 500 popular movies for scoring

### Q4: How is user data modeled?
**A**: The data model includes:
- **Core entities**: Movie, Genre, Actor
- **User interactions**: WatchHistory, Wishlist, Review, UserFeedback, InteractionTelemetry
- **AI-generated profiles**: UserTasteProfile, UserGenrePreference, AIUserInsight
- **System tracking**: AIModelVersion, Recommendation, RecommendationLog

### Q5: What security measures are implemented?
**A**: 
- Production boot guard (requires proper SECRET_KEY and ALLOWED_HOSTS)
- CSRF protection, XSS protection, HSTS
- Content Security Policy
- Rate limiting on API endpoints
- Input validation on all user inputs
- Docker network isolation (database not exposed)
- Password validation (min 12 chars, complexity checks)

### Q6: How do you track user behavior?
**A**: Through InteractionTelemetry model that captures:
- Interaction types: WATCH, TRAILER, CLICK, VIEW, RATING, WISHLIST
- Watch duration
- Timestamp
This data feeds into the recommendation engine to improve suggestions.

### Q7: Explain the caching strategy.
**A**: Recommendations are cached in Redis with:
- Key: `user_recommendations_{user_id}`
- TTL: 1 hour (3600 seconds)
- Cache is invalidated when user generates new interactions
This reduces database load and improves response times.

### Q8: How is the application deployed?
**A**: Using Docker Compose with:
- **Caddy**: Reverse proxy with auto-HTTPS
- **Web**: Django/Gunicorn application
- **MySQL**: Database (internal network only)
- **Redis**: Cache and Celery broker (internal network only)
CI/CD is handled by GitHub Actions running tests on every push/PR.

### Q9: What testing is performed?
**A**: 
- Unit tests for input validation
- API endpoint tests
- Authentication flow tests
- Pagination tests
- Recommendation engine tests
- Integration tests for watch history creation

### Q10: How do you explain recommendations to users?
**A**: The explanation engine generates human-readable reasons like:
- "You enjoy Action movies"
- "Directed by Christopher Nolan, matching your cinematic taste"
- "Highly rated by audiences"
- "Trending among movie lovers"

### Q11: What is the role of Celery in this project?
**A**: Celery is configured as a task queue for:
- Asynchronous model training
- Scheduled tasks (e.g., daily AI retraining at 3 AM)
- Background processing of recommendations
- Redis is used as the message broker

### Q12: How do you handle model versioning?
**A**: Through the AIModelVersion model that tracks:
- Model name and version
- Algorithm used

## Key Metrics to Remember

- **20+ database tables** for comprehensive data modeling
- **3 recommendation algorithms** working together
- **500 candidate movies** scored for personalized recommendations
- **1 hour cache TTL** for recommendations
- **10,000 max TF-IDF features** for content-based filtering
- **1000 API requests/hour** rate limit for authenticated users
- **12 character minimum** password length
- **10MB max log file size** with 5 backups

---

## How to Explain the Project in an Interview

### Elevator Pitch (30 seconds)
"LuminaRecs is an AI-powered movie recommendation platform I built using Django and machine learning. It analyzes user behavior—watch history, ratings, and even clicks—to provide personalized movie suggestions. The system combines multiple recommendation techniques including semantic search using transformer embeddings and FAISS for fast similarity matching."

### Technical Deep Dive (5 minutes)
1. Start with the architecture (Django MVT, REST API)
2. Explain the database design (20+ models, relationships)
3. Detail the recommendation engine (hybrid approach)
4. Discuss security measures (production guards, Docker isolation)
5. Mention deployment (Docker Compose, CI/CD)
6. Highlight testing strategy

### Key Differentiators to Mention
- Hybrid recommendation approach (not just one algorithm)
- Semantic search with transformer embeddings
- Production-ready security features
- Comprehensive logging and monitoring
- Docker-based deployment with network isolation

---

## Quick Reference: File Locations

| Component | File Path |
|-----------|-----------|
| Settings | `/core/settings.py` |
| Root URLs | `/core/urls.py` |
| All Models | `/platform_engine/models.py` |
| Main Views | `/platform_engine/views.py` |
| Frontend URLs | `/platform_engine/frontend_urls.py` |
| API URLs | `/platform_engine/urls.py` |
| Admin Config | `/platform_engine/admin.py` |
| Hybrid Engine | `/platform_engine/ml_engine/hybrid_engine.py` |
| Content Recommender | `/platform_engine/ml_engine/recommender.py` |
| Semantic Search | `/platform_engine/ml_engine/semantic_recommender.py` |
| Embedding Engine | `/platform_engine/ml_engine/embedding_engine.py` |
| Model Training | `/platform_engine/ml_engine/train_model.py` |
| Explain Engine | `/platform_engine/ml_engine/explain_engine.py` |
| Cache Engine | `/platform_engine/ml_engine/cache_engine.py` |
| Taste Engine | `/platform_engine/ai/taste_engine.py` |
| AI Engine | `/platform_engine/ai_engine.py` |
| Signals | `/platform_engine/signals.py` |
| Logging | `/platform_engine/utils/logging.py` |
| Validators | `/platform_engine/utils/validators.py` |
| Tests | `/platform_engine/tests.py` |
| Docker Compose | `/docker-compose.yml` |
| Dockerfile | `/Dockerfile` |
| CI/CD | `/.github/workflows/ci.yml` |
| Requirements | `/requirements.txt` |

---

Good luck with your interview! 🎬
- Accuracy metrics
- Number of movies trained
- Model file path
- Active status

### Q13: What is the database schema design approach?
**A**: 
- Normalized schema with proper foreign key relationships
- JSON fields for flexible data (cast_data, embedding)
- Database indexes on frequently queried fields
- Many-to-many relationships for movies-genres and movies-actors
- One-to-one for user profiles

### Q14: How does the semantic search work?
**A**: 
1. Movie text (title + overview + genres + director) is encoded using `sentence-transformers/all-MiniLM-L6-v2`
2. Embeddings are stored in a FAISS index
3. When searching, the query is encoded and compared against the index
4. FAISS returns the most similar movies based on L2 distance

### Q15: What are the key challenges in this project?
**A**: 
1. **Scalability**: Handling large movie catalogs and user bases
2. **Cold start**: Providing good recommendations for new users
3. **Real-time updates**: Keeping recommendations fresh as user interacts
4. **Performance**: Balancing recommendation quality with response time
5. **Data quality**: Ensuring accurate movie metadata

### 6. Docker Network Isolation
**Decision**: Separate frontend and backend networks
**Rationale**: Security - database and cache not exposed to internet
**Benefits**: Defense in depth, reduced attack surface

### 7. Structured Logging
**Decision**: JSON-formatted logs with request tracking
**Rationale**: Easier log analysis in production
**Benefits**: Request tracing, performance monitoring, security auditing
- **WatchHistoryPaginationTestCase**: Tests for pagination
- **MovieDetailsWatchHistoryTestCase**: Tests for watch history creation
- **HybridRecommendationsTestCase**: Tests for recommendation engine

### Running Tests
```bash
# Run all tests
python manage.py test platform_engine --verbosity 2

# Run specific test case
python manage.py test platform_engine.tests.MovieAPITestCase
```

### CI Testing
- Tests run automatically on push/PR
- Uses MySQL and Redis services
- MD5 password hasher for faster test execution
- `search_results.html` - Search results
- `analytics_dashboard.html` - Staff analytics

### Static Files
- **CSS**: Custom cinematic styling
- **JavaScript**: Interactive components
- **Images**: Movie posters, backdrops, avatars
- **Videos**: Trailers and promotional content
| `/analytics/` | analytics_dashboard | Staff analytics |
| `/collections/` | collections_list | Movie collections |
| `/genre/<name>/` | genre_movies | Movies by genre |
| `/actor/<name>/` | actor_movies | Movies by actor |
| `/director/<name>/` | director_movies | Movies by director |
| `/onboarding/` | onboarding | User onboarding |
| `/feedback/<id>/` | movie_feedback | Submit feedback |
| `/edit-profile/` | edit_profile | Edit profile |
| `/change-password/` | change_password | Change password |
| `/forgot-password/` | password_reset | Password reset |
| `/social/` | OAuth | Social authentication |
7. Create AIModelVersion record

#### SearchHistory
- **Purpose**: User search queries
- **Key Fields**: user (FK), query, searched_at

#### Collection
- **Purpose**: Curated movie collections
- **Key Fields**: name, slug, description, movies (M2M), created_at

#### WatchProgress
- **Purpose**: Resume playback position
- **Key Fields**: user (FK), movie (FK), progress, updated_at

#### DailyPick
- **Purpose**: Daily featured movie
- **Key Fields**: movie (FK), date, reason, is_active
3. **Strategy Pattern** - Multiple recommendation algorithms
4. **Observer Pattern** - Django signals for event handling
5. **Decorator Pattern** - Logging decorators, permission decorators
6. **Singleton Pattern** - LRU cache for model loading
7. **Factory Pattern** - Model creation in training pipeline
| Language | Python 3.12 |
| Framework | Django 6.0 |
| Database | MySQL 8.0 |
| Cache | Redis 7 |
| Task Queue | Celery 5.6 |
| ML/AI | PyTorch, FAISS, sentence-transformers, scikit-learn |
| Auth | social-auth-app-django (Google/GitHub OAuth), JWT |
| API | Django REST Framework |
| Frontend | HTML5, CSS3, JavaScript |
| Deployment | Docker Compose, Caddy, Gunicorn |
| CI/CD | GitHub Actions |