
import os
from pathlib import Path
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-2wc3_ftvs2(cyo66l=ee8o90gkt_q!c=hb(4s00#gm2cfk@z(+'  # fallback for dev only
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Parse ALLOWED_HOSTS from environment, strip whitespace, and add ngrok support
_allowed_hosts = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts]

# Add ngrok domain pattern support for tunneling
ALLOWED_HOSTS.extend([
    '*.ngrok-free.dev',
    '.ngrok-free.dev',
    'ngrok-free.dev',
])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'platform_engine.apps.PlatformEngineConfig',

    # instaled third-party packages
    'rest_framework',
    'corsheaders',
    'django_extensions',
    'social_django',

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
    'platform_engine.utils.logging.RequestLoggingMiddleware',  # Request logging
    'platform_engine.utils.security.SecurityHeadersMiddleware',  # Security headers
    'platform_engine.utils.security.RateLimitMiddleware',  # Rate limiting
    'platform_engine.utils.security.RequestValidationMiddleware',  # Request validation
    # 'platform_engine.utils.security.IPWhitelistMiddleware',  # Uncomment for IP whitelist
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


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

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


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Increased from default 8 for better security
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

STATIC_ROOT = BASE_DIR / "staticfiles"

CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'http://127.0.0.1:8000,http://localhost:8000,https://elke-unelongated-lorna.ngrok-free.dev'
).split(',')

# Store the CSRF token server-side in the session instead of a browser
# cookie ("double submit" fallback). Rationale (Aug 2026 debugging): this
# machine's browser persistently refused to keep Django's `csrftoken`
# cookie on localhost, causing endless "CSRF cookie not set" failures even
# though the server sent it correctly on every response. Session-backed
# CSRF removes that dependency entirely - {% csrf_token %} renders the
# token straight from the session into the hidden form field.
# NOTE for production: anonymous visitors loading form pages will each
# create a session row; flip to False via .env under heavy traffic.
CSRF_USE_SESSIONS = os.getenv('CSRF_USE_SESSIONS', 'True').lower() == 'true'

# CORS Configuration - Restricted by environment variable
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000'
).split(',')

# CORS remains restricted by default, including during development. Opt in
# explicitly only for short-lived local debugging sessions.
CORS_ALLOW_ALL_ORIGINS = (
    DEBUG
    and os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() == 'true'
)

# ===========================
# LOCAL HTTPS DEVELOPMENT
# ===========================
# Set USE_HTTPS=True in .env and start via ./run_https.sh
# (runserver_plus with certs/localhost.pem).
USE_HTTPS = os.getenv('USE_HTTPS', 'False').lower() == 'true'
if USE_HTTPS:
    # Trust the https variants even if CSRF_TRUSTED_ORIGINS in .env is stale.
    _https_origins = ('https://localhost:8000', 'https://127.0.0.1:8000')
    CSRF_TRUSTED_ORIGINS = list(
        dict.fromkeys([o.strip() for o in CSRF_TRUSTED_ORIGINS] + list(_https_origins))
    )
    # Secure cookies stay OFF while DEBUG=True so the site keeps working
    # even if someone briefly serves it over plain http locally. In
    # production (DEBUG=False) the env-driven block below controls these.
    if not DEBUG:
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True

# Security headers for production
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True').lower() == 'true'
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() == 'true'
    SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True').lower() == 'true'

LOGIN_URL = "login"

LOGIN_REDIRECT_URL = "homepage"

LOGOUT_REDIRECT_URL = "landing"

# ===========================
# SOCIAL AUTH (GOOGLE & GITHUB)
# ===========================
# Credentials come from .env; a provider with missing key/secret is simply
# not offered on the login/signup pages (see views._get_social_providers).
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.github.GithubOAuth2",
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", "")
SOCIAL_AUTH_GITHUB_KEY = os.getenv("SOCIAL_AUTH_GITHUB_KEY", "")
SOCIAL_AUTH_GITHUB_SECRET = os.getenv("SOCIAL_AUTH_GITHUB_SECRET", "")

SOCIAL_AUTH_URL_NAMESPACE = "social"
SOCIAL_AUTH_LOGIN_REDIRECT_URL = LOGIN_REDIRECT_URL
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    # Link the social login to an existing account that already uses the
    # same email address instead of raising a duplicate-account error.
    "social_core.pipeline.social_auth.associate_by_email",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)

#=========================
# EMAIL CONFIGURATION
#=========================

EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'LuminaRecs <noreply@luminarecs.com>'
)

#=========================
#REDIS CACHE
#=========================

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

CRONJOBS = [

    (
        "0 3 * * *",
        "django.core.management.call_command",
        ["retrain_ai"]
    )
]

# ===========================
# SENTRY ERROR TRACKING
# ===========================

SENTRY_DSN = os.getenv('SENTRY_DSN', '')

if SENTRY_DSN and not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    # Configure logging integration
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            sentry_logging,
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production' if not DEBUG else 'development',
        max_breadcrumbs=50,
        attach_stacktrace=True,
    )

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
            # Keep the development server readable; detailed events remain in
            # rotating log files when LOG_LEVEL is set to DEBUG.
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
