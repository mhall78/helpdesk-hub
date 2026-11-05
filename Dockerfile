FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATABASE_PATH=/data/helpdesk.db

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run as a non-root user; /data holds the SQLite file.
RUN useradd --create-home appuser && mkdir -p /data && chown appuser /data
USER appuser

EXPOSE 8000
# Render sets $PORT; locally it defaults to 8000.
# --preload runs create_app() (table setup + demo data) once, before the workers start.
CMD gunicorn --preload --bind 0.0.0.0:${PORT} --workers 2 --access-logfile - "app:create_app()"
