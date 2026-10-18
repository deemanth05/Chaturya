> Historical industry-profile documentation. For the current college application, use COLLEGE_GUIDE.md and COLLEGE_VALIDATION.md.

# Chaturya local AI workbench

A shared inspection workbench for Mac and Windows browsers, with inference hosted on your Mac through LM Studio. The pilot target is five accounts and two active jobs, with model calls serialized by default.

**Current decision policy:** every inspection produces a draft requiring engineering review. Safety factor, remaining life, acceptance thresholds and approval verdicts are disabled until approved rules and the governing standard edition are supplied. Synthetic fixtures are labelled throughout.

## What is implemented

- Local accounts, password hashing, expiring HttpOnly sessions, roles and access checks on jobs, source pages, downloads and WebSockets.
- Durable SQLite WAL job queue, two workers, retained state after each step, event replay and job history. Queued work survives a restart; in-flight work is marked interrupted and can be retried explicitly.
- A LangGraph inspection flow: bounded upload → image/text preparation → structured local-model extraction → local retrieval → Docker summary and independent check → deterministic review-required decision → Word draft.
- Registry-based model selection with visible reasons and scores; optional Laya typed decisions for ambiguous tasks. Generation and embeddings are separate capabilities.
- Image-only synthetic inspection PDF, PNG, thickness CSV and synthetic knowledge pages.
- BM25 retrieval, embedded persistent Qdrant dense retrieval and reciprocal rank fusion. The pilot uses the installed **Nomic embedding model**, as approved by the user. BGE-M3 remains a disabled configurable option. If no embedding model is enabled, BM25-only operation is openly displayed.
- Code generation with at most three attempts, isolated Docker execution and comparison against user-supplied JSON test cases. No host execution fallback.
- Exact local destination policy, no redirects or environment proxy use for service requests, durable audit events, JSONL mirror and process connection sampling. A blocked-call check tests the application policy before opening a socket.
- Next.js/Tailwind interface served as local static assets by FastAPI. No external fonts, CDN scripts or hosted dependencies are used at runtime.

## Current validation limits

The native workbench currently connects to `http://127.0.0.1:1234/v1`, where Windows LM Studio exposes Mac-hosted models through the existing LM Link connection. The generation identifier remains `google/gemma-4-12b-qat`. The Mac's direct address `http://192.168.1.18:1234` did not respond from this laptop; the Compose relay profile still requires a direct reachable Mac endpoint. See the validation record for completed checks and remaining capability limits. No cloud or simulated-response fallback is enabled in the application. LM Link's own transport requires independent network-isolation validation.

Automated tests use a simulated local model response and **real Docker execution**. This validates integration, scheduling and sandbox behavior, not model accuracy. Additional live checks have reached Gemma and Nomic on the Mac; see [validation](docs/VALIDATION.md) for outcomes and [deployment boundaries](docs/DEPLOYMENT.md) for isolation limits.

## Prepare on Windows

Install Python 3.12, Node.js 22 or newer, and Docker Desktop with Linux containers. Run from this project folder using a real Python installation; the Windows Store alias alone is insufficient.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
npm --prefix frontend ci --no-audit --no-fund
$env:NEXT_TELEMETRY_DISABLED='1'
npm --prefix frontend run build
docker build -f infra/sandbox.Dockerfile -t chaturya-sandbox:local .
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m workbench create-admin administrator
.\.venv\Scripts\python.exe -m workbench serve
```

The initial administrator password is prompted locally. There are no default credentials and no public self-registration. Open `http://127.0.0.1:8000`. An administrator can add inspectors and reviewers through People & access.

## Prepare on macOS

Install Python 3.12, Node.js 22 or newer, and Docker Desktop. Run LM Studio natively on the inference Mac.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix frontend ci --no-audit --no-fund
NEXT_TELEMETRY_DISABLED=1 npm --prefix frontend run build
docker build -f infra/sandbox.Dockerfile -t chaturya-sandbox:local .
cp .env.example .env
.venv/bin/python -m workbench create-admin administrator
.venv/bin/python -m workbench serve
```

Dependency downloads and image preparation belong to the connected preparation phase. Runtime starts without installing dependencies or pulling images. Build separate image/wheel bundles for Windows/Linux amd64 and Apple Silicon arm64; a prepared environment is not interchangeable across platforms.

## Share the server on the LAN

Choose **one shared server**; users on Mac and Windows connect in a browser. Separate deployments have separate accounts and histories. Set `WORKBENCH_ORIGINS` in `.env` to the actual browser-facing origin, for example `http://192.168.1.30:8000`, then run `python -m workbench serve --host 0.0.0.0`. Do not use a wildcard origin. For real credentials and reports, put the server behind your local HTTPS reverse proxy and set `WORKBENCH_SECURE_COOKIES=true`. The built-in server is HTTP only; TLS termination must be prepared separately.

