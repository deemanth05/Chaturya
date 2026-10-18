"""Deterministic fault/authorization tests. Model doubles exist only in tests."""
import io
import json
import time
import zipfile

import httpx
import pytest
from docx import Document
from fastapi.testclient import TestClient

from workbench.api import create_app
from workbench.auth import create_user
from workbench.college import Answer, validate_answer
from workbench.knowledge import split_document
from workbench.college_access import visible_documents
from test_security import sign_in
from test_workflows import wait_job

HEADERS = {"Origin": "http://testserver"}


def college_handler(request):
    body = json.loads(request.content)
    data = json.loads(body["messages"][-1]["content"])
    sources = data["sources"]
    section = {"heading": "Explanation", "text": sources[0]["text"] if sources else data["request"],
        "evidence": [{"source_id": sources[0]["source_id"], "quote": sources[0]["text"][:80]}] if sources else []}
    result = {"title": "Test-only draft", "status": "answered", "sections": [section], "missing_information": []}
    return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}]})


def setup(settings, handler=college_handler):
    settings.profile = "college"
    app = create_app(settings, httpx.MockTransport(handler))
    accounts = {role: create_user(app.state.store, role + "-person", "a-long-password-123", role)
                for role in ("admin", "faculty", "staff", "student")}
    return app, accounts


def upload(client, name, text, **metadata):
    response = client.post("/api/knowledge", headers=HEADERS,
        files={"file": (name, text.encode(), "text/plain")}, data={"metadata": json.dumps(metadata)})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def task(client, **changes):
    body = {"workflow": "question", "prompt": "Explain the laboratory material", "grounding": "local", **changes}
    return client.post("/api/jobs/college", json=body, headers=HEADERS)


def test_empty_college_abstains_without_calling_model(settings):
    calls = []
    def fail(request):
        calls.append(request)
        raise AssertionError("Empty knowledge must not call an LLM")
    app, accounts = setup(settings, fail)
    with TestClient(app) as client:
        sign_in(client, "student-person")
        response = task(client)
        job = wait_job(client, response.json()["id"])
        assert job["status"] == "completed", job
        assert job["state"]["result"]["status"] == "insufficient_evidence"
        assert calls == []
        assert client.post("/api/jobs/inspection", files={"file": ("report.pdf", b"x")}, headers=HEADERS).status_code == 410
        assert client.get("/api/fixtures/report").status_code == 404
        sign_in(client, "admin-person")
        assert client.post("/api/fixtures/knowledge", headers=HEADERS).status_code == 404
        assert "/api/jobs/inspection" not in client.get("/api/schema").json()["paths"]


def test_document_scopes_apply_to_search_sources_jobs_and_downloads(settings):
    app, accounts = setup(settings)
    with TestClient(app) as client:
        sign_in(client, "admin-person")
        restricted = upload(client, "faculty-material.txt", "Faculty laboratory material: protected answer explanations.", audience="faculty", status="published")
        course = upload(client, "course-material.txt", "Laboratory material includes resistance and circuit analysis.", audience="college", status="published", course="actual-course-id")
        sign_in(client, "student-person")
        assert client.get("/api/knowledge").json() == []
        for suffix in ("chunks", "download"):
            assert client.get(f"/api/knowledge/{restricted}/{suffix}").status_code == 404
        assert task(client, document_ids=[restricted]).status_code == 404
        assert task(client, workflow="teaching", document_ids=[course]).status_code == 403
        sign_in(client, "admin-person")
        student = accounts["student"]["id"]
        assert client.put(f"/api/accounts/{student}/memberships", json={"courses": ["actual-course-id"]}, headers=HEADERS).status_code == 200
        sign_in(client, "student-person")
        docs = client.get("/api/knowledge").json()
        assert [d["id"] for d in docs] == [course] and "source_path" not in docs[0]
        job = wait_job(client, task(client, document_ids=[course]).json()["id"])
        assert job["status"] == "completed", job
        result = job["state"]["result"]
        assert result["review_required"] and result["approval_verdict"] is None
        assert {s["document_id"] for s in result["sources"]} == {course}
        for format in ("docx", "md", "json"):
            download = client.get(f"/api/jobs/{job['id']}/download?format={format}")
            assert download.status_code == 200
            if format == "docx":
                with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
                    xml = archive.read("word/document.xml").decode()
                    assert "HUMAN REVIEW REQUIRED" in xml and "course-material.txt" in xml
        sign_in(client, "faculty-person")
        assert client.get(f"/api/jobs/{job['id']}").status_code == 404
        sign_in(client, "admin-person")
        client.put(f"/api/accounts/{student}/memberships", json={"courses": []}, headers=HEADERS)
        sign_in(client, "student-person")
        for suffix in ("", "/events", "/download"):
            assert client.get(f"/api/jobs/{job['id']}" + suffix).status_code == 404


