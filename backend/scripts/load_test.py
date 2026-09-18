"""Minimal, dependency-free (yalnızca httpx) load test aracı.

Repository'de bir load/performance test altyapısı bulunmadığı için CLAUDE.md
AŞAMA 8'e göre eklendi. CI'ın parçası DEĞİLDİR — ayrı, açıkça manuel çalıştırılan
bir araçtır ve çalışan bir stack (docker compose up) gerektirir.

Kullanım (backend/ dizininden, .venv aktifken):

    python scripts/load_test.py --base-url http://localhost:8000 \
        --endpoint /api/v1/foremen --concurrency 10 20 40 60 100 --requests 200

Yalnızca senkron I/O'yu (DB pool + endpoint latency) ölçer; iş kurallarını,
skorları veya RBAC kapsamını değiştirmez ve doğrulamaz. Sentetik/seed veriye
karşı çalıştırılmalıdır — gerçek üretim verisine karşı KOŞMAYIN.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class _Result:
    latencies_ms: list[float] = field(default_factory=list)
    statuses: dict[int, int] = field(default_factory=dict)
    errors: int = 0
    error_types: dict[str, int] = field(default_factory=dict)
    pool_timeouts: int = 0


async def _worker(
    client: httpx.AsyncClient, url: str, params: dict, n: int, result: _Result, lock: asyncio.Lock
) -> None:
    for _ in range(n):
        started = time.perf_counter()
        try:
            resp = await client.get(url, params=params, timeout=60.0)
        except httpx.HTTPError as exc:
            async with lock:
                result.errors += 1
                name = type(exc).__name__
                result.error_types[name] = result.error_types.get(name, 0) + 1
            continue
        elapsed_ms = (time.perf_counter() - started) * 1000
        async with lock:
            result.latencies_ms.append(elapsed_ms)
            result.statuses[resp.status_code] = result.statuses.get(resp.status_code, 0) + 1
            if resp.status_code == 503:
                try:
                    if resp.json().get("error", {}).get("code") == "DB_POOL_EXHAUSTED":
                        result.pool_timeouts += 1
                except ValueError:
                    pass


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, int(round(pct / 100 * (len(sorted_values) - 1))))
    return sorted_values[idx]


async def _run_one_level(
    base_url: str, endpoint: str, params: dict, concurrency: int, total_requests: int, headers: dict
) -> _Result:
    result = _Result()
    lock = asyncio.Lock()
    per_worker = max(1, total_requests // concurrency)
    limits = httpx.Limits(max_connections=concurrency + 5, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(base_url=base_url, headers=headers, limits=limits) as client:
        started = time.perf_counter()
        await asyncio.gather(
            *[_worker(client, endpoint, params, per_worker, result, lock) for _ in range(concurrency)]
        )
        wall_seconds = time.perf_counter() - started
    result.wall_seconds = wall_seconds  # type: ignore[attr-defined]
    return result


def _print_report(endpoint: str, concurrency: int, total_requests: int, result: _Result) -> None:
    latencies = sorted(result.latencies_ms)
    n_ok = sum(v for k, v in result.statuses.items() if k < 400)
    n_err = sum(v for k, v in result.statuses.items() if k >= 400) + result.errors
    wall = getattr(result, "wall_seconds", 0.0)
    rps = (len(latencies) / wall) if wall > 0 else 0.0
    print(
        f"| {concurrency:>11} | {rps:>6.1f} | {_percentile(latencies, 50):>6.0f} | "
        f"{_percentile(latencies, 95):>6.0f} | {_percentile(latencies, 99):>6.0f} | "
        f"{max(latencies) if latencies else 0:>8.0f} | {n_err:>5} | {result.pool_timeouts:>13} |"
    )
    if n_ok == 0:
        print(
            f"  UYARI: {endpoint} concurrency={concurrency} için hiç başarılı istek yok. "
            f"Statuses={result.statuses} error_types={result.error_types}"
        )


async def main_async(args: argparse.Namespace) -> None:
    headers = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    print(f"\n=== Endpoint: {args.endpoint} (params={args.param}) ===")
    print(f"Ortam: {args.base_url} (bu betik yalnızca LOCAL/TEST ortamına karşı çalıştırılmalıdır)")
    print("| concurrency |   rps  |   p50  |   p95  |   p99  |   max ms |  err  | pool_timeouts |")
    print("|-------------|--------|--------|--------|--------|----------|-------|---------------|")
    params = dict(p.split("=", 1) for p in args.param) if args.param else {}
    for c in args.concurrency:
        result = await _run_one_level(args.base_url, args.endpoint, params, c, args.requests, headers)
        _print_report(args.endpoint, c, args.requests, result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--endpoint", default="/api/v1/foremen")
    parser.add_argument("--param", action="append", help="ek query param, key=value (tekrarlanabilir)")
    parser.add_argument("--concurrency", type=int, nargs="+", default=[10, 20, 40, 60, 100])
    parser.add_argument("--requests", type=int, default=200, help="concurrency seviyesi başına toplam istek")
    parser.add_argument("--token", default=None, help="Authorization: Bearer <token> (auth_bypass yoksa gerekli)")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
