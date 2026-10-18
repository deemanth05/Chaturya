> Historical industry-profile documentation. For the current college application, use COLLEGE_GUIDE.md and COLLEGE_VALIDATION.md.

# Validation record

This file distinguishes completed tests from deployment acceptance. It must not be read as proof of zero Internet egress or production readiness.

## Automated integration tests

18 tests passed on the Windows development workstation with a running Docker Desktop Linux engine and the prepared `chaturya-sandbox:local` image.

Coverage includes password hashing and validation; unauthenticated access; inspector job isolation across metadata, downloads, events and page views; administrator-only operations; cross-origin write rejection; unauthenticated WebSocket rejection; exact endpoint allowlisting; redirect rejection; source page validation; non-finite/invalid measurement rejection; configuration-only specialist model addition; Laya low-confidence fallback; sparse and hybrid retrieval with provenance; re-indexing existing sparse chunks; restart behavior; independent summary verification; real container networking and write restrictions; and the code retry loop.

Three inspection jobs completed with simulated model responses and real Docker calculations. The measured worker maximum was two. The code workflow used a deliberately incorrect first simulated generation; the real sandbox comparison failed it, and the second generation passed both supplied cases. This is an integration test, not a measurement of the real model's reasoning accuracy.

## Frontend and fixture checks

The Next.js production static export and TypeScript checks passed. A rebuild hit a sandbox file-permission error and then passed when rerun with access to the same project output directory. The full Linux amd64 application image and sandbox image also built successfully. The application image booted with `--network none`, and its health endpoint returned ready when queried from inside the container. The disposable test container was then removed. Compose configuration validation passed; full deployment of the Compose relay topology remains a separate check.

The login, authenticated workbench, retained history and live source evidence screens were inspected in the in-app browser at its narrow viewport. The synthetic fixture PDF was rasterized with Poppler and its page image inspected; the three readings and labels are legible. The fixture has no text layer.

Word archives were generated, reopened and structurally checked during integration tests. The packaged DOCX rendering helper was attempted but no LibreOffice renderer is available in this Windows runtime. Visual Word layout verification remains pending; no claim of render QA is made.

## Live LM Studio checks

The endpoint `http://172.28.196.227:1234/v1/models` was reached without a bearer token and returned:

- `google/gemma-4-12b-qat`
- `text-embedding-nomic-embed-text-v1.5`

The Gemma model passed a simple synthetic red-image probe. Nomic produced embeddings for 14 synthetic knowledge chunks, which were stored in embedded Qdrant and marked as hybrid-indexed. Nomic uses separate document and query instruction prefixes from registry configuration.

The first live report requests revealed that this LM Studio version rejects `response_format.type=json_object`. The application was corrected to use explicit JSON Schemas for extraction and code generation. The failed runs remain in the temporary preview history.

On the corrected path, one complete live inspection returned all three expected rows: P-101 at 5.8 mm and 12 bar, P-101 at 5.6 mm and 12 bar, and P-202 at 7.2 mm and 8 bar, all from page 1. Its extraction step took approximately 112 seconds. Hybrid retrieval, real Docker calculation and Word archive download succeeded; the checked minimum was 5.6 mm and the mean was 6.2 mm. The decision remained engineering review required with no verdict. Two other jobs in that batch exceeded the initial 180-second model-service timeout.

The default timeout is now configurable and set to 600 seconds. In the fresh batch, two jobs completed with the same correct readings, hybrid retrieval, checked calculations and Word downloads. The third extracted its readings but failed during retrieval after the local model service became unavailable. A live code task also timed out. Thus **three consecutive successful live runs have not been established**, and the live code workflow has not passed its acceptance check. Automatic tests do verify the code retry loop using simulated generations and actual Docker execution.

Fresh-batch job IDs: `db20b690-03f1-4cd4-bdee-a658022cac30` and `afcdfeb6-46d3-4801-b495-e85ef1cdbd7e` completed; `388cdb46-6c9c-4149-b02a-27570fc82ef8` failed during retrieval. The live code job was `d5a1836b-2929-4375-95f1-fd45348d6ee7`.

