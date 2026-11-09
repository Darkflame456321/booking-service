import os
import runpy
import secrets
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import pytest
from django.core.exceptions import ImproperlyConfigured


@pytest.fixture
def config_env():
    return {
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(48),
        "POSTGRES_DB": "test_database",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
    }


def load_settings(env):
    with patch.dict(os.environ, env, clear=True), patch("dotenv.load_dotenv"):
        return runpy.run_path(str(Path("app/settings.py")))


def test_secret_key_is_required(config_env):
    del config_env["DJANGO_SECRET_KEY"]
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY is required"):
        load_settings(config_env)


def test_database_password_has_no_fallback(config_env):
    del config_env["POSTGRES_PASSWORD"]
    with pytest.raises(ImproperlyConfigured, match="POSTGRES_PASSWORD is required"):
        load_settings(config_env)


def test_component_password_keeps_special_characters(config_env):
    config_env["POSTGRES_PASSWORD"] += "@:/?#"
    result = load_settings(config_env)
    assert result["DATABASES"]["default"]["PASSWORD"] == config_env["POSTGRES_PASSWORD"]


def test_database_url_overrides_components(config_env):
    password = secrets.token_urlsafe(32) + "@:/?#"
    config_env["DATABASE_URL"] = f"postgres://other:{quote(password, safe='')}@db:5432/other"
    result = load_settings(config_env)["DATABASES"]["default"]
    assert result["NAME"] == "other"
    assert result["USER"] == "other"
    assert result["PASSWORD"] == password
