from pathlib import Path

import pytest
from dotenv import dotenv_values

from scripts.init_env import create_env


def test_generated_env_contains_secrets_instead_of_placeholders(tmp_path):
    template = Path(".env.example").read_text(encoding="utf-8")
    (tmp_path / ".env.example").write_text(template, encoding="utf-8")
    create_env(tmp_path)
    values = dotenv_values(tmp_path / ".env")
    assert len(values["POSTGRES_PASSWORD"]) >= 32
    assert len(values["DJANGO_SECRET_KEY"]) >= 48
    assert "replace-with-random" not in (tmp_path / ".env").read_text(encoding="utf-8")


def test_existing_env_is_never_overwritten(tmp_path):
    (tmp_path / ".env.example").write_text(
        "POSTGRES_PASSWORD=replace-with-random-postgres-password"
    )
    existing = tmp_path / ".env"
    existing.write_text("preserve existing settings", encoding="utf-8")
    with pytest.raises(FileExistsError):
        create_env(tmp_path)
    assert existing.read_text(encoding="utf-8") == "preserve existing settings"
