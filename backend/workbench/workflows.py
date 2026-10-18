import asyncio
import json
import os
import time
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .extraction import extract, read_pages, parse_json, docling_text
from .reports import generate_note
from .sandbox import SUMMARY_CODE, verify_summary


class InspectionState(TypedDict, total=False):
    job_id: str
    user_id: str
    name: str
    input_path: str
    source_sha256: str
    synthetic: bool
    pages: list
    measurements: list
    warnings: list
    extraction_route: dict
    extraction_method: str
    scanned: bool
    docling_text: str
    retrieval: dict
    summary: dict | None
    sandbox: dict
    decision: dict
    artifact: str


class Workflows:
    def __init__(self, settings, store, registry, transport, knowledge, sandbox):
        self.settings, self.store, self.registry = settings, store, registry
        self.transport, self.knowledge, self.sandbox = transport, knowledge, sandbox
        graph = StateGraph(InspectionState)
        nodes = [("prepare", self.prepare), ("extract", self.extraction), ("retrieve", self.retrieve),
                 ("calculate", self.calculate), ("decide", self.decide), ("document", self.document)]
        for name, function in nodes:
            graph.add_node(name, self.traced(name, function))
        graph.add_edge(START, "prepare")
        for (left, _), (right, _) in zip(nodes, nodes[1:]):
            graph.add_edge(left, right)
        graph.add_edge("document", END)
        self.inspection = graph.compile()
        from .college import CollegeWorkflows
        self.college = CollegeWorkflows(self)

    def traced(self, name, function):
        async def run(state):
            started = time.perf_counter()
            self.store.event("step.started", {"step": name}, state["job_id"])
            update = await function(state)
            merged = {**state, **update}
            self.store.snapshot(state["job_id"], merged)
            self.store.event("step.completed", {"step": name, "latency_ms": round((time.perf_counter()-started)*1000)}, state["job_id"])
            return update
        return run

    async def prepare(self, state):
        pages = await asyncio.to_thread(read_pages, Path(state["input_path"]), self.settings.data / "jobs" / state["job_id"] / "pages", self.settings.max_pages)
        update = {"pages": pages, "warnings": ["All extracted measurements require human source verification"]}
        if os.getenv("DOCLING_ARTIFACTS_PATH") and Path(state["input_path"]).suffix.lower() == ".pdf":
            update["docling_text"] = await asyncio.to_thread(docling_text, Path(state["input_path"]))
            self.store.event("extraction.docling_prepared", {"characters": len(update["docling_text"]), "offline_artifacts": True}, state["job_id"])
        return update

    async def extraction(self, state):
        values = await extract(state["pages"], self.registry, self.transport, state["job_id"], state.get("docling_text"))
        values["warnings"] = state.get("warnings", []) + values["warnings"]
        return values

    async def retrieve(self, state):
        query = "inspection thickness pressure remaining life source verification " + " ".join(v["tag"] for v in state["measurements"])
        result = await self.knowledge.search(query, state["job_id"])
        warnings = list(state["warnings"])
        if result.get("warning"):
            warnings.append(result["warning"])
        if any(source.get("synthetic") for source in result["sources"]):
            warnings.append("Retrieved knowledge includes synthetic fixtures; no operating limit is authoritative")
        self.store.event("retrieval.completed", {"mode": result["mode"], "source_count": len(result["sources"])}, state["job_id"])
        return {"retrieval": result, "warnings": warnings}

    async def calculate(self, state):
        warnings = list(state["warnings"])
        try:
            result = await self.sandbox.run(self.settings.data / "jobs" / state["job_id"] / "calculation", SUMMARY_CODE,
                                             {"measurements": state["measurements"]})
            summary = verify_summary(result, state["measurements"])
            self.store.event("sandbox.verified", {"purpose": "descriptive_summary", **result}, state["job_id"])
            return {"summary": summary, "sandbox": result}
        except Exception as exc:
            warnings.append("Sandbox calculation unavailable: " + str(exc)[:400])
            self.store.event("sandbox.unavailable", {"error": str(exc)[:500]}, state["job_id"])
            return {"summary": None, "warnings": warnings}

    async def decide(self, state):
        decision = {"status": "engineering_review_required", "approval_verdict": None,
                    "safety_factor": None, "remaining_life_years": None,
                    "reason": "Approved formulas, thresholds and standard editions have not been supplied"}
        self.store.event("decision.review_required", decision, state["job_id"])
        return {"decision": decision}

    async def document(self, state):
        target = self.settings.data / "jobs" / state["job_id"] / "inspection-draft.docx"
        await asyncio.to_thread(generate_note, state, target)
        return {"artifact": target.name}

    async def code(self, state):
        job_id, prompt = state["job_id"], state["prompt"]
        model, trace = await self.registry.route(prompt, self.transport, job_id, task="code")
        state = {**state, "route": trace, "attempts": []}
        cases = state.get("cases", [])
        last_error = ""
        for attempt in range(1, 4):
            self.store.event("code.attempt", {"attempt": attempt, "model": model["id"]}, job_id)
            messages = [{"role": "system", "content": "Write a self-contained Python program using only the standard library. "
                "Read JSON input from /input/input.json. Print only the JSON result to stdout. Return JSON with one string field code. "
                "Do not access networks, external services, secrets or other files."},
                {"role": "user", "content": prompt + ("\nPrevious verification failure:\n" + last_error if last_error else "")}]
            try:
                raw = await self.registry.chat(self.transport, model, messages, job_id, json_output=True, schema={
                    "type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"], "additionalProperties": False})
                code = parse_json(raw)["code"]
                if not isinstance(code, str) or len(code) > 64000:
                    raise ValueError("Invalid generated code")
                checks = []
                for i, case in enumerate(cases or [{"input": {}, "expected": None}]):
                    result = await self.sandbox.run(self.settings.data / "jobs" / job_id / f"attempt-{attempt}" / f"case-{i}", code, case["input"])
                    if result["exit_code"] != 0:
                        raise ValueError(result["stderr"] or "Program exited unsuccessfully")
                    actual = json.loads(result["stdout"].strip())
                    if cases and json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(case["expected"], sort_keys=True, allow_nan=False):
                        raise ValueError(f"Case {i+1}: expected {json.dumps(case['expected'])}, got {json.dumps(actual)}")
                    checks.append({"case": i+1, "output": actual, "latency_ms": result["latency_ms"]})
                state["attempts"].append({"attempt": attempt, "status": "passed", "checks": checks})
                state["verification"] = "passed_supplied_cases" if cases else "executed_without_correctness_tests"
                state["artifact"] = "solution.py"
                (self.settings.data / "jobs" / job_id / "solution.py").write_text(code, encoding="utf-8")
                self.store.snapshot(job_id, state)
                self.store.event("code.completed", {"verification": state["verification"], "attempts": attempt}, job_id)
                return state
            except Exception as exc:
                last_error = str(exc)[:2000]
                state["attempts"].append({"attempt": attempt, "status": "failed", "error": last_error})
                self.store.snapshot(job_id, state)
                self.store.event("code.failed_attempt", {"attempt": attempt, "error": last_error}, job_id)
                if isinstance(exc, (FileNotFoundError, RuntimeError)):
                    raise
        raise ValueError("Verification failed after 3 attempts: " + last_error)


