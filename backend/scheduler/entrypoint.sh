#!/bin/sh
set -eu

echo "formen-scheduler: starting cron — reconcile-stale-jobs every 15m, generate-monthly-reports + send-monthly-report-emails monthly on day 1 (see scheduler/README.md)."
echo "formen-scheduler: run exactly one instance of this service — jobs are not lock-protected against a second concurrent scheduler."

# cron kendi sınırlı env'iyle çalışır; container env'ini her job'ın source
# ettiği dosyaya yazıyoruz. `printenv | sed` boşluk ve çok satırlı PEM
# değerlerini bozar; shlex.quote her değeri POSIX uyumlu tek token yapar.
python3 -c '
import os
import shlex

with open("/etc/formen-scheduler.env", "w") as f:
    for name, value in os.environ.items():
        f.write(f"export {name}={shlex.quote(value)}\n")
'
chmod 600 /etc/formen-scheduler.env

exec cron -f