def test_faculty_drafts_are_private_and_teaching_requires_sources(settings):
    app, _ = setup(settings)
    with TestClient(app) as client:
        sign_in(client, "faculty-person")
        doc = upload(client, "working-notes.txt", "Laboratory material: analyze linear circuit equations.", audience="college", status="published")
        assert client.get("/api/knowledge").json()[0]["audience"] == "private"
        assert task(client, workflow="teaching").status_code == 400
        job = wait_job(client, task(client, workflow="teaching", document_ids=[doc]).json()["id"])
        assert job["status"] == "completed", job
        assert any("unpublished" in warning for warning in job["state"]["warnings"])
        sign_in(client, "student-person")
        assert client.get("/api/knowledge").json() == []
        assert client.get(f"/api/jobs/{job['id']}").status_code == 404


def test_general_study_letters_and_role_permissions(settings):
    app, _ = setup(settings)
    with TestClient(app) as client:
        sign_in(client, "student-person")
        assert task(client, grounding="general").status_code == 400
        study = wait_job(client, task(client, workflow="study", grounding="general", prompt="Explain how matrix multiplication works").json()["id"])
        assert study["status"] == "completed", study
        assert study["state"]["result"]["grounding"] == "general"
        assert study["state"]["result"]["sources"] == []
        assert task(client, workflow="letter", grounding="provided_facts").status_code == 403
        sign_in(client, "staff-person")
        assert task(client, workflow="letter", grounding="provided_facts").status_code == 400
        letter = wait_job(client, task(client, workflow="letter", grounding="provided_facts",
            facts={"recipient": "Department office", "subject": "Document request", "purpose": "Request the current handbook"}).json()["id"])
        assert letter["status"] == "completed", letter
        assert "user-supplied facts" in letter["state"]["result"]["basis"]


def test_deactivation_revokes_existing_sessions_and_queued_work(settings):
    app, accounts = setup(settings)
    from workbench.auth import session_token, session_user
    token = session_token(app.state.store, accounts["student"]["id"])
    assert session_user(app.state.store, token)
    with TestClient(app) as client:
        sign_in(client, "admin-person")
        assert client.patch(f"/api/accounts/{accounts['student']['id']}", json={"active": False}, headers=HEADERS).status_code == 200
        assert session_user(app.state.store, token) is None
        assert client.post("/api/auth/login", json={"username": "student-person", "password": "a-long-password-123"}, headers=HEADERS).status_code == 401
        assert client.patch(f"/api/accounts/{accounts['admin']['id']}", json={"active": False}, headers=HEADERS).status_code == 409


def test_citation_validation_blocks_fabricated_or_missing_references():
    base = {"title": "Draft", "status": "answered", "sections": [{"heading": "Evidence", "text": "A claim", "evidence": []}], "missing_information": []}
    with pytest.raises(ValueError, match="omitted"):
        validate_answer(Answer.model_validate(base), [], True)
    base["sections"][0]["evidence"] = [{"source_id": "unknown", "quote": "fabricated quotation"}]
    with pytest.raises(ValueError, match="citation"):
        validate_answer(Answer.model_validate(base), [], True)
    with pytest.raises(ValueError, match="invent"):
        validate_answer(Answer.model_validate(base), [], False)


def test_word_extraction_preserves_tables_and_uses_no_invented_pages(tmp_path):
    path = tmp_path / "source.docx"
    document = Document()
    document.add_paragraph("Real document structure")
    split_word = document.add_paragraph()
    split_word.add_run("resis")
    split_word.add_run("tance").bold = True
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Circuit laboratory content"
    document.save(path)
    chunks = split_document(path)
    assert all(c["page"] == 0 for c in chunks)
    assert "Circuit laboratory content" in " ".join(c["text"] for c in chunks)
    assert "resistance" in " ".join(c["text"] for c in chunks)


@pytest.mark.asyncio
async def test_dense_search_filters_private_ids_before_ranking(settings):
    import yaml
    from conftest import model_handler
    settings.profile = "college"
    config = yaml.safe_load(settings.registry.read_text())
    config["models"][1]["enabled"] = True
    settings.registry.write_text(yaml.safe_dump(config))
    app = create_app(settings, httpx.MockTransport(model_handler))
    store, kb = app.state.store, app.state.workflows.knowledge
    admin = create_user(store, "admin-person", "a-long-password-123", "admin")
    student = create_user(store, "student-person", "a-long-password-123", "student")
    try:
        for name, audience, text in [("public.txt", "college", "Laboratory circuits and resistance."),
                                     ("secret.txt", "faculty", "Laboratory circuits: protected answer key.")]:
            path = settings.data / "knowledge" / name
            path.write_text(text)
            await kb.ingest(path, name, admin["id"], metadata={"audience": audience, "status": "published"})
        result = await kb.search("laboratory circuits", current=student)
        assert result["mode"] == "hybrid"
        assert {s["name"] for s in result["sources"]} == {"public.txt"}
        assert "protected" not in json.dumps(result)
    finally:
        kb.close()
        await app.state.transport.close()


