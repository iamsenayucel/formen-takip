FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Scheduler ayrı stage'dir; API image'ına cron eklemez.
# Sistem crontab kurulumu ve daemon için root gerekir; app.cli ek yetki kullanmaz.
FROM base AS scheduler

RUN apt-get update && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*
COPY scheduler/crontab /etc/cron.d/formen-scheduler
RUN chmod 0644 /etc/cron.d/formen-scheduler && crontab /etc/cron.d/formen-scheduler
COPY scheduler/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]

# Varsayılan target runtime'dır; çıplak docker build de doğru stage'i üretir.
FROM base AS runtime

# Backend ek yetki gerektirmez; non-root kullanıcı 8000 portunu ve /app'i kullanır.
RUN groupadd --system app && useradd --system --gid app --home /app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
