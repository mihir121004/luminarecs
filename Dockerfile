FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System tools needed at build time (faiss/torch build wheels and gunicorn).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn

COPY . .

# Static files collected at build time (faster cold start); ownership fixed
# so the unprivileged runtime user can still re-collect on boot.
RUN python manage.py collectstatic --noinput \
 && addgroup --system --gid 1000 app \
 && adduser --system --uid 1000 --ingroup app app \
 && mkdir -p /app/media /app/staticfiles \
 && chown -R app:app /app/staticfiles /app/media

# Run as unprivileged user from here on.
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS -o /dev/null http://127.0.0.1:8000/ || exit 1

CMD ["sh", "/app/entrypoint.sh"]