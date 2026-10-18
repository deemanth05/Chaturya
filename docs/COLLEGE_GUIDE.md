# Local College AI — operating guide

## What has been built

A local engineering-college AI backend with four primary workflows: document questions, study support, teaching-material drafts and administrative letter drafts. A fifth programming-practice workflow generates Python, runs it inside Docker and compares its output with supplied test cases.

The application has generic branding. There is no preloaded college identity, course catalogue, attendance rule, examination rule, fee, student record or fabricated knowledge base. Administrators supply the actual documents and access assignments. Test inputs live only under `backend/tests/`, are excluded from the backend image and have no sample-loading endpoint. The active document index and run history have been cleared.

The browser workspace uses the supplied design reference’s dark panels, animated composer and evidence inspector, adapted for college tools. Its documents, accounts, runs, answers and downloads come from the real backend. See [the interface guide](COLLEGE_UI.md) for a tour. The API remains independent of the visual design.

## What each college group can do

| Group | Practical uses | Controls |
| --- | --- | --- |
| Students | Ask about accessible handbooks and syllabi; revise engineering concepts; request source-based explanations; practise Python with expected-output cases | Own job history only; published college/student documents within assigned departments and courses; no faculty-only material |
| Faculty | Draft lesson plans, lab guidance and proposed practice questions from actual course material; search accessible documents; add private working notes | Teaching requires a selected document; uploads remain private drafts until an administrator publishes them; no visibility into other users' jobs |
| Office staff | Draft correspondence using supplied recipient, subject, purpose and other real facts; consult accessible procedures and notices | Draft only; no invented signatures, fees or approvals; staff-restricted documents are separate from student material |
| Administrators | Create/deactivate accounts, assign memberships, publish/archive documents, verify transcripts, review all jobs and audit events | Publishing is explicit; account deactivation revokes sessions; administrators can inspect retained data |

Faculty and staff can record a review on their own completed jobs; administrators can review any job. A recorded review is a note, not a digital signature or an approval decision. No workflow automatically grades students, issues certificates, approves admissions or makes disciplinary decisions.

## Preparation and installation

Use Python 3.12, Node.js 24 and Docker Desktop with Linux containers on Windows or macOS during preparation. LM Studio runs the actual models. Download dependencies, container images and weights during preparation. Build the interface once with `npm --prefix frontend ci` and `npm --prefix frontend run build:local`. The exported interface runs inside the Python server; Node is not required at runtime. The backend Dockerfile builds it automatically.

Windows, from the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
docker build -f infra/sandbox.Dockerfile -t chaturya-sandbox:local .
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m workbench create-admin <your-admin-username>
.\.venv\Scripts\python.exe -m workbench serve
```

macOS:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
docker build -f infra/sandbox.Dockerfile -t chaturya-sandbox:local .
cp .env.example .env
.venv/bin/python -m workbench create-admin <your-admin-username>
.venv/bin/python -m workbench serve
```

Replace angle-bracket placeholders with actual values. Do not copy `.env.example` over an existing configured `.env`. Administrator creation prompts for a password of 12–256 characters; there are no built-in credentials or public self-registration. Run each command against the same `WORKBENCH_DATA` directory. Open `http://127.0.0.1:8000` and sign in.

If pip was not installed with the virtual environment, repair/install pip using your Python installation before continuing. Dependency installation and Docker image preparation require internet access during preparation, not during normal model calls.

## Connect the real local models

`config/registry.yaml` controls model IDs, endpoint URLs, modalities and scoring. The currently verified native connection is:

- Generation/vision: `google/gemma-4-12b-qat`.
- Embeddings: `text-embedding-nomic-embed-text-v1.5`.
- API base URL: `http://127.0.0.1:1234/v1`, supplied by LM Studio on this Windows laptop over its existing connection to the Mac.

That loopback address is specific to the machine running the backend. On a different workstation, use a reachable LM Studio address and update both the model `base_url` and exact `network.allowed_origins` entry. A direct Mac connection has the form `http://<reachable-Mac-LAN-IP>:1234/v1`; allowlist the matching origin without `/v1`. Keep LM Studio and the Mac awake. Optional API tokens belong in `WORKBENCH_LM_STUDIO_API_KEY` in the untracked `.env`, never browser code.

The router selects text reasoning for questions/study, writing for teaching/letters, image extraction for scans and code generation for programming. Registry scoring chooses among enabled models supporting that capability, and the reason is logged. With one generation model enabled these tasks correctly use that same model. Add another installed model with a higher relevant strength in the YAML, then restart; adding a model does not automatically authorize another network host. Laya is an optional adapter and is disabled until its endpoint is configured and validated; installation alone does not enable it.