class JobRunner:
    def __init__(self, workflows, settings, store):
        self.workflows, self.settings, self.store = workflows, settings, store
        self.queue = asyncio.Queue()
        self.tasks = []

    async def start(self):
        interrupted = self.store.rows("SELECT id FROM jobs WHERE status='running'")
        for row in interrupted:
            self.store.execute("UPDATE jobs SET status='interrupted',error=? WHERE id=?", ("Server restarted during execution; retry explicitly", row["id"]))
            self.store.event("job.interrupted", {"reason": "server_restart"}, row["id"])
        for row in self.store.rows("SELECT id FROM jobs WHERE status='queued' ORDER BY created"):
            self.queue.put_nowait(row["id"])
        self.tasks = [asyncio.create_task(self.worker()) for _ in range(self.settings.workers)]

    async def worker(self):
        while True:
            job_id = await self.queue.get()
            try:
                # Atomic claim prevents duplicate execution within the pilot deployment.
                claimed = self.store.execute("UPDATE jobs SET status='running',updated=? WHERE id=? AND status='queued'", (time.time(), job_id))
                if not claimed:
                    continue
                job = self.store.one("SELECT * FROM jobs WHERE id=?", (job_id,))
                state = json.loads(job["state"])
                self.store.event("job.started", {"workflow": job["workflow"]}, job_id)
                if job["workflow"] == "inspection" and self.settings.profile == "industry":
                    result = await self.workflows.inspection.ainvoke(state)
                elif job["workflow"] == "code":
                    from .college_access import current_user
                    if not current_user(self.store, job["user_id"]):
                        raise ValueError("Account is inactive or unavailable")
                    if self.settings.profile == "college" and "code" not in self.workflows.college.config["workflows"]:
                        raise ValueError("Code workflow is disabled")
                    result = await self.workflows.code(state)
                elif job["workflow"] in {"question", "study", "teaching", "letter"}:
                    result = await self.workflows.college.graph.ainvoke(state)
                else:
                    raise ValueError("Unknown or disabled workflow")
                self.store.snapshot(job_id, dict(result), status="completed")
                self.store.event("job.completed", {"artifact": result.get("artifact"), "draft_only": job["workflow"] != "code"}, job_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.store.execute("UPDATE jobs SET status='failed',error=?,updated=? WHERE id=?", (str(exc)[:2000], time.time(), job_id))
                self.store.event("job.failed", {"error": str(exc)[:2000]}, job_id)
            finally:
                self.queue.task_done()

    async def stop(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

