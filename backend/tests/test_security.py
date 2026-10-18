import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from workbench.api import create_app
from workbench.auth import create_user, password_hash, verify_password
from workbench.network import EgressDenied, LocalTransport
from workbench.store import Store
from conftest import model_handler


def test_passwords_are_salted_and_verified():
    first, second = password_hash("correct-password-123"), password_hash("correct-password-123")
    assert first != second
    assert verify_password("correct-password-123", first)
    assert not verify_password("wrong", first)
    with pytest.raises(ValueError):
        password_hash("short")


@pytest.mark.asyncio
async def test_exact_network_allowlist_blocks_before_transport(settings):
    store = Store(settings.data)
    calls = []
    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, json={"ok": True})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)
    network = LocalTransport(["http://127.0.0.1:1234"], store, client=client)
    for address in ("https://example.com", "http://8.8.8.8", "http://127.0.0.1:9999", "http://10.1.1.1:1234", "http://127.0.0.1:1234@8.8.8.8", "http://0.0.0.0"):
        with pytest.raises(EgressDenied):
            await network.request("GET", address)
    assert calls == []
    assert len(store.events()) == 6
    await network.request("GET", "http://127.0.0.1:1234/v1/models")
    assert len(calls) == 1
    await network.close()


@pytest.mark.asyncio
async def test_redirect_is_not_followed(settings):
    store = Store(settings.data)
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://example.com"})
    network = LocalTransport(["http://127.0.0.1:1234"], store, client=httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False))
    with pytest.raises(EgressDenied):
        await network.request("GET", "http://127.0.0.1:1234/v1/models")
    assert len(calls) == 1
    await network.close()


def sign_in(client, username, password="a-long-password-123"):
    result = client.post("/api/auth/login", json={"username": username, "password": password}, headers={"Origin": "http://testserver"})
    assert result.status_code == 200, result.text


def test_accounts_job_isolation_csrf_and_admin_access(settings):
    app = create_app(settings, httpx.MockTransport(model_handler))
    store = app.state.store
    create_user(store, "administrator", "a-long-password-123", "admin")
    one = create_user(store, "inspector-one", "a-long-password-123")
    create_user(store, "inspector-two", "a-long-password-123")
    with TestClient(app) as client:
        assert client.get("/api/jobs").status_code == 401
        sign_in(client, "inspector-one")
        assert client.get("/api/accounts").status_code == 403
        assert client.post("/api/system/blocked-check", headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.post("/api/auth/logout").status_code == 403
        import time
        store.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)", ("private-run", one["id"], "Private report", "inspection", "failed", time.time(), time.time(), "{}", "test"))
        assert client.get("/api/jobs/private-run").status_code == 200
        sign_in(client, "inspector-two")
        for path in ("", "/events", "/download", "/pages/1"):
            assert client.get("/api/jobs/private-run" + path).status_code == 404
        assert client.get("/api/jobs").json() == []
        sign_in(client, "administrator")
        assert client.get("/api/jobs/private-run").status_code == 200
        body = client.post("/api/system/blocked-check", headers={"Origin": "http://testserver"}).json()
        assert body == {"blocked": True, "layer": "application_policy", "socket_attempted": False, "os_firewall_verified": False}
        assert client.get("/api/system").json()["monitor"]["external_bytes"] is None
        assert client.get("/api/audit").status_code == 200
        assert client.post("/api/accounts", json={"username": "new-person", "password": "a-long-password-123", "role": "faculty"}, headers={"Origin": "http://testserver"}).status_code == 200
        client.post("/api/auth/logout", headers={"Origin": "http://testserver"})
        assert client.get("/api/jobs").status_code == 401


def test_websocket_requires_session_and_correct_origin(settings):
    from starlette.websockets import WebSocketDisconnect
    app = create_app(settings, httpx.MockTransport(model_handler))
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/api/jobs/unknown/stream", headers={"Origin": "http://testserver"}):
                pass