SQLite and embedded Qdrant support this single-server pilot. Run one API process: do not start multiple Uvicorn workers against the embedded Qdrant directory. The server already runs two asynchronous job workers internally. Inspectors see their own jobs; reviewers and administrators can see all jobs. Everyone can read the shared knowledge library; only administrators can add sources or accounts.

## Connect LM Studio

1. Start the model server on the Mac with local-network serving enabled. Keep the Mac awake while jobs run.
2. Confirm its reachable IP and port from the workbench server. Test `python scripts/diagnose_model.py`.
3. Update `config/registry.yaml` if the address or exact model identifier changes. Add the exact service origin under `network.allowed_origins` too. Registry changes take effect after server restart.
4. In Model connections, run the connection/image probe. The image probe is a simple synthetic color check, not an extraction accuracy benchmark.
5. If LM Studio requires a bearer token, set `WORKBENCH_LM_STUDIO_API_KEY` in the untracked server-side `.env`. A registry entry can name a different secret environment variable through `api_key_env`. Tokens are never sent to the browser or written to audit events.

No specific RAM capacity or inference speed is guaranteed. Benchmark Gemma on the 24 GB Mac first. The 8 GB Mac mini is not assumed to fit a 12B generation model; it can be evaluated for a smaller model or Laya. Request queues protect memory but cannot make an oversized model fit. `WORKBENCH_MODEL_TIMEOUT` defaults to 600 seconds for a slow vision request; the connection timeout remains eight seconds. The audit distinguishes model queue wait from service time.

## First inspection

1. Sign in as administrator and add synthetic examples to the Knowledge library.
2. Download the sample report from Workbench. It is a genuine image-only PDF, with expected readings in `fixtures/reports/synthetic-thickness.csv`.
3. Upload the sample and check the synthetic-data box.
4. Follow the saved trace. Confirm the values against the source page and inspect retrieved evidence.
5. Download the Word draft after completion. If Docker is unavailable, the draft explicitly omits the calculation and records that limitation. Model extraction failure stops the run and produces no misleading artifact.

For a real pilot, replace synthetic knowledge with permitted local SOPs and independently evaluate extraction on representative reports. Missing SOP evidence never becomes an invented limit.

## Add models and Laya

Add a supported OpenAI-compatible generation endpoint entry to `config/registry.yaml`; no routing-code change is needed. Models must already be installed and served. Enable a specialist only after testing its capability. An entirely new serving protocol requires an adapter. Only one generation model is supplied today, so multi-model routing acceptance remains pending.

To enable dense retrieval, install a local BGE-M3 embedding model in a compatible serving runtime, confirm the exact model ID, then enable/update the embedding entry and restart. Use **Build dense index** in the Knowledge library to embed existing chunks. Existing BM25-only documents are not silently re-embedded.

Optional Docling support is available through `.[docling]`. Prepare all Docling/OCR model artifacts while connected and set `DOCLING_ARTIFACTS_PATH` to that local folder. The inspection preparation node then runs Docling with remote services disabled and supplies its text as supplemental evidence alongside the page images. Without prepared artifacts, the default path uses PDF text extraction and the model's image input. The optional Docling path has not been exercised in this environment.

Laya-MLX runs natively on Apple Silicon, outside Docker. Prepare its checkpoint and package while connected, then set `LAYA_MODEL_PATH` to the local folder and run:

```sh
.venv/bin/python -m pip install '.[laya]'
LAYA_MODEL_PATH=./models/laya .venv/bin/python scripts/laya_server.py
```

Set `router.laya_url` to its `/v1/systemone` URL, add the exact local origin to the allowlist and restart the workbench. If Laya is on another Mac, explicitly set `LAYA_HOST` and its firewall rules. Alternatively, a compatible Laya server in LM Studio/Ollama can expose `/v1/systemone`; verify the installed runtime supports it. Laya is used for routing only, never as the engineering approval authority.

## Test

```powershell
$env:WORKBENCH_DOCKER_TESTS='1'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=tmp\pytest
```

```sh
WORKBENCH_DOCKER_TESTS=1 .venv/bin/python -m pytest -q --basetemp=tmp/pytest
```

Without `WORKBENCH_DOCKER_TESTS=1`, Docker integration tests are explicitly skipped. The running Docker engine and prepared sandbox image are required for those tests.

## Offline deployment

See [deployment instructions](docs/DEPLOYMENT.md) for trust boundaries, local service relays, image export/import and the remaining host firewall validation. **The monitor deliberately does not claim 0 external bytes.** Process connection sampling cannot establish that, and the Mac-hosted model service needs its own independent enforcement and capture.

The accepted scope and outstanding work are in [project decisions](docs/DECISIONS.md).

Integration references: [LM Studio structured output](https://lmstudio.ai/docs/developer/openai-compat/structured-output), [Nomic embedding task prefixes](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5), [Laya-MLX](https://github.com/mizorewww/laya-mlx).

