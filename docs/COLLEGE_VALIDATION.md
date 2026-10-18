# College validation record — 17 October 2026

This record separates actual integration checks from college-data acceptance. The application is a functional pilot; this is not certification for student-record processing or proof of whole-host zero Internet traffic.

**Cleanup on 18 October 2026:** the historical job IDs below document earlier validation only. All 33 pilot runs, five reference/demo documents, 94 indexed chunks and 764 old audit events were removed from active storage at the user's request, together with their artifacts and vector index. The existing account was preserved. A recovery copy is outside the served/indexed data; the current library/history are empty. Sample ingestion/download endpoints were removed, and test assets were isolated under `backend/tests/`.

After cleanup, all **33 regression tests passed**, including actual Docker sandbox checks. Live database checks returned one preserved account and zero jobs, documents, chunks and reviews, with SQLite integrity `ok`. The existing browser session remained valid. The live UI visibly showed **Knowledge library 0**, **Your runs will appear here**, and the empty-library state. No new validation jobs or test documents were added to live storage during these final checks.

## College interface rebuild — 17–18 October 2026

The local industrial design reference was inspected read-only. Its visual layout, animated composer and processing orb were adapted into the college Next.js interface. Reference records, timed answers, simulated actions and invented network/hardware readings were not transferred.

The production static build and TypeScript checks passed. The cross-platform `build:local` command exported the interface to the running FastAPI server. Browser checks confirmed retained run selection, actual question text and output, retrieved source excerpts and section references, completed artifact links, real library metadata, scan-review publication controls, actual account listing and membership loading, model configuration and audit-event rendering. Access settings were inspected without publishing private development documents or changing memberships. Narrow-panel layout was visually checked; the source inspector overlays the workspace instead of squeezing it.

A new study request was entered and submitted through the rebuilt interface with general educational knowledge explicitly selected. Actual Gemma inference produced a completed review draft explaining voltage/current: job `676c870d-fe87-4cf7-817d-cf4f86205960`, backend elapsed **22.3 seconds**. The answer explicitly states it is not grounded in college documents. It remains in real history; no canned response or synthetic college source was used.

This UI verification does not replace college-document acceptance, prove model accuracy, certify whole-host egress isolation or establish production security. Existing backend test results below predate the UI-only rebuild; backend workflow logic was unchanged.

## Backend automated checks

**33 tests passed** on the Windows development workstation with `WORKBENCH_DOCKER_TESTS=1` and a running Linux Docker engine. The suite includes real container execution, no-network/read-only/non-root checks, a deliberately failed generated program repaired on a second attempt, two job workers, retained/recovered queue state, authentication, cross-origin protection, exact model-service allowlisting and redirect rejection.

College checks cover four roles, private faculty uploads, department/course document scopes, filtering dense search IDs before ranking, protected source downloads, own-job isolation, access revocation, inactive-account checks between graph steps, publication attestation for OCR, additive upgrades, queue admission limits, Word table extraction, citation checks, one bounded output-repair attempt and withholding unvalidated results from the API. Controlled model responses are used only inside automated tests for fault injection; these are not measurements of actual model accuracy. No production route returns a canned model answer.

## Actual local-model runs

Generation used `google/gemma-4-12b-qat`; dense retrieval used `text-embedding-nomic-embed-text-v1.5` through `http://127.0.0.1:1234/v1`. This native Windows endpoint exposes the Mac model through the existing LM Studio/LM Link connection. The direct-LAN Docker relay topology was not used for these live requests.

The evidence was the actual operating guide, an image rendered from that guide, a short attributed excerpt from the official Python documentation, and real workbench configuration facts. No fictional institution, fees, attendance threshold, student list or approved syllabus was created. These references are private drafts in the development account and are not installed automatically for new deployments.

| Workflow | Retained job ID | Result | Server elapsed |
| --- | --- | --- | --- |
| Document question | `d777bc18-e262-4c43-914f-022191032c01` | answered | 108.7 s |
| General engineering study | `e145dcef-ba98-4b83-96ff-2b58e385f291` | answered | 37.2 s |
| Teaching draft from actual Python reference | `64ee36d2-83ef-4323-a0fd-9d4064f70e11` | answered | 45.9 s |
| Letter from actual configuration facts | `0da42f50-d083-4f21-856b-45ead325dc7c` | answered | 16.4 s |
| Generated code with real Docker verification | `cd8f6556-4411-4c22-b7cf-df7d499b2e82` | passed_supplied_cases | 9.0 s |
| Question on actual guide-image transcript | `d702ba7a-f5d4-41a6-a53e-47ef69c17c5f` | answered | 17.9 s |