Measured successful generations in that batch used 1,043 prompt tokens and 1,380 completion tokens and took approximately 169 seconds. Embedding service time was roughly 83–89 ms once it obtained the shared slot. Queue wait is recorded separately and can be much longer than service time. These are observations on the synthetic fixture, not a service-level guarantee.

## Outstanding acceptance checks

- Three consecutive successful live report completions with a stable LM Studio connection, plus a successful real-model code run.
- Extraction quality on representative real inspection reports and ambiguous scans.
- Laya-MLX loading/inference on the Mac and approximately 20 representative routing prompts.
- Two installed generation specialists routed to different tasks; only one generation model is available today.
- The optional Docling offline-artifact path.
- Native macOS startup, end-user LAN access and the full Compose image/profile on both target architectures.
- Word layout rendering and review of every page.
- Host/inference-Mac firewall enforcement and independent packet capture. The monitor reports external bytes as unavailable, never as a fabricated zero.
- Approved engineering calculations and decision thresholds, which are intentionally disabled pending the user's source rules.

## Scope of sovereignty evidence

The controlled application-policy test blocks an external destination before a socket call. The real sandbox test confirms a connection cannot be established from a `--network none` container. Backend process sampling and audit logs cover their stated scopes only. Neither test proves the entire workstation, browser, Docker daemon or inference Mac made zero external calls.

## Updated Mac address check

The user subsequently changed the LM Studio address to `http://192.168.1.18:1234`, retaining model identifier `google/gemma-4-12b-qat`. The native registry, exact network allowlist, Compose relay destination and diagnostic default were updated. Historical results above still describe the previous address.

The workbench was started on `http://127.0.0.1:8000` using the existing pilot accounts and retained history in `tmp/preview-data`. Both the direct model-list check and the in-application model probe timed out at the new Mac address. Synthetic inspection job `da2def1f-d945-4ef3-96de-da96733ab375` therefore failed at extraction without generating a document.

The Windows Wi-Fi interface reported `172.16.85.6/16`. A ping to the Mac address also timed out. Different subnets can communicate when routing is provided, but no working connection to the new endpoint was established in these checks. Confirm a routable connection between the devices and LM Studio local-network serving before repeating live inference.

After the address change, all 18 regression tests passed with real Docker sandbox checks enabled, and Compose configuration validation passed. The local workbench health endpoint and interface both returned HTTP 200. The workbench was left running as requested; live Mac inference remains unverified at the new address.

## Updated LM Studio and LM Link connection

After the user's LM Studio update, Windows LM Studio reported version 0.4.26 and showed the Gemma model ready on `Ameys-MacBook-Air.local` through the existing LM Link connection. Its local API server was stopped. Starting that existing server exposed `http://127.0.0.1:1234`; `/v1/models` successfully listed Gemma, Nomic embeddings, `laya@bf16`, `laya@q8_0` and `laya-mlx`.

The native registry and exact service allowlist now use `http://127.0.0.1:1234`, keeping the same Gemma identifier and Mac-hosted generation. The direct Mac address still timed out from this Windows network. The Compose relay profile remains configured for the direct Mac address and requires separate connectivity validation; a container's loopback address cannot reach Windows LM Studio.

The application model probe passed image input through the updated connection, and all 18 regression tests passed again. Live synthetic inspection `507381fc-dc74-4ff0-8acf-62a573951f01` was started through the application to verify extraction, retrieval, Docker calculation and Word generation.

That live inspection completed successfully. Every extracted tag, thickness, pressure and source page matched the independent CSV fixture. Hybrid retrieval completed; a real `sandbox.verified` event confirmed the descriptive calculation, with minimum thickness 5.6 mm and mean thickness 6.2 mm. The generated Word archive downloaded successfully, and the decision remained engineering review required with a null approval verdict. This establishes one complete successful run on the updated LM Link connection, not the outstanding three-run reliability check or visual Word layout QA.

The application's allowlist covers its calls to the local LM Studio API. It does not measure or enforce LM Link's own transport, so an independent audit of that transport is required before claiming air-gapped operation.
