import asyncio
import hashlib
import io
import json
import secrets
import sqlite3
import time
import uuid
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pypdf.errors import PyPdfError
from docx.opc.exceptions import PackageNotFoundError
from lxml.etree import XMLSyntaxError
from pydantic import BaseModel, Field

from . import settings as settings_module
from .auth import create_user, session_token, session_user, verify_password
from .knowledge import Knowledge
from .monitor import Monitor
from .network import EgressDenied, LocalTransport
from .registry import Registry
from .sandbox import Sandbox
from .settings import ROOT, Settings
from .store import Store
from .workflows import JobRunner, Workflows
from .college_access import visible_documents, load_config, current_user


class Login(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


class Account(Login):
    role: Literal["admin", "faculty", "staff", "student"] = "student"


class CollegeJob(BaseModel):
    workflow: Literal["question", "study", "teaching", "letter"]
    prompt: str = Field(min_length=10, max_length=12000)
    grounding: Literal["local", "general", "provided_facts"] = "local"
    language: str = Field(default="English", min_length=2, max_length=80)
    document_ids: list[str] = Field(default_factory=list, max_length=20)
    facts: dict[str, str] = Field(default_factory=dict, max_length=30)


class Memberships(BaseModel):
    departments: list[str] = Field(default_factory=list, max_length=30)
    courses: list[str] = Field(default_factory=list, max_length=100)


class AccountStatus(BaseModel):
    active: bool


class DocumentMetadata(BaseModel):
    audience: Literal["college", "faculty", "staff", "student", "private"] = "private"
    status: Literal["draft", "published", "archived"] = "draft"
    department: str = Field(default="", max_length=100)
    course: str = Field(default="", max_length=100)
    version: str = Field(default="", max_length=100)
    language: str = Field(default="", max_length=80)
    transcript_verified: bool = False


class Case(BaseModel):
    input: dict[str, Any]
    expected: Any


class CodeJob(BaseModel):
    prompt: str = Field(min_length=10, max_length=12000)
    cases: list[Case] = Field(default_factory=list, max_length=10)


class Review(BaseModel):
    note: str = Field(min_length=5, max_length=4000)


class Probe(BaseModel):
    model_id: str = Field(max_length=200)
    image: bool = False


def create_app(settings=None, model_http_transport=None):
    settings = settings or Settings()
    settings.prepare()
    store = Store(settings.data)
    registry = Registry(settings.registry)
    client = httpx.AsyncClient(transport=model_http_transport, trust_env=False, follow_redirects=False,
                              timeout=httpx.Timeout(settings.model_timeout, connect=8))
    transport = LocalTransport(registry.config["network"]["allowed_origins"], store, settings.model_concurrency, client)
    knowledge = Knowledge(store, registry, transport)
    workflows = Workflows(settings, store, registry, transport, knowledge, Sandbox(settings))
    runner = JobRunner(workflows, settings, store)
    monitor = Monitor(store, registry.config["network"]["allowed_origins"])
    login_attempts = {}
    ingest_lock = asyncio.Lock()
    college = load_config(settings.college_config)

    @asynccontextmanager
    async def lifespan(app):
        await runner.start()
        monitor.task = asyncio.create_task(monitor.loop())
        store.event("system.started", {"workers": settings.workers, "model_concurrency": settings.model_concurrency,
                                      "profile": settings.profile, "external_enforcement_verified": False})
        yield
        await runner.stop()
        monitor.task.cancel()
        await asyncio.gather(monitor.task, return_exceptions=True)
        await transport.close()
        knowledge.close()

    app = FastAPI(title="Local College AI", version="0.2.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store, app.state.registry = store, registry
    app.state.runner, app.state.workflows, app.state.transport = runner, workflows, transport

    @app.middleware("http")
    async def security(request, call_next):
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > settings.max_upload + 65536:
                    return Response("Request exceeds 20 MB", status_code=413)
            except ValueError:
                return Response("Invalid request length", status_code=400)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin not in settings.origins:
                return Response("Origin is not permitted", status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return Response("Cross-site requests are not permitted", status_code=403)
            if request.cookies.get("workbench_session") and not origin and request.headers.get("sec-fetch-site") != "same-origin":
                return Response("Authenticated writes require an allowed Origin header", status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
        return response

    def user(request: Request):
        result = session_user(store, request.cookies.get("workbench_session"))
        if not result:
            raise HTTPException(401, "Sign in to continue")
        return result

    def admin(current=Depends(user)):
        if current["role"] != "admin":
            raise HTTPException(403, "Administrator access required")
        return current

    def access(job_id, current):
        job = store.one("SELECT * FROM jobs WHERE id=?", (job_id,))
        privileged = {"admin", "reviewer"} if settings.profile == "industry" else {"admin"}
        if not job or (job["user_id"] != current["id"] and current["role"] not in privileged):
            raise HTTPException(404, "Job not found")
        job["state"] = json.loads(job["state"])
        if settings.profile == "college" and current["role"] != "admin":
            allowed = {d["id"] for d in visible_documents(store, current) if d["status"] != "archived"}
            sources = job["state"].get("retrieval", {}).get("sources", [])
            if any(s.get("document_id") not in allowed for s in sources):
                raise HTTPException(404, "Job sources are no longer available to this account")
        return job

    def public_state(job):
        # Never expose server paths, raw model input or generated scratch files.
        state = dict(job["state"])
        if job["workflow"] in {"question", "study", "teaching", "letter"} and job["status"] != "completed":
            state.pop("result", None)
        state.pop("input_path", None)
        state["pages"] = [{"page": p["page"]} for p in state.get("pages", [])]
        return {**job, "state": state}

    async def save_upload(upload, target, permitted):
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in permitted:
            raise HTTPException(415, "Unsupported file type")
        total = 0
        try:
            with target.open("wb") as stream:
                while chunk := await upload.read(65536):
                    total += len(chunk)
                    if total > settings.max_upload:
                        raise HTTPException(413, "File exceeds 20 MB")
                    stream.write(chunk)
            if total == 0:
                raise HTTPException(400, "File is empty")
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return suffix

    def enqueue(current, name, workflow, state, job_id=None):
        job_id = job_id or str(uuid.uuid4())
        # Per-user + global admission limits for a small shared pilot.
        with store.db() as db:
            db.execute("BEGIN IMMEDIATE")
            pending = db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
            own_pending = db.execute("SELECT COUNT(*) FROM jobs WHERE user_id=? AND status IN ('queued','running')", (current["id"],)).fetchone()[0]
            if pending >= settings.queue_total:
                raise HTTPException(429, "Job queue is full")
            if own_pending >= settings.queue_per_user:
                raise HTTPException(429, "Your pending-job limit has been reached")
            now = time.time()
            state = {**state, "job_id": job_id, "user_id": current["id"], "name": name}
            db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)", (job_id, current["id"], name, workflow, "queued", now, now, json.dumps(state), None))
        runner.queue.put_nowait(job_id)
        store.event("job.queued", {"workflow": workflow, "name": name}, job_id, current["id"])
        return public_state(access(job_id, current))

    @app.get("/api/health")
    async def health():
        return {"status": "ready", "accounts_initialized": bool(store.one("SELECT id FROM users WHERE active=1 LIMIT 1")), "version": "0.2.0", "profile": settings.profile}

    @app.post("/api/auth/login")
    async def login(body: Login, request: Request, response: Response):
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        attempts = [t for t in login_attempts.get(key, []) if now-t < 300]
        if len(attempts) >= 10:
            raise HTTPException(429, "Too many sign-in attempts; try again in five minutes")
        attempts.append(now)
        login_attempts[key] = attempts
        row = store.one("SELECT * FROM users WHERE username=? AND active=1", (body.username.strip().lower(),))
        valid = await asyncio.to_thread(verify_password, body.password, row["password"] if row else
            "pbkdf2_sha256$600000$00000000000000000000000000000000$" + "0"*64)
        if not row or not valid:
            store.event("auth.failed", {"source": key})
            raise HTTPException(401, "Invalid username or password")
        token = session_token(store, row["id"])
        login_attempts.pop(key, None)
        response.set_cookie("workbench_session", token, httponly=True, secure=settings.secure_cookies, samesite="strict", max_age=8*3600, path="/")
        store.event("auth.signed_in", {}, actor=row["id"])
        return current_user(store, row["id"])

    @app.get("/api/auth/me")
    async def me(current=Depends(user)):
        return current

    @app.post("/api/auth/logout")
    async def logout(request: Request, response: Response, current=Depends(user)):
        token = request.cookies.get("workbench_session", "")
        store.execute("DELETE FROM sessions WHERE token=?", (hashlib.sha256(token.encode()).hexdigest(),))
        response.delete_cookie("workbench_session", path="/")
        store.event("auth.signed_out", {}, actor=current["id"])
        return {"ok": True}

    @app.get("/api/accounts")
    async def accounts(current=Depends(admin)):
        return store.rows("SELECT id,username,COALESCE(college_role,CASE role WHEN 'inspector' THEN 'staff' WHEN 'reviewer' THEN 'faculty' ELSE role END) AS role,active,created FROM users ORDER BY created")

    @app.post("/api/accounts")
    async def add_account(body: Account, current=Depends(admin)):
        try:
            return await asyncio.to_thread(create_user, store, body.username, body.password, body.role)
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Username already exists") from None
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    @app.get("/api/jobs")
    async def jobs(current=Depends(user)):
        clauses = []
        args = []
        if settings.profile == "college":
            clauses.append("workflow IN ('question','study','teaching','letter','code')")
        if current["role"] != "admin":
            clauses.append("user_id=?")
            args.append(current["id"])
        rows = store.rows("SELECT id,name,workflow,status,created,updated,error FROM jobs " +
            ("WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY created DESC LIMIT 100", args)
        return rows

    @app.get("/api/college")
    async def college_info(current=Depends(user)):
        return {"type": "engineering_college", "workflows": college["workflows"],
            "teaching_roles": college["teaching_roles"], "letter_roles": college["letter_roles"],
            "default_language": college["institution"]["default_language"], "automatic_decisions": False,
            "ui_integration": "Authenticated REST API plus per-job WebSocket events"}

    @app.get("/api/schema")
    async def schema(current=Depends(user)):
        contract = app.openapi()
        contract.setdefault("components", {}).setdefault("securitySchemes", {})["workbenchSession"] = {
            "type": "apiKey", "in": "cookie", "name": "workbench_session"}
        for path, operations in contract["paths"].items():
            if path not in {"/api/health", "/api/auth/login"}:
                for method, operation in operations.items():
                    if method in {"get", "post", "put", "patch", "delete"}:
                        operation["security"] = [{"workbenchSession": []}]
        return contract

    @app.put("/api/accounts/{account_id}/memberships")
    async def set_memberships(account_id: str, body: Memberships, current=Depends(admin)):
        if not current_user(store, account_id):
            raise HTTPException(404, "Active account not found")
        values = [(kind, value.strip()) for kind, entries in (("department", body.departments), ("course", body.courses)) for value in entries]
        if any(not value or len(value) > 100 for _, value in values):
            raise HTTPException(400, "Use nonempty department and course identifiers of at most 100 characters")
        with store.db() as db:
            db.execute("DELETE FROM memberships WHERE user_id=?", (account_id,))
            db.executemany("INSERT OR IGNORE INTO memberships VALUES(?,?,?)", [(account_id, kind, value) for kind, value in values])
        store.event("account.memberships_changed", {"user_id": account_id, **body.model_dump()}, actor=current["id"])
        return body.model_dump()

    @app.get("/api/accounts/{account_id}/memberships")
    async def get_memberships(account_id: str, current=Depends(user)):
        if current["role"] != "admin" and current["id"] != account_id:
            raise HTTPException(404, "Account not found")
        return store.rows("SELECT kind,value FROM memberships WHERE user_id=? ORDER BY kind,value", (account_id,))

    @app.patch("/api/accounts/{account_id}")
    async def account_status(account_id: str, body: AccountStatus, current=Depends(admin)):
        if account_id == current["id"] and not body.active:
            raise HTTPException(409, "Cannot deactivate your own account")
        if not store.execute("UPDATE users SET active=? WHERE id=?", (int(body.active), account_id)):
            raise HTTPException(404, "Account not found")
        if not body.active:
            store.execute("DELETE FROM sessions WHERE user_id=?", (account_id,))
        store.event("account.status_changed", {"user_id": account_id, "active": body.active}, actor=current["id"])
        return {"active": body.active}

    @app.post("/api/jobs/college", status_code=202)
    async def college_job(body: CollegeJob, current=Depends(user)):
        if body.workflow not in college["workflows"]:
            raise HTTPException(403, "Workflow is disabled")
        allowed = college.get(body.workflow + "_roles")
        if allowed is not None and current["role"] not in allowed:
            raise HTTPException(403, "This workflow requires a faculty or office account")
        modes = {"question": {"local"}, "study": {"local", "general"}, "teaching": {"local"}, "letter": {"local", "provided_facts"}}
        if body.grounding not in modes[body.workflow]:
            raise HTTPException(400, "Grounding mode is not permitted for this workflow")
        if body.workflow == "teaching" and not body.document_ids:
            raise HTTPException(400, "Select an actual syllabus or course-material document")
        if body.workflow == "letter" and not all(body.facts.get(key, "").strip() for key in ("recipient", "subject", "purpose")):
            raise HTTPException(400, "Letter facts must include recipient, subject and purpose")
        if len(json.dumps(body.facts, ensure_ascii=False)) > 12000:
            raise HTTPException(400, "Letter facts exceed 12000 characters")
        visible_ids = {d["id"] for d in visible_documents(store, current) if d["status"] != "archived"}
        if not set(body.document_ids).issubset(visible_ids):
            raise HTTPException(404, "A selected document is unavailable")
        if body.grounding != "local" and body.document_ids:
            raise HTTPException(400, "Select local grounding to use documents")
        return enqueue(current, body.prompt[:80], body.workflow, body.model_dump())

    @app.post("/api/jobs/inspection", status_code=202, include_in_schema=settings.profile == "industry")
    async def inspection(file: UploadFile = File(...), synthetic: bool = Form(False), current=Depends(user)):
        if settings.profile != "industry":
            raise HTTPException(410, "Inspection workflows are disabled in the college profile")
        job_id = str(uuid.uuid4())
        folder = settings.data / "jobs" / job_id
        folder.mkdir(parents=True)
        suffix = Path(file.filename or "").suffix.lower()
        target = folder / ("source" + suffix)
        await save_upload(file, target, {".pdf", ".png", ".jpg", ".jpeg"})
        with target.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        return enqueue(current, Path(file.filename).name[:200], "inspection", {
            "input_path": str(target), "source_sha256": digest, "synthetic": synthetic}, job_id)

    @app.post("/api/jobs/code", status_code=202)
    async def code_job(body: CodeJob, current=Depends(user)):
        if settings.profile == "college" and "code" not in college["workflows"]:
            raise HTTPException(403, "Code workflow is disabled")
        if len(json.dumps(body.model_dump(), allow_nan=False)) > 64000:
            raise HTTPException(400, "Code task is too large")
        return enqueue(current, body.prompt[:80], "code", body.model_dump())

    @app.get("/api/jobs/{job_id}")
    async def job(job_id: str, current=Depends(user)):
        result = public_state(access(job_id, current))
        result["reviews"] = store.rows("SELECT reviews.*,users.username FROM reviews JOIN users ON users.id=reviews.actor WHERE job_id=? ORDER BY time", (job_id,))
        return result

    @app.get("/api/jobs/{job_id}/events")
    async def events(job_id: str, after: int = 0, current=Depends(user)):
        access(job_id, current)
        return store.events(job_id, after)

    @app.get("/api/jobs/{job_id}/pages/{page}")
    async def page(job_id: str, page: int, current=Depends(user)):
        job = access(job_id, current)
        if page < 1 or page > len(job["state"].get("pages", [])):
            raise HTTPException(404, "Source page not found")
        return FileResponse(settings.data / "jobs" / job_id / "pages" / f"page-{page}.png", media_type="image/png")

    @app.get("/api/jobs/{job_id}/download")
    async def download(job_id: str, format: Literal["docx", "md", "json"] = "docx", current=Depends(user)):
        job = access(job_id, current)
        artifact = job["state"].get("artifact")
        if artifact == "college-draft.docx":
            artifact = {"docx": "college-draft.docx", "md": "college-draft.md", "json": "college-result.json"}[format]
        if job["status"] != "completed" or artifact not in {"inspection-draft.docx", "solution.py", "college-draft.docx", "college-draft.md", "college-result.json"}:
            raise HTTPException(404, "No completed artifact is available")
        return FileResponse(settings.data / "jobs" / job_id / artifact, filename=artifact)

    @app.post("/api/jobs/{job_id}/retry", status_code=202)
    async def retry(job_id: str, current=Depends(user)):
        job = access(job_id, current)
        if job["status"] not in {"failed", "interrupted"}:
            raise HTTPException(409, "Only failed or interrupted jobs can be retried")
        old = job["state"]
        if job["workflow"] == "inspection":
            state = {"input_path": old["input_path"], "synthetic": old.get("synthetic", False), "source_sha256": old.get("source_sha256", "")}
        elif job["workflow"] == "code":
            state = {"prompt": old["prompt"], "cases": old.get("cases", [])}
        else:
            state = {key: old[key] for key in ("workflow", "prompt", "grounding", "language", "document_ids", "facts")}
        return enqueue(current, job["name"], job["workflow"], state)

    @app.post("/api/jobs/{job_id}/reviews")
    async def review(job_id: str, body: Review, current=Depends(user)):
        if current["role"] not in {"admin", "faculty", "staff", "reviewer"}:
            raise HTTPException(403, "Reviewer access required")
        job = access(job_id, current)
        if job["status"] != "completed":
            raise HTTPException(409, "Complete the run before recording a review")
        store.execute("INSERT INTO reviews(job_id,actor,note,time) VALUES(?,?,?,?)", (job_id, current["id"], body.note, time.time()))
        store.event("review.recorded", {"note": body.note, "approval_verdict": None}, job_id, current["id"])
        return {"recorded": True, "approval_verdict": None}

    @app.websocket("/api/jobs/{job_id}/stream")
    async def stream(websocket: WebSocket, job_id: str, after: int = 0):
        current = session_user(store, websocket.cookies.get("workbench_session"))
        if not current or websocket.headers.get("origin") not in settings.origins:
            await websocket.close(code=1008)
            return
        try:
            access(job_id, current)
        except HTTPException:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        try:
            while True:
                current = session_user(store, websocket.cookies.get("workbench_session"))
                if not current:
                    await websocket.close(code=1008)
                    return
                try:
                    access(job_id, current)
                except HTTPException:
                    await websocket.close(code=1008)
                    return
                items = store.events(job_id, after)
                for event in items:
                    await websocket.send_json(event)
                    after = event["id"]
                await websocket.send_json({"kind": "heartbeat", "after": after})
                await asyncio.sleep(.7)
        except (WebSocketDisconnect, RuntimeError):
            pass

    @app.get("/api/knowledge")
    async def documents(current=Depends(user)):
        if settings.profile == "college":
            return [{k: v for k, v in d.items() if k != "source_path"} for d in visible_documents(store, current)]
        return store.rows("SELECT documents.*,COUNT(chunks.id) AS chunks FROM documents LEFT JOIN chunks ON chunks.document_id=documents.id GROUP BY documents.id ORDER BY created DESC")

    @app.post("/api/knowledge")
    async def add_knowledge(file: UploadFile = File(...), synthetic: bool = Form(False),
                            metadata: str = Form("{}"), current=Depends(user)):
        if current["role"] not in {"admin", "faculty", "staff"}:
            raise HTTPException(403, "Document ingestion requires faculty, office or administrator access")
        try:
            meta = DocumentMetadata.model_validate_json(metadata).model_dump()
        except ValueError:
            raise HTTPException(400, "Invalid document metadata") from None
        if settings.profile == "college" and synthetic:
            raise HTTPException(400, "Synthetic knowledge is disabled in the college profile")
        if current["role"] != "admin":
            meta.update(audience="private", status="draft", department="", course="")
        suffix = Path(file.filename or "").suffix.lower()
        target = settings.data / "knowledge" / (str(uuid.uuid4()) + suffix)
        await save_upload(file, target, {".pdf", ".txt", ".md", ".docx", ".png", ".jpg", ".jpeg"})
        try:
            async with ingest_lock:
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
                existing = store.one("SELECT id FROM documents WHERE sha256=?", (digest,))
                if existing:
                    target.unlink(missing_ok=True)
                    raise HTTPException(409, "Identical content is already stored; an administrator can manage its access")
                return await knowledge.ingest(target, Path(file.filename).name[:200], current["id"], synthetic, meta)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        except (PyPdfError, zipfile.BadZipFile, PackageNotFoundError, XMLSyntaxError, OSError):
            raise HTTPException(400, "The document cannot be read; check its format and whether it is damaged or encrypted") from None
        except (httpx.HTTPError, RuntimeError) as exc:
            raise HTTPException(503, "Local indexing service unavailable: " + str(exc)[:400]) from None

    @app.patch("/api/knowledge/{document_id}")
    async def update_document(document_id: str, body: DocumentMetadata, current=Depends(admin)):
        document = store.one("SELECT * FROM documents WHERE id=? AND synthetic=0", (document_id,))
        if not document:
            raise HTTPException(404, "Document not found")
        extraction = document["extraction"]
        if extraction == "vision_unverified" and body.status == "published":
            if not body.transcript_verified:
                raise HTTPException(400, "Verify the vision transcript against the original before publishing")
            extraction = "vision_verified"
        store.execute("UPDATE documents SET audience=?,status=?,department=?,course=?,version=?,language=?,extraction=? WHERE id=?",
            (body.audience, body.status, body.department.strip(), body.course.strip(), body.version.strip(), body.language.strip(), extraction, document_id))
        store.event("knowledge.access_changed", {"document_id": document_id, **body.model_dump()}, actor=current["id"])
        return {"updated": True, "extraction": extraction}

    def accessible_document(document_id, current):
        doc = next((d for d in visible_documents(store, current) if d["id"] == document_id), None)
        if not doc:
            raise HTTPException(404, "Document not found")
        return doc

    @app.get("/api/knowledge/{document_id}/chunks")
    async def document_chunks(document_id: str, current=Depends(user)):
        accessible_document(document_id, current)
        return store.rows("SELECT id,page,section,text FROM chunks WHERE document_id=? ORDER BY rowid", (document_id,))

    @app.get("/api/knowledge/{document_id}/download")
    async def source_download(document_id: str, current=Depends(user)):
        doc = accessible_document(document_id, current)
        stored = Path(doc["source_path"] or "")
        target = (stored if stored.is_absolute() else settings.data / stored).resolve()
        if not target.is_relative_to(settings.data / "knowledge") or not target.is_file():
            raise HTTPException(404, "Original source is unavailable")
        return FileResponse(target, filename=doc["name"])

    @app.post("/api/knowledge/reindex-dense")
    async def reindex_dense(current=Depends(admin)):
        try:
            async with ingest_lock:
                document_ids = [d["id"] for d in visible_documents(store, current) if d["status"] != "archived"] if settings.profile == "college" else None
                return await knowledge.reindex_dense(current["id"], document_ids)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    @app.get("/api/system")
    async def system(current=Depends(user)):
        return {"monitor": monitor.snapshot(), "worker_limit": settings.workers,
            "model_concurrency": settings.model_concurrency, "profile": settings.profile, "automatic_decisions": False,
            "models": registry.models, "laya_configured": bool(registry.config.get("router", {}).get("laya_url")),
            "storage": "local SQLite WAL and embedded Qdrant", "allowed_origins": registry.config["network"]["allowed_origins"]}

    @app.post("/api/system/blocked-check")
    async def blocked_check(current=Depends(admin)):
        # Policy test intentionally stops before any DNS lookup or socket call.
        try:
            transport.check("https://example.com/sovereignty-check")
        except EgressDenied:
            store.event("network.policy_test", {"passed": True, "socket_attempted": False}, actor=current["id"])
            return {"blocked": True, "layer": "application_policy", "socket_attempted": False,
                    "os_firewall_verified": False}
        raise HTTPException(500, "Egress policy did not reject the test")

    @app.post("/api/models/probe")
    async def probe(body: Probe, current=Depends(admin)):
        model = next((m for m in registry.models if m["id"] == body.model_id and m.get("enabled")), None)
        if not model:
            raise HTTPException(404, "Enabled model not found")
        try:
            listed = await transport.request("GET", model["base_url"].rstrip("/") + "/models", model_call=False, headers=registry.headers(model))
            ids = [item["id"] for item in listed.get("data", [])]
            if model["id"] not in ids:
                return {"reachable": True, "listed": False, "available_ids": ids, "image_verified": False}
            image_ok = False
            if body.image:
                import base64
                buffer = io.BytesIO()
                Image.new("RGB", (96, 96), "red").save(buffer, format="PNG")
                result = await registry.chat(transport, model, [{"role": "user", "content": [
                    {"type": "text", "text": "What is the solid background color of this image? Answer with one color word only."},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,"+base64.b64encode(buffer.getvalue()).decode()}}
                ]}], None)
                image_ok = result.strip().lower().strip(". ") == "red"
            answer = {"reachable": True, "listed": True, "image_probe_run": body.image, "image_verified": image_ok,
                      "note": "A simple color probe does not establish document transcription accuracy"}
            store.event("model.probed", {"model": model["id"], **answer}, actor=current["id"])
            return answer
        except Exception as exc:
            return {"reachable": False, "listed": False, "image_verified": False, "error": str(exc) or type(exc).__name__}

    @app.get("/api/audit")
    async def audit(after: int = 0, current=Depends(admin)):
        return store.events(after=after, limit=500)

    # Unknown API paths, including removed demo endpoints, must never fall
    # through to the static UI mount (which handles only browser GET/HEAD).
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], include_in_schema=False)
    async def unknown_api(path: str):
        raise HTTPException(404, "API endpoint not found")

    frontend = ROOT / ("college-console" if settings.profile == "college" else "frontend/out")
    if frontend.exists():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")

    return app