The initial document-question timing predates request tuning. Later runs use per-model `reasoning_effort: none` and `max_output_tokens: 4096`, verified against the installed LM Studio server. Timings are observations on this setup, not performance guarantees.

Word archives were reopened and structurally checked; Markdown and JSON downloads were retrieved, source identifiers/excerpts were checked against stored source text, and outputs retain `review_required: true` and no approval verdict. Citation validation normalizes whitespace only, retaining source words and punctuation. This does not prove semantic entailment or authoritative policy status.

Vision transcription actually called the local vision model and was indexed with Nomic. The resulting document remains `vision_unverified`/draft; no human publication attestation was invented. The scan-answer run succeeded after fixing line-wrap handling. It is a rendered technical-document page, not a real college scan or an OCR accuracy benchmark.

The real generated Python program passed two supplied cases in Docker. The live model succeeded on its first attempt; the failed-first-attempt repair path was separately tested with controlled model responses and real Docker execution.

## Three consecutive retrieval checks after fixes

| Job ID | Expected and observed result | Client elapsed |
| --- | --- | --- |
| `615fff6f-bc31-45be-84c4-49f27577f083` | answered | 26.2 s |
| `0308408b-9d1d-4055-bcb5-9831f5283455` | answered | 34.2 s |
| `4b88dac6-fec8-41c4-8301-5d73da5716c3` | insufficient_evidence | 18.2 s |

The first two answer programming questions from the actual Python excerpt. The third asks for an official college attendance threshold absent from that reference; it completed with `insufficient_evidence` and withheld answer sections. These three runs needed no manual intervention.

## Failures found and corrected

- A teaching request exhausted its output allowance while generating extended reasoning. An actual tiny JSON probe established that this LM Studio version accepts `reasoning_effort: none` and returned zero reasoning tokens. The request option and output allowance now live in the model registry.
- LM Studio briefly reported no loaded model during validation. Those jobs failed visibly; once the model was loaded and answering again, new real runs succeeded. No simulated-response fallback was introduced.
- An inconsistent letter response used an insufficient-evidence status while also returning text. Mode-specific instructions and validation feedback now distinguish a produced draft from an issued/approved document; at most one regeneration is allowed for an invalid structured response.
- A source excerpt differed only in PDF/image line wrapping. Citation comparison now normalizes whitespace, while fabricated words, punctuation changes and unknown identifiers still fail.
- The initial teaching prompt ambiguously referred to a workbench safety guide. The model withheld a syllabus-style answer rather than inventing one. The later subject-material test used the actual Python reference.
- Final review tightened access revocation between graph steps and hid incomplete/failed draft results from normal job responses.

Failed/interrupted development runs remain in retained history as diagnostic evidence.

## Runtime preparation and browser checks

The college console returned HTTP 200, its script passed a syntax check, and its authenticated job view showed the real completed answer and download links. The authenticated API schema excludes industrial fixture/inspection routes in college mode. The project, configuration, current documentation and college console were searched for the institution name and location strings; none were embedded.

The Linux amd64 dependency image built successfully during preparation. A later full rebuild could not fetch a Docker registry authentication token because that external registry request timed out. The final source-only update used `infra/offline-update.Dockerfile` against the already prepared local image, installed no dependencies and succeeded with build networking disabled. The final application image started with `--network none`; requests from inside the temporary container returned ready/college/version 0.2.0 and HTTP 200 for the console. The temporary container was removed afterward. This establishes offline startup of the prepared image, not offline inference over the separate LM Link connection.

## Remaining deployment checks

- Actual approved college handbooks, syllabi, regulations, notices and templates have not been supplied or validated. Real college answer quality remains an acceptance task with those documents.
- The blocked-call check rejected the external destination before any socket attempt. It verifies the application policy. The separate model runtime/bridge and host firewall still require independent isolation checks; process sampling and a null external-byte counter are not evidence of zero bytes.
- DOCX visual rendering was not verified; inspect layout in Word before distribution. No institution-supplied Word template was available.
- macOS server installation and ARM64 container execution were not tested here; Mac-hosted inference was exercised through the existing bridge. LAN HTTPS, backups/restoration, role assignments for actual people and operational retention remain deployment work.
- Laya remains optional/unconfigured, one generation model is active, and multilingual accuracy has not been benchmarked. Configuration-only specialist selection is covered by automated tests, not a live multi-generation-model benchmark.

See COLLEGE_GUIDE.md for installation, all features, college use cases, operating instructions and the future UI contract.
