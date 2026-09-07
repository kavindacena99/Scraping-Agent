"""Central Django and application configuration.

All environment access is intentionally confined to this module.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 0:
        raise ValueError(f"{name} must be zero or greater")
    return value


def env_float(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if value < 0:
        raise ValueError(f"{name} must be zero or greater")
    return value


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = env_bool("DEBUG", True)
if not DEBUG and (not SECRET_KEY or SECRET_KEY == "unsafe-development-key"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a strong value when DEBUG is false.")
ALLOWED_HOSTS = [item.strip() for item in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if item.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "research",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "mysql.connector.django",
        "NAME": os.getenv("DB_NAME", "website_research"),
        "USER": os.getenv("DB_USER", "research_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "EXCEPTION_HANDLER": "research.exceptions.api_exception_handler",
}

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN]

LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "openai").lower(),
    "model": os.getenv("LLM_MODEL", "gpt-4.1-mini"),
    "api_keys": {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "gemini": os.getenv("GEMINI_API_KEY", ""),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
    },
}
EMBEDDING_CONFIG = {
    "provider": os.getenv("EMBEDDING_PROVIDER", "openai").lower(),
    "model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    "api_keys": LLM_CONFIG["api_keys"],
}
CHROMA_CONFIG = {
    "persist_directory": str((PROJECT_ROOT / os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_data")).resolve()),
}
CRAWLER_CONFIG = {
    "user_agent": os.getenv("CRAWLER_USER_AGENT", "AIWebsiteResearchAgent/0.1 (+responsible-research)"),
    "timeout_seconds": env_float("CRAWLER_TIMEOUT_SECONDS", 15),
    "max_pages": max(1, env_int("CRAWLER_MAX_PAGES", 8)),
    "max_depth": env_int("CRAWLER_MAX_DEPTH", 2),
    "max_page_bytes": max(1024, env_int("CRAWLER_MAX_PAGE_BYTES", 2_000_000)),
    "max_redirects": env_int("CRAWLER_MAX_REDIRECTS", 4),
    "request_delay_seconds": env_float("CRAWLER_REQUEST_DELAY_SECONDS", 0.25),
}
AGENT_CONFIG = {
    "max_retrieval_retries": env_int("AGENT_MAX_RETRIEVAL_RETRIES", 2),
    "max_crawl_iterations": env_int("AGENT_MAX_CRAWL_ITERATIONS", 2),
    "retrieval_top_k": max(1, env_int("RETRIEVAL_TOP_K", 6)),
    "relevance_threshold": min(1.0, env_float("RELEVANCE_SCORE_THRESHOLD", 0.65)),
    "chunk_size": max(200, env_int("DOCUMENT_CHUNK_SIZE", 1000)),
    "chunk_overlap": env_int("DOCUMENT_CHUNK_OVERLAP", 150),
}
MAX_PROMPT_LENGTH = max(100, env_int("MAX_PROMPT_LENGTH", 4000))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "{asctime} {levelname} {name} event={message}",
            "style": "{",
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "structured"}},
    "loggers": {"research": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
