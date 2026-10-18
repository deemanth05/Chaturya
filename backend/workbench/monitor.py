import asyncio
import os
import time
import psutil


class Monitor:
    """Observe this service process; enforcement remains an OS/network duty."""
    def __init__(self, store, allowed):
        from urllib.parse import urlsplit
        self.store = store
        self.allowed = {(urlsplit(x).hostname, urlsplit(x).port or (443 if x.startswith("https") else 80)) for x in allowed}
        self.status = {"visibility": "not_sampled", "unexpected_connections": [], "external_bytes": None,
                       "enforcement": "application_allowlist_only", "scope": "backend_process_only"}
        self.task = None
        self.seen = set()

    async def loop(self):
        while True:
            try:
                connections = await asyncio.to_thread(psutil.Process(os.getpid()).net_connections, kind="inet")
                unexpected = [{"ip": c.raddr.ip, "port": c.raddr.port, "status": c.status} for c in connections
                              if c.raddr and c.status == psutil.CONN_ESTABLISHED and (c.raddr.ip, c.raddr.port) not in self.allowed
                              # Inbound UI connections have the backend listening port as laddr.
                              and c.laddr.port not in {8000, 8001}]
                for item in unexpected:
                    key = (item["ip"], item["port"])
                    if key not in self.seen:
                        self.store.event("network.unexpected_observed", item)
                        self.seen.add(key)
                self.status.update(visibility="sampled", unexpected_connections=unexpected, sampled_at=time.time())
            except (psutil.AccessDenied, OSError):
                self.status["visibility"] = "permission_denied"
            await asyncio.sleep(3)

    def snapshot(self):
        blocked = self.store.one("SELECT COUNT(*) AS count FROM events WHERE kind='network.blocked'")["count"]
        local = self.store.one("SELECT COUNT(*) AS count FROM events WHERE kind='network.local_call'")["count"]
        return {**self.status, "blocked_attempts": blocked, "local_calls": local,
                "note": "External byte accounting is unavailable. Process sampling cannot prove zero host egress."}
