import asyncio
import ipaddress
import json
import time
from urllib.parse import urlsplit

import httpx


class EgressDenied(ValueError):
    pass


def origin(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise EgressDenied("Invalid service URL")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        raise EgressDenied("Service destinations must use literal local IP addresses") from None
    if not (address.is_private or address.is_loopback) or address.is_unspecified or address.is_multicast:
        raise EgressDenied("Only explicit local service IP addresses are allowed")
    hostname = f"[{address}]" if address.version == 6 else str(address)
    return f"{parsed.scheme}://{hostname}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}"


class LocalTransport:
    def __init__(self, allowed, store, concurrency=1, client=None):
        self.allowed = {origin(item) for item in allowed}
        self.store = store
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = client or httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=httpx.Timeout(180, connect=8))

    def check(self, url, job_id=None):
        try:
            target = origin(url)
            if target not in self.allowed:
                raise EgressDenied("Destination is outside the exact local service allowlist")
        except (ValueError, EgressDenied) as exc:
            self.store.event("network.blocked", {"url": str(url)[:200], "reason": str(exc), "layer": "application_policy"}, job_id)
            raise EgressDenied(str(exc)) from None
        return target

    async def request(self, method, url, *, body=None, job_id=None, model_call=True, headers=None):
        target = self.check(url, job_id)
        started = time.perf_counter()

        async def perform():
            service_started = time.perf_counter()
            queue_wait_ms = round((service_started-started)*1000)
            self.store.event("network.local_started", {"destination": target, "queue_wait_ms": queue_wait_ms}, job_id)
            try:
                response = await self.client.request(method, url, json=body, headers=headers)
                if 300 <= response.status_code < 400:
                    raise EgressDenied("Service redirects are disabled")
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                self.store.event("network.failed", {"destination": target, "error": type(exc).__name__}, job_id)
                if isinstance(exc, httpx.HTTPStatusError):
                    try:
                        detail = exc.response.json().get("error", "Request rejected")
                    except (ValueError, AttributeError):
                        detail = "Request rejected"
                    raise RuntimeError(f"Local service returned HTTP {exc.response.status_code}: {str(detail)[:700]}") from exc
                if isinstance(exc, httpx.TimeoutException):
                    raise RuntimeError("Local model service timed out; confirm the Mac is awake and the model fits in memory") from exc
                raise
            self.store.event("network.local_call", {"destination": target, "latency_ms": round((time.perf_counter()-started)*1000),
                "queue_wait_ms": queue_wait_ms, "service_ms": round((time.perf_counter()-service_started)*1000),
                "request_body_bytes": len(json.dumps(body).encode()) if body else 0,
                "response_body_bytes": len(response.content)}, job_id)
            return data

        if model_call:
            async with self.semaphore:
                return await perform()
        return await perform()

    async def close(self):
        await self.client.aclose()

