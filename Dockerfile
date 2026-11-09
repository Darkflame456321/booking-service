FROM python:3.13-slim AS tooling
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR /app
RUN pip install --no-cache-dir poetry==2.2.1
COPY pyproject.toml poetry.lock ./

FROM tooling AS development
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"
RUN poetry install --no-root --no-interaction
COPY app ./app
COPY tests ./tests
COPY db ./db
COPY manage.py ./
COPY scripts ./scripts
COPY .env.example ./

FROM tooling AS dependencies
RUN poetry install --only main --no-root --no-interaction

FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN useradd --uid 10001 --create-home booking
COPY --from=dependencies /app/.venv /app/.venv
COPY app ./app
COPY manage.py ./
USER booking
EXPOSE 9000
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:9000", "--workers", "1", "--threads", "8", "--access-logfile", "-", "--error-logfile", "-"]
