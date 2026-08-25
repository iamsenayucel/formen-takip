# Scheduler

Runs three periodic CLI jobs (`app/cli.py`) that otherwise nobody would ever trigger in production:

| Job | Schedule (Europe/Istanbul) | Idempotent? |
|---|---|---|
| `reconcile-stale-jobs` | every 15 min | Pure watchdog scan — no-op unless a job is actually stuck past its timeout |
| `generate-monthly-reports` | day 1, 02:00 | Yes — skips foreman+month combinations that already exist |
| `send-monthly-report-emails` | day 1, 03:00 | Yes by default — `SENT` reports are not resent (would need `--retry-failed`) |

Times are pinned to business local time via `CRON_TZ=Europe/Istanbul` at the top of the `crontab` file (Karaman is a single location, matching `app/core/config.py`'s `timezone` default) — not the container's own clock, which is UTC in the base image.

## Why cron, not Celery/Redis/a Kubernetes CronJob

Three jobs, none needing sub-minute precision or distributed coordination, on an app that is
explicitly single-replica by design (see root `CLAUDE.md`). Redis+Celery or a k8s CronJob would
add operational surface (a broker to run and monitor, a second deployment target) with no
matching benefit here. `cron` inside a container reuses the exact same image and Python
environment as the backend — no new dependency, no new thing to keep alive.

## Run exactly one instance

These jobs are not lock-protected against a second concurrent scheduler container:
`generate-monthly-reports` and `send-monthly-report-emails` are idempotent per run so a duplicate
trigger mostly self-corrects, but `send-monthly-report-emails` racing with `--retry-failed` against
itself could still send a duplicate email in a narrow window. Don't `docker compose up --scale
scheduler=2`, and don't run the `scheduler` service on more than one host.

## Enabling it

Off by default — the `scheduler` service only starts with the `scheduler` Compose profile:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile scheduler up -d
```

(add `-f docker-compose.db.yml` too if Postgres runs on this same host). It shares its
environment with `backend` via the `x-backend-env` anchor in `docker-compose.yml`, so anything
that reaches the backend (`DATABASE_URL`, `SMTP_*`, `CLOUDFRONT_PRIVATE_KEY`, ...) reaches the
scheduler identically — cron itself gives jobs a near-empty environment regardless, so
`entrypoint.sh` dumps the container's real environment into a file each crontab line sources;
that dump goes through Python's `shlex.quote` (not raw `printenv`) specifically so a value with
spaces or a multi-line PEM key like `CLOUDFRONT_PRIVATE_KEY` survives intact instead of being
truncated or split into bogus lines.
`docker-compose.prod.yml` gives this service `restart: unless-stopped`, same as `backend`/
`frontend`/`edge` — without it, a crash or host reboot would silently stop the scheduler and
nobody would notice until a monthly report or email failed to go out.

## Running a job manually

Same as any other CLI command — no need to wait for the schedule:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec scheduler python -m app.cli reconcile-stale-jobs
```

## Logs

`crontab` redirects each job's stdout/stderr to `/proc/1/fd/1` / `/proc/1/fd/2` (cron itself is
PID 1 in this container), so `docker compose logs scheduler` shows job output — cron would
otherwise try to email it, which isn't configured and would silently discard it.
