import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ===========================
# CORE CONFIGURATION
# ===========================

# SECURITY WARNING: keep the secret key used in production secret!
# Fail fast if SECRET_KEY is not set in production - no insecure fallback.
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is required. "
        "Set it in your .env file or environment before starting the server."
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ===========================
# APPLICATION DEFINITION
# ===========================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'platform_engine.apps.PlatformEngineConfig',

    # Installed third-party packages
    'rest_framework',
    'corsheaders',
    'django_extensions',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ===========================
# DATABASE CONFIGURATION
# ===========================

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.getenv('DB_NAME', 'luminarecs_db'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}

# ===========================
# PASSWORD VALIDATION
# ===========================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Increased from default 8
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ===========================
# INTERNATIONALIZATION
# ===========================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ===========================
# STATIC FILES
# ===========================

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ===========================
# SECURITY SETTINGS
# ===========================

CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'http://127.0.0.1:8000,http://localhost:8000,https://elke-unelongated-lorna.ngrok-free.dev',
).split(',')

# CORS Configuration
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000',

).split(',')

# CORS remains restricted by default, including during development. Opt in
# explicitly only for short-lived local debugging sessions.
CORS_ALLOW_ALL_ORIGINS = (
    DEBUG
    and os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() == 'true'
)

# Security headers for production
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True').lower() == 'true'
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() == 'true'
    SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True').lower() == 'true'
    SECURE_CONTENT_SECURITY_POLICY = {
        'DEFAULT_SRC': ("'self'",),
        'SCRIPT_SRC': ("'self'", "'unsafe-inline'"),
        'STYLE_SRC': ("'self'", "'unsafe-inline'"),
        'IMG_SRC': ("'self'", "data:", "https:"),
    }

# ===========================
# AUTHENTICATION & ROUTING
# ===========================

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "homepage"
LOGOUT_REDIRECT_URL = "landing"

# ===========================
# CACHE CONFIGURATION
# ===========================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        }
    }
}

# Cache TTL for recommendations (in seconds)
CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))

# ===========================
# CELERY CONFIGURATION
# ===========================

CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ===========================
# LOGGING CONFIGURATION
# ===========================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'luminarecs.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'platform_engine': {
            'handlers': ['console', 'file', 'error_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

# ===========================
# SENTRY ERROR TRACKING
# ===========================

SENTRY_DSN = os.getenv('SENTRY_DSN', '')

if SENTRY_DSN and not DEBUG:
    import sentry_sdk 
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production' if not DEBUG else 'development'
    )

# ===========================
# REST FRAMEWORK CONFIGURATION
# ===========================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
    'EXCEPTION_HANDLER': 'platform_engine.utils.exceptions.custom_exception_handler',
}

# ===========================
# SIMPLE JWT CONFIGURATION
# ===========================

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ===========================
# ML/AI CONFIGURATION
# ===========================

EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
FAISS_INDEX_PATH = os.path.join(BASE_DIR, os.getenv('FAISS_INDEX_PATH', 'ml_models/movie_index.faiss'))
RECOMMENDATION_CACHE_TTL = int(os.getenv('RECOMMENDATION_CACHE_TTL', '3600'))

# ===========================
# CRONJOBS CONFIGURATION
# ===========================

CRONJOBS = [
    (
        "0 3 * * *",
        "django.core.management.call_command",
        ["retrain_ai"]
    )
]
