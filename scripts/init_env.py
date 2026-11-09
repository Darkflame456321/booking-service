import os
import secrets
from pathlib import Path


def create_env(root: Path) -> None:
    template = (root / ".env.example").read_text(encoding="utf-8")
    content = template.replace(
        "replace-with-random-postgres-password", secrets.token_urlsafe(32)
    ).replace("replace-with-random-django-secret-key", secrets.token_urlsafe(48))
    descriptor = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as env_file:
        env_file.write(content)


if __name__ == "__main__":
    try:
        create_env(Path(__file__).resolve().parent.parent)
    except FileExistsError:
        print(".env already exists; existing settings were preserved.")
    else:
        print(".env created with generated credentials. Keep this file private.")
