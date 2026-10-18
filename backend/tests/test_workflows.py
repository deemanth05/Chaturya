import asyncio
import io
import json
import os
import time
import zipfile

import httpx
import pytest
from fastapi.testclient import TestClient
from workbench.api import create_app
from workbench.auth import create_user
from workbench.sandbox import Sandbox, SUMMARY_CODE, verify_summary
from workbench.store import Store
from workbench.workflows import JobRunner
from conftest import ROOT, model_handler
from test_security import sign_in

docker = pytest.mark.skipif(os.getenv("WORKBENCH_DOCKER_TESTS") != "1", reason="Set WORKBENCH_DOCKER_TESTS=1 to execute real isolated Docker tests")


def wait_job(client, job_id, seconds=60):
    until = time.monotonic()+seconds
    while time.monotonic() < until:
        value = client.get(f"/api/jobs/{job_id}").json()
        if value["status"] not in {"running", "queued"}:
            return value
        time.sleep(.15)
    raise AssertionError("Job did not finish")


@docker
def test_three_inspection_runs_with_mock_model_and_real_sandbox(settings):
    app = create_app(settings, httpx.MockTransport(model_handler))
    create_user(app.state.store, "administrator", "a-long-password-123", "admin")
    running, maximum = 0, 0
    original = app.state.workflows.inspection
    class ObservedGraph:
        async def ainvoke(self, state):
            nonlocal running, maximum
            running += 1
            maximum = max(maximum, running)
            try:
                await asyncio.sleep(.1)
                return await original.ainvoke(state)
            finally:
                running -= 1
    app.state.workflows.inspection = ObservedGraph()
    with TestClient(app) as client:
        sign_in(client, "administrator")
        headers = {"Origin": "http://testserver"}
        # Test inputs use the ordinary ingestion API; production has no sample seeder.
        assert client.post("/api/fixtures/knowledge", headers=headers).status_code == 404
        for source in (ROOT / "backend/tests/fixtures/knowledge").glob("*.md"):
            assert client.post("/api/knowledge", files={"file": (source.name, source.read_bytes(), "text/markdown")},
                               data={"synthetic": "true"}, headers=headers).status_code == 200
        ids = []
        for _ in range(3):
            response = client.post("/api/jobs/inspection", files={"file": ("synthetic-scan.pdf", (ROOT / "backend/tests/fixtures/reports/synthetic-inspection-scan.pdf").read_bytes(), "application/pdf")}, data={"synthetic": "true"}, headers=headers)
            assert response.status_code == 202, response.text
            ids.append(response.json()["id"])
        for job_id in ids:
            job = wait_job(client, job_id)
            assert job["status"] == "completed", job
            assert job["state"]["extraction_method"] == "vision"
            assert job["state"]["summary"]["minimum_thickness_mm"] == 5.6
            assert job["state"]["decision"]["approval_verdict"] is None
            assert job["state"]["retrieval"]["mode"] == "bm25_only"
            assert "input_path" not in job["state"]
            artifact = client.get(f"/api/jobs/{job_id}/download")
            assert artifact.status_code == 200
            with zipfile.ZipFile(io.BytesIO(artifact.content)) as z:
                xml = z.read("word/document.xml").decode()
                assert "Engineering review required" in xml and "Synthetic demonstration" in xml
            assert client.get(f"/api/jobs/{job_id}/pages/1").status_code == 200
            events = client.get(f"/api/jobs/{job_id}/events").json()
            assert any(e["kind"] == "sandbox.verified" for e in events)
        assert maximum == 2
        # Retained history survives a new database connection.
        assert Store(settings.data).one("SELECT COUNT(*) AS n FROM jobs WHERE status='completed'")["n"] == 3


@docker
def test_code_retry_fixes_failed_run_with_real_execution(settings):
    app = create_app(settings, httpx.MockTransport(model_handler))
    create_user(app.state.store, "person", "a-long-password-123")
    with TestClient(app) as client:
        sign_in(client, "person")
        response = client.post("/api/jobs/code", json={"prompt": "Sum a list named values and return total.", "cases": [
            {"input": {"values": [2, 3]}, "expected": {"total": 5}}, {"input": {"values": []}, "expected": {"total": 0}}]}, headers={"Origin": "http://testserver"})
        assert response.status_code == 202, response.text
        job = wait_job(client, response.json()["id"])
        assert job["status"] == "completed", job
        assert [a["status"] for a in job["state"]["attempts"]] == ["failed", "passed"]
        assert job["state"]["verification"] == "passed_supplied_cases"


@docker
def test_sandbox_blocks_network_and_host_write(settings):
    sandbox = Sandbox(settings)
    result = sandbox.execute(settings.data / "isolation", """import socket,json,os
blocked=False
try:
    socket.create_connection(('1.1.1.1',443),timeout=1)
except OSError:
    blocked=True
try:
    open('/input/escape.txt','w').write('bad')
    readonly=False
except OSError:
    readonly=True
print(json.dumps({'network_blocked':blocked,'input_readonly':readonly,'uid':os.getuid()}))
""")
    assert result["exit_code"] == 0, result
    assert json.loads(result["stdout"]) == {"network_blocked": True, "input_readonly": True, "uid": 65534}


@pytest.mark.asyncio
async def test_restart_retains_queue_and_marks_inflight_interrupted(settings):
    store = Store(settings.data)
    user = create_user(store, "person", "a-long-password-123")
    for key, status in (("waiting", "queued"), ("inflight", "running")):
        store.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)", (key, user["id"], key, "code", status, time.time(), time.time(), "{}", None))
    class FakeWorkflows:
        async def code(self, state):
            return {"artifact": "solution.py"}
    runner = JobRunner(FakeWorkflows(), settings, store)
    await runner.start()
    await asyncio.wait_for(runner.queue.join(), 3)
    assert store.one("SELECT status FROM jobs WHERE id='inflight'")["status"] == "interrupted"
    assert store.one("SELECT status FROM jobs WHERE id='waiting'")["status"] == "completed"
    await runner.stop()


def test_summary_verifier_rejects_model_output_mismatch():
    with pytest.raises(ValueError):
        verify_summary({"exit_code": 0, "stdout": '{"count":1,"minimum_thickness_mm":99,"mean_thickness_mm":99,"maximum_thickness_mm":99}'}, [{"thickness_mm": 5}])
