FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SERVE_STATIC=1 \
    DJANGO_DB_PATH=/data/db.sqlite3

WORKDIR /app

COPY requirements.txt requirements-production.txt ./
RUN pip install --no-cache-dir -r requirements-production.txt \
    && groupadd --system --gid 10001 web \
    && useradd --system --uid 10001 --gid web --no-create-home web \
    && install -d -o web -g web /data

COPY manage.py ./
COPY heat_empire ./heat_empire
COPY templates ./templates
COPY static ./static
COPY deploy/healthcheck.py deploy/backup.py ./
COPY --chmod=755 deploy/entrypoint.sh /usr/local/bin/heat-entrypoint
RUN DJANGO_SECRET_KEY=collectstatic-build-only python manage.py collectstatic --noinput

USER web
EXPOSE 8000
ENTRYPOINT ["heat-entrypoint"]
CMD ["gunicorn", "heat_empire.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-"]