Two job workers run concurrently, while model calls are serialized by default to protect the Mac's memory. The installed LM Studio version was verified to accept reasoning_effort: none for Gemma; the registry uses it to avoid consuming the structured-draft output budget on hidden thinking, with max_output_tokens set to 4096. These are per-model request settings, not changes to LM Studio global settings. Leave reasoning_effort absent for another server until its supported values are verified. More users do not mean every model is loaded at once. The 8 GB Mac should not be assumed to support the same model load as the 24 GB machine.

## Resume the currently running development session

The current local session is running at `http://127.0.0.1:8000` with its existing account in `tmp/preview-data`. On 18 October 2026, all 33 existing pilot runs, five reference/demo documents and their indexes/artifacts were removed from active storage at the user's request. Your account remains usable. The library and history now start empty; upload actual college sources before document-grounded use. A local recovery copy is outside active storage and is not served or indexed.

The untracked local `.env` selects `WORKBENCH_DATA=./tmp/preview-data`, so a normal restart from this project keeps your account. For a fresh college deployment use a separate empty data directory and create the actual administrator there. Do not run two application processes against one embedded Qdrant directory.

## First administrator setup

1. Sign in and use **People & access → Create account** to add actual faculty, office staff and students. Use a unique initial password per account. Accounts are created only by an administrator.
2. Open **Manage** for an account to assign actual department/course identifiers, one per line. Identifiers are exact, case-sensitive strings; use the same identifiers on documents and memberships. Empty course and department fields mean no restriction at that level.
3. Upload actual syllabi, handbooks, academic regulations, lab manuals, approved notices and office procedures under **Knowledge library → Add document**. Set the version; uploads start as private drafts. Administrators can then set the intended audience and restrictions.
4. In **Knowledge library**, use **Read transcript** and download the original. Open the document’s settings to publish only the material that should be shared evidence. Set department and course restrictions where needed.
5. Keep teaching answer keys and internal office records in appropriate restricted audiences. A document with audience `faculty` does not become visible to a student who merely belongs to its course.

If both department and course are set, a reader must have both memberships. Private documents are visible only to their owner and administrators. Archived documents are excluded from retrieval. Owners may use their own unpublished drafts, but the result warns that these are not official policy. Administrators can view archived records for governance but cannot retrieve them as current evidence.

## Uploads, scans and document versions

Supported input: PDF, DOCX, UTF-8 TXT/Markdown and PNG/JPEG. Uploads are bounded to 20 MB. Text PDFs are limited to 200 pages; scanned or mixed PDFs requiring the vision path are limited to 10 pages per file. Split longer scanned documents before upload. PDFs retain source page numbers. DOCX, TXT and Markdown use section/chunk references because they do not supply reliable pagination.

Scanned pages are transcribed by the real local vision model. There is no canned OCR result. The transcript is indexed as an unpublished `vision_unverified` draft. An administrator must compare indexed chunks with the original and publish it with `transcript_verified: true`. This is a recorded human attestation; it does not automatically establish OCR accuracy. Check formulas, symbols, tables and numerical values especially carefully.

Different file contents create different document versions. Upload the replacement, set its version label, and archive the superseded document. The application does not infer which of two conflicting regulations is authoritative merely from filenames or upload dates. Identical file contents are deduplicated; ask an administrator to change the existing document's audience rather than silently making a private duplicate public. Documents are archived rather than deleted through the pilot API.

BM25 and dense Qdrant retrieval are combined with reciprocal rank fusion. Nomic embeddings are computed locally. Disabling all embedding models explicitly selects BM25-only mode; a configured embedding service failure is reported, not replaced by fabricated vectors. Department, course, audience, publication status and synthetic-data restrictions apply before evidence is passed to either the dense search or the generation model. The same access checks protect source downloads and indexed chunks.

## Use the four main workflows

### College-document question

Choose **Ask documents**. Ask a specific question and optionally select relevant documents using **Sources** in the composer. Without a selection the system searches all documents you can access. If there is no accessible matching evidence, it returns `insufficient_evidence` without asking the model to invent a college answer.

Each generated section must carry a valid source identifier and an excerpt matching the supplied source words and punctuation. Whitespace differences, such as PDF line wrapping, are normalized. Invalid or missing references block release. A malformed structured draft gets one regeneration attempt with validation feedback; it is withheld if checks still fail. Incomplete and failed jobs do not expose their unvalidated result through the API. Read the citations and original before relying on a result: an exact citation proves traceability, not that every model statement follows logically from it. Undated or conflicting policies still need a responsible person's interpretation.

### Study support