def test_vision_source_requires_publication_attestation(settings):
    from PIL import Image
    def transcriber(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"text": "Test-only laboratory transcription text."})}}]})
    app, _ = setup(settings, transcriber)
    buffer = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(buffer, format="PNG")
    with TestClient(app) as client:
        sign_in(client, "admin-person")
        response = client.post("/api/knowledge", headers=HEADERS,
            files={"file": ("test-only-image.png", buffer.getvalue(), "image/png")},
            data={"metadata": json.dumps({"audience": "college", "status": "published"})})
        assert response.status_code == 200, response.text
        doc = response.json()
        assert doc["status"] == "draft" and doc["extraction"] == "vision_unverified"
        assert client.patch(f"/api/knowledge/{doc['id']}", json={"audience": "college", "status": "published"}, headers=HEADERS).status_code == 400
        assert client.patch(f"/api/knowledge/{doc['id']}", json={"audience": "college", "status": "published", "transcript_verified": True}, headers=HEADERS).json()["extraction"] == "vision_verified"
        sign_in(client, "student-person")
        assert len(client.get("/api/knowledge").json()) == 1


def test_legacy_database_upgrade_is_additive_and_preserves_accounts(settings):
    import sqlite3
    from workbench.store import Store
    from workbench.college_access import current_user
    settings.data.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.data / "workbench.sqlite3") as db:
        db.execute("CREATE TABLE users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','inspector','reviewer')),created REAL NOT NULL)")
        db.execute("INSERT INTO users VALUES('old-user','old-name','unused','inspector',1)")
    store = Store(settings.data)
    assert current_user(store, "old-user")["role"] == "staff"
    create_user(store, "new-student", "a-long-password-123", "student")
    Store(settings.data)
    assert store.one("SELECT COUNT(*) AS n FROM users")["n"] == 2


def test_queue_limits_protect_shared_capacity(settings):
    settings.queue_per_user = 1
    app, accounts = setup(settings)
    with TestClient(app) as client:
        sign_in(client, "student-person")
        app.state.store.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)", ("occupied", accounts["student"]["id"], "Existing test job", "study", "running", time.time(), time.time(), "{}", None))
        assert task(client).status_code == 429
        sign_in(client, "faculty-person")
        assert task(client).status_code == 202
        settings.queue_total = 1
        assert task(client).status_code == 429


@pytest.mark.asyncio
async def test_deactivated_owner_never_falls_back_to_unscoped_retrieval(settings):
    app, accounts = setup(settings)
    store = app.state.store
    store.execute("UPDATE users SET active=0 WHERE id=?", (accounts["student"]["id"],))
    try:
        with pytest.raises(ValueError, match="inactive"):
            await app.state.workflows.college.retrieve({"user_id": accounts["student"]["id"], "grounding": "local", "prompt": "laboratory material", "job_id": "not-started"})
    finally:
        app.state.workflows.knowledge.close()
        await app.state.transport.close()


def test_inconsistent_status_is_repaired_before_release(settings):
    calls = []
    def inconsistent(request):
        calls.append(request)
        result = {"title": "Draft", "status": "insufficient_evidence" if len(calls) == 1 else "answered",
                  "sections": [{"heading": "Concept", "text": "A general educational explanation.", "evidence": []}],
                  "missing_information": []}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(result)}}]})
    app, _ = setup(settings, inconsistent)
    with TestClient(app) as client:
        sign_in(client, "student-person")
        job = wait_job(client, task(client, workflow="study", grounding="general").json()["id"])
        assert job["status"] == "completed", job
        assert len(calls) == 2
        assert any(e["kind"] == "college.repair_requested" for e in client.get(f"/api/jobs/{job['id']}/events").json())


def test_failed_unvalidated_draft_is_not_exposed_by_job_api(settings):
    app, accounts = setup(settings)
    with TestClient(app) as client:
        sign_in(client, "student-person")
        state = {"result": {"sections": [{"text": "unvalidated-output"}]}}
        app.state.store.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)", ("invalid", accounts["student"]["id"], "Invalid draft", "question", "failed", time.time(), time.time(), json.dumps(state), "validation failed"))
        result = client.get("/api/jobs/invalid").json()
        assert "result" not in result["state"]
        assert "unvalidated-output" not in json.dumps(result)
        assert client.get("/api/jobs/invalid/download").status_code == 404


def test_citation_normalizes_line_breaks_without_changing_words():
    answer = Answer.model_validate({"title": "Draft", "status": "answered", "sections": [{"heading": "Source", "text": "A supported statement", "evidence": [{"source_id": "source", "quote": "study support and practice"}]}], "missing_information": []})
    result = validate_answer(answer, [{"id": "source", "text": "Includes study\nsupport and practice exercises."}], True)
    assert result["sections"][0]["evidence"][0]["quote"] == "study support and practice"
    with pytest.raises(ValueError):
        validate_answer(answer, [{"id": "source", "text": "Includes study support without practice exercises."}], True)
