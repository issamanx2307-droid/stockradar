"""
การตั้งค่า Django สำหรับระบบ Radar หุ้น
"""

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "localhost,127.0.0.1"
).split(",")

# ---------------------------------------------------------------------------
# แอปพลิเคชัน
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "jazzmin",
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    # แอปหลัก
    "radar",
    "channels",
    "engine_api",
    "django_celery_beat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "stockradar.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "stockradar.wsgi.application"
ASGI_APPLICATION = "stockradar.asgi.application"

# ---------------------------------------------------------------------------
# Channel Layers — ใช้ InMemory (ไม่ต้องการ Redis)
# ถ้ามี Redis ให้เปลี่ยนเป็น channels_redis.core.RedisChannelLayer
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# ---------------------------------------------------------------------------
# ฐานข้อมูล — SQLite สำหรับ dev, PostgreSQL สำหรับ production
# ---------------------------------------------------------------------------

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get(
            "DATABASE_URL",
            f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
        ),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------------------------
# Cache + Celery (Redis)
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "")

# Cache: Redis ถ้ามี, fallback เป็น LocMem
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 300,
        }
    }
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
    # Celery Broker + Result Backend (Redis)
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
    # Celery fallback (local dev)
    CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/0"

# Celery shared settings
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Bangkok"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/day",
    },
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}

# ---------------------------------------------------------------------------
# Allauth / Subscription Settings
# ---------------------------------------------------------------------------

SITE_ID = 1
ACCOUNT_EMAIL_VERIFICATION  = "none"
ACCOUNT_LOGIN_METHODS        = {"email"}
ACCOUNT_SIGNUP_FIELDS        = ["email*", "password1*", "password2*"]

# Google OAuth
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id":     os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret":        os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "key":           "",
        },
        "SCOPE":       ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}
SOCIALACCOUNT_AUTO_SIGNUP        = True   # สร้าง user อัตโนมัติ
SOCIALACCOUNT_EMAIL_REQUIRED     = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# ---------------------------------------------------------------------------
# CORS — อนุญาต React dev server
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # production HTTPS defaults (overridden by CORS_ORIGINS env var)
    "https://radarhoon.com",
    "https://www.radarhoon.com",
] + [
    o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
]
CORS_ALLOW_ALL_ORIGINS = DEBUG

# CSRF Trusted Origins — ต้องมีเมื่อใช้ HTTPS หรืออยู่หลัง reverse proxy
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "https://radarhoon.com,https://www.radarhoon.com"
    ).split(",") if o.strip()
]

# Security headers (production)
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER      = True
    SECURE_CONTENT_TYPE_NOSNIFF    = True
    X_FRAME_OPTIONS                = "DENY"
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    # บอก Django ว่าอยู่หลัง Nginx proxy — ใช้ X-Forwarded-Proto header
    SECURE_PROXY_SSL_HEADER        = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# ภาษาและเวลา
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "th"
TIME_ZONE = "Asia/Bangkok"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# การตั้งค่า Data Pipeline
# ---------------------------------------------------------------------------

PRICE_HISTORY_DAYS = int(os.environ.get("PRICE_HISTORY_DAYS", 365))

# Token สำหรับ GitHub Actions ส่งข้อมูลราคาเข้า VPS
# ตั้งค่าใน .env: IMPORT_API_TOKEN=<random_secret>
IMPORT_API_TOKEN = os.environ.get("IMPORT_API_TOKEN", "")
SUPPORTED_EXCHANGES = ["SET", "NASDAQ", "NYSE"]
PRICE_LOAD_BATCH_SIZE = int(os.environ.get("PRICE_LOAD_BATCH_SIZE", 50))

# ---------------------------------------------------------------------------
# Jazzmin Settings (Admin UI Customization)
# ---------------------------------------------------------------------------

JAZZMIN_SETTINGS = {
    "site_title": "Radar หุ้น",
    "site_header": "📡 Radar หุ้น",
    "site_brand": "📡 Radar",
    "site_logo": None,
    "site_logo_classes": "img-circle",
    "site_icon": None,
    "welcome_sign": "ยินดีต้อนรับสู่ระบบจัดการ Radar หุ้น",
    "copyright": "Radar Stock System",
    "search_model": ["radar.Symbol", "auth.User"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "🌐 หน้าเว็บ", "url": "http://localhost:5173", "new_window": True},
        {"name": "📊 Admin", "url": "admin:index", "permissions": ["auth.view_user"]},
    ],
    "usermenu_links": [
        {"name": "🌐 เปิดหน้าเว็บ", "url": "http://localhost:5173", "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": ["radar", "auth"],
    "icons": {
        "auth":                     "fas fa-shield-alt",
        "auth.user":                "fas fa-user-circle",
        "auth.Group":               "fas fa-users",
        "radar.Symbol":             "fas fa-chart-line",
        "radar.PriceDaily":         "fas fa-coins",
        "radar.Indicator":          "fas fa-wave-square",
        "radar.Signal":             "fas fa-bolt",
        "radar.Profile":            "fas fa-id-badge",
        "radar.BusinessProfile":    "fas fa-building",
        "radar.StockTerm":          "fas fa-book-open",
        "radar.TermQuestion":       "fas fa-question-circle",
        "radar.PositionAnalysis":   "fas fa-balance-scale",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "language_chooser": False,
}

JAZZMIN_UI_CONFIG = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": True,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-teal",
    "navbar": "navbar-dark navbar-primary",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_fixed": True,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-teal",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary":   "btn-primary",
        "secondary": "btn-secondary",
        "info":      "btn-outline-info",
        "warning":   "btn-outline-warning",
        "danger":    "btn-outline-danger",
        "success":   "btn-success",
    },
}
