from __future__ import annotations

from ipaddress import ip_address

from django.conf import settings


def is_public_ip(value: str) -> bool:
    try:
        parsed = ip_address(value)
    except ValueError:
        return False
    return parsed.is_global


def get_client_ip(request) -> str:
    remote_addr = (request.META.get("REMOTE_ADDR") or "").strip()
    trusted_proxy_hops = max(int(getattr(settings, "TRUSTED_PROXY_HOPS", 0)), 0)

    if trusted_proxy_hops == 0:
        return remote_addr or "0.0.0.0"

    cloudflare_ip = (request.META.get("HTTP_CF_CONNECTING_IP") or "").strip()
    if is_public_ip(cloudflare_ip):
        return cloudflare_ip

    real_ip = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if is_public_ip(real_ip):
        return real_ip

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    chain = [part.strip() for part in forwarded_for.split(",") if part.strip()]
    for candidate in chain:
        if is_public_ip(candidate):
            return candidate

    return remote_addr or "0.0.0.0"
