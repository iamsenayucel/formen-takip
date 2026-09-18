from __future__ import annotations

import ipaddress
from typing import Iterable

from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def parse_trusted_networks(value: str) -> list[IPNetwork]:
    networks: list[IPNetwork] = []
    for raw in value.split(","):
        candidate = raw.strip()
        if not candidate:
            continue
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            continue
    return networks


def _is_trusted_host(host: str | None, networks: Iterable[IPNetwork]) -> bool:
    if not host:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(address in network for network in networks)


def select_client_from_forwarded_for(forwarded_for: str, trusted_networks: Iterable[IPNetwork]) -> str | None:
    hosts = [item.strip() for item in forwarded_for.split(",") if item.strip()]
    for host in reversed(hosts):
        if not _is_trusted_host(host, trusted_networks):
            return host
    return None


class TrustedProxyClientIPMiddleware:
    def __init__(self, app: ASGIApp, trusted_proxies: str) -> None:
        self.app = app
        self.trusted_networks = parse_trusted_networks(trusted_proxies)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.trusted_networks:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        direct_host = client[0] if client else None

        if _is_trusted_host(direct_host, self.trusted_networks):
            headers = dict(scope.get("headers") or [])
            forwarded_for = headers.get(b"x-forwarded-for")
            if forwarded_for:
                resolved = select_client_from_forwarded_for(
                    forwarded_for.decode("latin-1"), self.trusted_networks
                )
                if resolved is not None:
                    scope = dict(scope)
                    scope["client"] = (resolved, 0)

        await self.app(scope, receive, send)


def get_client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