Choose **Study support**, then use **Settings → Evidence basis → Local documents** for syllabus/notes-based revision, or explicitly choose **General educational knowledge** for a conceptual explanation independent of college documents. The latter is clearly labelled as model knowledge, not college policy. Suitable requests include engineering mathematics explanations, circuit concepts, algorithm walkthroughs and revision questions. General tutoring does not require a fabricated syllabus.

Select the requested output language. English is the default; other languages are passed to the model, but translation and technical terminology quality require verification. This pilot does not certify multilingual accuracy.

### Teaching material draft

Faculty or administrators select an actual syllabus or course-material document and request a lesson plan, lab guidance or proposed practice questions. Selection is mandatory. The workflow grounds the draft in supplied course material, adds source excerpts and marks output for review. It must not invent official course outcomes, credits or examination approval. Drafted exercises are proposals. The pilot does not connect to a timetable, LMS or examination system.

### Administrative letter draft

Faculty, office staff or administrators choose **Office drafts**. In **Settings**, choose **Only facts I provide** for factual correspondence, or **Local documents** when the draft relies on a policy. Fill the recipient, subject and purpose fields and add other real details needed for the letter. API clients supply these as a `facts` object. Missing required fields are rejected before generation. Other missing essentials should be returned as information needed instead of invented text. Read the result before use; user facts are assertions, not verified student records.

No letter is sent, issued, digitally signed or recorded in an external system. The result is a draft.

## Programming practice

Choose **Code lab**, enter the Python task and configure a JSON list of cases in **Settings**, each containing an `input` object and an `expected` result. Generated code reads `/input/input.json` and prints a JSON result. The system executes it in a real Docker container and compares output with the supplied cases. Up to three generation/verification attempts are allowed. Failed verification is returned to the model for repair. Connection or missing-Docker failures are reported rather than retried as if they were code defects.

Containers have no network, a read-only input mount/root filesystem, a non-root user, dropped capabilities, memory/CPU/process/output/time limits and temporary scratch space. Code never falls back to execution on the host. Without expected cases the result is labelled `executed_without_correctness_tests`, not correct or graded. Passing the supplied cases does not prove correctness for every possible input. Only the Python standard library is available in the prepared sandbox image.

## History, review and downloads

Select a run to see status, result, routing and step events. Successful college runs provide Word (`.docx`), Markdown (`.md`) and JSON (`.json`) downloads. Programming runs provide the generated `.py` file. Evidence references are explicit source notes; the current Word exporter does not create native Word footnotes or apply an institution-supplied template.

Queued jobs survive a server restart. Jobs interrupted while running are marked `interrupted` and can be retried explicitly with `POST /api/jobs/{id}/retry`; failed jobs can be retried too. Do not resubmit a slow request simply because the model is taking several minutes. Two active jobs are supported; later jobs queue. Admission is limited to 50 pending jobs overall and 10 per account by default; configure WORKBENCH_QUEUE_TOTAL and WORKBENCH_QUEUE_PER_USER to change those limits. Results and audit events remain on local disk. There is no automatic retention purge, backup scheduler or ERP integration.

Students, faculty and staff see their own runs. Administrators can review all runs. If access to a job's source is revoked or a source is archived, a non-administrator can no longer fetch that job's result, events or download. This does not revoke files previously downloaded. Store data and backups on an appropriately protected disk.

To reset a password locally:

```text
python -m workbench reset-password <username>
```

Use the environment's actual Python executable and the correct `WORKBENCH_DATA`. Password reset revokes existing sessions. Administrators can deactivate an account through `PATCH /api/accounts/{id}` with `{"active":false}`. The pilot has no self-service password change, SSO, MFA or student-information-system identity sync.

## Use from a script

The included client uses real API calls and prompts for your password:

```text
python scripts/college_client.py --username <username> --workflow study --grounding general --prompt "Explain the difference between a stack and a queue" --output output/study
python scripts/college_client.py --username <faculty-username> --source <actual-local-syllabus-file> --workflow teaching --prompt "Draft a short source-based lesson outline" --output output/teaching
python scripts/college_client.py --username <username> --document <accessible-document-id> --prompt "Explain the relevant procedure in this document" --output output/answer
```

The source-upload command creates a private draft. Reuse its returned document ID later; a repeated identical upload returns a conflict. `--facts <actual-json-file>` supplies letter facts. `--server` changes the workbench address. Optional `WORKBENCH_CLIENT_PASSWORD` supports a controlled automated test; avoid saving passwords in shell history or files. The client does not install demo accounts or seed data.

## Integrate the final UI

Use the same browser origin as the API, normally by serving the built UI from FastAPI or putting both behind one local reverse proxy. The UI source is in `frontend/`; `npm --prefix frontend run build:local` exports it to `college-console/`. Backend code does not depend on its DOM or styling. The earlier basic console remains at `/basic.html` for recovery.

