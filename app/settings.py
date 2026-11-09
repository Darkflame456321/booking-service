import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"{name} is required")
    return value


SECRET_KEY = required_env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
ROOT_URLCONF = "app.urls"
WSGI_APPLICATION = "app.wsgi.application"
INSTALLED_APPS = ["django.contrib.postgres", "rest_framework", "drf_spectacular", "app"]
MIDDLEWARE = ["app.middleware.JSONErrorMiddleware"]
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}]
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
if database_url := os.environ.get("DATABASE_URL"):
    database_config = dj_database_url.parse(
        database_url,
        conn_max_age=0,
        conn_health_checks=True,
    )
else:
    database_config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_env("POSTGRES_DB"),
        "USER": required_env("POSTGRES_USER"),
        "PASSWORD": required_env("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "15432"),
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
    }
DATABASES = {"default": database_config}
DATABASES["default"].setdefault("OPTIONS", {}).update(
    {
        "options": "-c statement_timeout=5000",
        "pool": {"min_size": 1, "max_size": 10, "timeout": 5},
    }
)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["app.parsers.ExactJSONParser", "app.parsers.UniqueFormParser"],
    "EXCEPTION_HANDLER": "app.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "COERCE_DECIMAL_TO_STRING": True,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Hotel Booking API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}
