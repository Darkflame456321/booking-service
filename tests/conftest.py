import os
from copy import deepcopy
from pathlib import Path
from unittest.mock import create_autospec
from uuid import uuid4

import dj_database_url
import httpx
import psycopg
import pytest
from django.db import connections
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app.db import Repository
from app.wsgi import application


@pytest.fixture
def repository_mock():
    return create_autospec(Repository, instance=True)


@pytest.fixture
def client(repository_mock, monkeypatch):
    monkeypatch.setattr("app.views.get_repository", lambda: repository_mock)
    with httpx.Client(
        transport=httpx.WSGITransport(app=application), base_url="http://localhost"
    ) as http_client:
        yield http_client


@pytest.fixture
def test_database_config():
    config = deepcopy(connections["default"].settings_dict)
    if dsn := os.environ.get("TEST_DATABASE_URL"):
        config.update(dj_database_url.parse(dsn))
    elif os.environ.get("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("set RUN_INTEGRATION_TESTS=1 or TEST_DATABASE_URL to run integration tests")
    dsn = make_conninfo(
        dbname=config["NAME"],
        user=config["USER"],
        password=config["PASSWORD"],
        host=config["HOST"],
        port=config["PORT"],
        **{key: value for key, value in config.get("OPTIONS", {}).items() if key.startswith("ssl")},
    )
    return config, dsn


@pytest.fixture
def repository(django_db_blocker, test_database_config):
    config, dsn = test_database_config
    schema = "test_" + uuid4().hex
    with django_db_blocker.unblock(), psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute("CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public")
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        wrapper = connections["default"]
        wrapper.close()
        wrapper.close_pool()
        original = wrapper.settings_dict
        config.setdefault("OPTIONS", {}).update(
            {
                "options": f"-c search_path={schema},public -c statement_timeout=5000",
                "pool": {"min_size": 1, "max_size": 10, "timeout": 5},
            }
        )
        config["CONN_MAX_AGE"] = 0
        connections.settings["default"] = config
        wrapper.settings_dict = config
        try:
            with wrapper.cursor() as cursor:
                cursor.execute(Path("db/schema.sql").read_text(encoding="utf-8"))
            yield Repository()
        finally:
            wrapper.close()
            wrapper.close_pool()
            connections.settings["default"] = original
            wrapper.settings_dict = original
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def integration_client(repository):
    with httpx.Client(
        transport=httpx.WSGITransport(app=application), base_url="http://localhost"
    ) as http_client:
        yield http_client
