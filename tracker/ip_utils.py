from __future__ import annotations

from django.conf import settings


def get_client_ip(request) -> str:
    remote_addr = (request.META.get("REMOTE_ADDR") or "").strip()
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    trusted_proxy_hops = max(int(getattr(settings, "TRUSTED_PROXY_HOPS", 0)), 0)

    if not forwarded_for or trusted_proxy_hops == 0:
        return remote_addr or "0.0.0.0"

    chain = [part.strip() for part in forwarded_for.split(",") if part.strip()]
    if not chain:
        return remote_addr or "0.0.0.0"

    if len(chain) >= trusted_proxy_hops:
        return chain[-trusted_proxy_hops]

    return remote_addr or chain[0]
