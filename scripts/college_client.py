"""Real API client: authenticate, optionally ingest a real file, run and download.

No canned model responses, generated corpus or demo accounts are installed.
"""
import argparse
import getpass
import json
import os
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--username", required=True)
    parser.add_argument("--source", type=Path, help="Actual local PDF, Word, text, Markdown or image file")
    parser.add_argument("--document", action="append", default=[], help="Existing accessible document ID")
    parser.add_argument("--workflow", choices=["question", "study", "teaching", "letter"], default="question")
    parser.add_argument("--grounding", choices=["local", "general", "provided_facts"], default="local")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--language", default="English")
    parser.add_argument("--facts", type=Path, help="JSON file of actual supplied letter facts")
    parser.add_argument("--output", type=Path, help="Download DOCX, Markdown and JSON into this directory")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    password = os.getenv("WORKBENCH_CLIENT_PASSWORD") or getpass.getpass("Password: ")
    origin = args.server.rstrip("/")
    with httpx.Client(base_url=origin, headers={"Origin": origin}, trust_env=False, follow_redirects=False, timeout=900) as client:
        def request(method, path, **kwargs):
            response = client.request(method, "/api" + path, **kwargs)
            response.raise_for_status()
            return response.json()
        request("POST", "/auth/login", json={"username": args.username, "password": password})
        try:
            ids = list(args.document)
            if args.source:
                with args.source.open("rb") as stream:
                    document = request("POST", "/knowledge", files={"file": (args.source.name, stream)},
                        data={"metadata": json.dumps({"audience": "private", "status": "draft"})})
                ids.append(document["id"])
                print("Indexed actual source:", document["id"], document.get("mode"), document.get("extraction"))
            facts = json.loads(args.facts.read_text(encoding="utf-8-sig")) if args.facts else {}
            job = request("POST", "/jobs/college", json={"workflow": args.workflow, "grounding": args.grounding,
                "prompt": args.prompt, "language": args.language, "document_ids": ids, "facts": facts})
            print("Job:", job["id"], flush=True)
            until = time.monotonic() + args.timeout
            last = None
            while job["status"] in {"queued", "running"} and time.monotonic() < until:
                events = request("GET", "/jobs/" + job["id"] + "/events")
                if events and events[-1]["id"] != last:
                    last = events[-1]["id"]
                    print(events[-1]["kind"], json.dumps(events[-1]["payload"], ensure_ascii=False), flush=True)
                time.sleep(2)
                job = request("GET", "/jobs/" + job["id"])
            if job["status"] != "completed":
                raise SystemExit(f"Job {job['status']}: {job.get('error') or 'still running; inspect retained history'}")
            print(json.dumps(job["state"]["result"], ensure_ascii=False, indent=2))
            if args.output:
                args.output.mkdir(parents=True, exist_ok=True)
                for format in ("docx", "md", "json"):
                    response = client.get(f"/api/jobs/{job['id']}/download", params={"format": format})
                    response.raise_for_status()
                    target = args.output / (job["id"] + "." + format)
                    target.write_bytes(response.content)
                    print("Saved:", target.resolve())
        finally:
            request("POST", "/auth/logout")


if __name__ == "__main__":
    main()