1. `POST /api/auth/login` with username/password. Keep the HttpOnly session cookie; do not copy credentials into browser storage. `GET /api/auth/me` retrieves the active role.
2. `GET /api/college` supplies enabled workflows and role constraints. `GET /api/knowledge` lists only accessible documents.
3. `POST /api/jobs/college` submits a job. Use the returned ID for history, events and downloads.
4. Connect to `/api/jobs/{id}/stream?after=<event-id>` with `ws:` or `wss:` matching your deployment. Replay events after the last received ID; the stream includes heartbeats. Polling `/events?after=...` and `/jobs/{id}` is also supported.
5. Display routing, evidence excerpts, source references, warnings, insufficient-evidence states and required review. Do not label an output approved simply because the job completed.
6. Offer `/api/jobs/{id}/download?format=docx`, `md` or `json`. Original sources are `/api/knowledge/{id}/download`; extracted text is `/chunks`.

`GET /api/schema` returns the authenticated OpenAPI contract. Mutation requests require an allowed browser `Origin` with cookie authentication. Same-origin `fetch` sends this automatically. Script clients must supply it explicitly. No wildcard CORS is enabled.

Example job body (field names only; values must reflect an actual request):

```json
{
  "workflow": "question",
  "prompt": "Explain the procedure described in the selected document",
  "grounding": "local",
  "language": "English",
  "document_ids": [],
  "facts": {}
}
```

Other administration endpoints: `POST /api/accounts`, `PUT /api/accounts/{id}/memberships` with `departments`/`courses` arrays, `PATCH /api/knowledge/{id}` with audience/status/scope/version metadata, `POST /api/knowledge/reindex-dense`, `POST /api/jobs/{id}/reviews`, and `GET /api/audit`. Uploads use multipart `file` plus a JSON-encoded `metadata` form field.

## Shared Mac/Windows deployment

Choose one trusted machine as the central application/data host. Keep models on the Mac. Bind FastAPI to the trusted LAN using `serve --host 0.0.0.0 --port 8000`, configure `WORKBENCH_ORIGINS` to the actual browser URL, and arrange the host firewall for the intended college network. Use a local HTTPS reverse proxy and `WORKBENCH_SECURE_COOKIES=true` before handling real student data over a shared network. Keep only one application process/replica against the embedded Qdrant directory; two internal workers provide the supported concurrency.

The current native LM Studio bridge is verified on Windows. It is not the same as the optional Docker Compose relay topology. Compose requires a directly reachable Mac address in `WORKBENCH_LM_HOST`, an absolute host data path in `WORKBENCH_SANDBOX_MOUNT_ROOT`, prebuilt images and validated routing. Docker loopback is not Windows loopback. The controller's Docker socket is a privileged trust boundary; generated code must never get that socket. A dedicated sandbox broker is a future hardening step.

For source-only updates when dependencies are already prepared, `docker build --network none --pull=false -f infra/offline-update.Dockerfile -t chaturya-workbench:local .` reuses the existing local application image and installs nothing. Prepare a new full image whenever dependencies change.

Back up the complete data directory while the application is stopped, including SQLite, audit log, source files, job files and Qdrant data. Copying a live index/database piecemeal is not a verified backup procedure. Existing users and jobs are preserved by additive migrations. Legacy accounts without a new college role resolve inspector to staff and reviewer to faculty; new accounts use explicit college roles. The original SQLite role column is retained for compatibility and `college_role` is authoritative for new accounts. Existing legacy documents migrate to archived/private metadata; an administrator must deliberately publish any real material intended for college use.

## Local operation and its verification limits

All application model/embedding calls pass through an exact local-address allowlist. Redirects and environment proxies are disabled, offline/telemetry flags are set, and no cloud fallback or runtime canned response exists. User documents are data, not instructions to run tools. Search/generation do not autonomously follow links found in files. The administration blocked-call check demonstrates application rejection before a socket is opened; audit events record it.

The process monitor is sampled evidence, not complete packet accounting. It does not measure the separate LM Studio/LM Link process, and `external_bytes: null` means not measured, never zero. A fully air-gapped/zero-egress claim still requires independently configured and tested host/network isolation for the application, model host and any bridge. This pilot must not advertise proven zero external traffic based solely on its application logs.

Real college answer quality cannot be certified before actual approved college documents are provided and reviewed. OCR accuracy, source relevance and model inference can fail. Exact excerpt validation does not prove entailment or authority. The generated DOCX format has structural checks; visual rendering has not been verified on this workstation because the supported rendering dependency is unavailable. Inspect exported Word layout before distribution. See `COLLEGE_VALIDATION.md` for the actual checks completed in this build.
