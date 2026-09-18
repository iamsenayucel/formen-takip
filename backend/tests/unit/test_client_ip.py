import asyncio

import pytest
from starlette.requests import Request

from app.core.client_ip import (
    TrustedProxyClientIPMiddleware,
    get_client_ip,
    parse_trusted_networks,
    select_client_from_forwarded_for,
)


def _run_middleware(trusted_proxies: str, client: tuple[str, int] | None, headers: list[tuple[bytes, bytes]]):
    captured_scope = {}

    async def inner_app(scope, receive, send):
        captured_scope.update(scope)

    middleware = TrustedProxyClientIPMiddleware(inner_app, trusted_proxies=trusted_proxies)
    scope = {"type": "http", "client": client, "headers": headers}

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        pass

    asyncio.run(middleware(scope, receive, send))
    return captured_scope


class TestParseTrustedNetworks:
    def test_parses_comma_separated_cidrs(self):
        networks = parse_trusted_networks("172.28.5.0/24, 10.0.0.1")
        assert len(networks) == 2

    def test_ignores_blank_and_invalid_entries(self):
        networks = parse_trusted_networks("172.28.5.0/24, , not-an-ip")
        assert len(networks) == 1

    def test_empty_string_yields_no_networks(self):
        assert parse_trusted_networks("") == []


class TestSelectClientFromForwardedFor:
    def test_single_ip_used_when_no_trusted_networks(self):
        assert select_client_from_forwarded_for("203.0.113.5", []) == "203.0.113.5"

    def test_strips_trailing_trusted_hops(self):
        networks = parse_trusted_networks("172.28.5.0/24")
        result = select_client_from_forwarded_for("203.0.113.5, 172.28.5.10, 172.28.5.20", networks)
        assert result == "203.0.113.5"

    def test_all_entries_trusted_returns_none(self):
        networks = parse_trusted_networks("172.28.5.0/24")
        result = select_client_from_forwarded_for("172.28.5.10, 172.28.5.20", networks)
        assert result is None

    def test_ipv6_client_is_selected(self):
        networks = parse_trusted_networks("172.28.5.0/24")
        result = select_client_from_forwarded_for("2001:db8::1, 172.28.5.10", networks)
        assert result == "2001:db8::1"


class TestTrustedProxyClientIPMiddleware:
    def test_trusted_proxy_single_forwarded_ip_is_used(self):
        scope = _run_middleware(
            "172.28.5.0/24",
            ("172.28.5.10", 12345),
            [(b"x-forwarded-for", b"203.0.113.5")],
        )
        assert scope["client"][0] == "203.0.113.5"

    def test_trusted_proxy_multiple_forwarded_ips_selects_real_client(self):
        scope = _run_middleware(
            "172.28.5.0/24",
            ("172.28.5.10", 12345),
            [(b"x-forwarded-for", b"203.0.113.5, 172.28.5.10")],
        )
        assert scope["client"][0] == "203.0.113.5"

    def test_untrusted_direct_peer_spoofed_header_is_ignored(self):
        scope = _run_middleware(
            "172.28.5.0/24",
            ("198.51.100.9", 12345),
            [(b"x-forwarded-for", b"6.6.6.6")],
        )
        assert scope["client"][0] == "198.51.100.9"

    def test_trusted_proxy_without_forwarded_header_falls_back_to_direct_peer(self):
        scope = _run_middleware("172.28.5.0/24", ("172.28.5.10", 12345), [])
        assert scope["client"][0] == "172.28.5.10"

    def test_no_client_on_scope_does_not_raise(self):
        scope = _run_middleware("172.28.5.0/24", None, [(b"x-forwarded-for", b"203.0.113.5")])
        assert scope["client"] is None

    def test_ipv6_direct_client_behind_trusted_proxy(self):
        scope = _run_middleware(
            "172.28.5.0/24",
            ("172.28.5.10", 12345),
            [(b"x-forwarded-for", b"2001:db8::42, 172.28.5.10")],
        )
        assert scope["client"][0] == "2001:db8::42"


class TestGetClientIp:
    def test_returns_host_when_client_present(self):
        request = Request(scope={"type": "http", "client": ("203.0.113.5", 12345), "headers": []})
        assert get_client_ip(request) == "203.0.113.5"

    def test_returns_none_when_client_missing(self):
        request = Request(scope={"type": "http", "client": None, "headers": []})
        assert get_client_ip(request) is None
