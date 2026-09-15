"""Outbound webhook URL validation (SSRF guard)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.exceptions.http_exceptions import ValidationException


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def _validate_resolved_ips(ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address]) -> None:
    if not ips:
        raise ValidationException(
            message_key="errors.validation",
            params={"message": "Invalid webhook URL"},
        )
    for ip in ips:
        if _is_blocked_ip(ip):
            raise ValidationException(
                message_key="errors.validation",
                params={"message": "Invalid webhook URL"},
            )


def _resolve_hostname_sync(hostname: str, *, port: int = 443) -> None:
    try:
        addrinfo = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValidationException(
            message_key="errors.validation",
            params={"message": "Invalid webhook URL"},
        ) from exc

    seen: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for _family, _type, _proto, _canonname, sockaddr in addrinfo:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip not in seen:
            seen.add(ip)
            ips.append(ip)
    _validate_resolved_ips(ips)


def validate_outbound_webhook_url(url: str) -> str:
    """Validate a customer webhook URL before save or delivery."""
    cleaned = (url or "").strip()
    if not cleaned or len(cleaned) > 2000:
        raise ValidationException(
            message_key="errors.validation",
            params={"message": "Invalid webhook URL"},
        )

    parsed = urlparse(cleaned)
    if parsed.scheme != "https":
        raise ValidationException(
            message_key="errors.validation",
            params={"message": "Invalid webhook URL"},
        )
    if parsed.username or parsed.password:
        raise ValidationException(
            message_key="errors.validation",
            params={"message": "Invalid webhook URL"},
        )
    if not parsed.hostname:
        raise ValidationException(
            message_key="errors.validation",
            params={"message": "Invalid webhook URL"},
        )

    host = parsed.hostname.lower()
    if host in {"localhost"} or host.endswith(".localhost"):
        raise ValidationException(
            message_key="errors.validation",
            params={"message": "Invalid webhook URL"},
        )

    port = parsed.port or 443
    try:
        ip = ipaddress.ip_address(host)
        if _is_blocked_ip(ip):
            raise ValidationException(
                message_key="errors.validation",
                params={"message": "Invalid webhook URL"},
            )
    except ValueError:
        _resolve_hostname_sync(host, port=port)

    return cleaned
