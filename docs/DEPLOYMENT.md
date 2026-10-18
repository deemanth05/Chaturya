> Current college setup and actual validation are documented in COLLEGE_GUIDE.md and COLLEGE_VALIDATION.md. The isolation boundaries below also apply to that profile. Set WORKBENCH_LM_HOST to an actually reachable Mac IP before using Compose; the native Windows loopback bridge is a separate topology.

# Deployment and isolation boundaries

## Recommended pilot topology

Mac/Windows browsers → one local workbench server → explicitly allowlisted LM Studio and optional Laya services on the Mac. The server stores reports, accounts, runs, source pages, drafts, audit events and the knowledge index locally. The browser never calls LM Studio directly.

Use the 24 GB Mac as the first inference candidate and benchmark before assigning workloads. Keep model calls serialized initially. The 8 GB Mac is a separate capacity test, not an automatic inference failover. There is no cloud fallback.

The client semaphore limits requests from this workbench process. If a request times out, check the LM Studio queue before repeatedly retrying: the server may still be finishing or cancelling its previous generation. Configure server-side concurrency and model eviction on the Mac as part of capacity validation.

## Enforcement layers

1. All application service requests use a single transport with literal private IP destinations, exact origin/port allowlisting, redirect rejection, disabled environment proxies and audit events. A new destination must be authorized in operator-controlled configuration.
2. Offline/telemetry flags are set before framework imports. Missing model weights or OCR artifacts must be prepared before runtime. The program does not download them on demand.
3. Generated programs run in Docker with `--network none`, no capabilities, no privilege escalation, a non-root user, read-only input/root filesystems, a bounded temporary directory, CPU/memory/process/output limits and a timeout. There is no host-Python fallback.
4. Deployment hosts and the inference Mac still require independently verified firewall rules or a physically isolated network. Application flags and process polling do not enforce isolation for other processes, model runtimes, Docker Desktop or the host itself.

The API's blocked-call button verifies layer 1 before socket creation. It does not test the host firewall. The sandbox integration test exercises network denial from inside a real sandbox container. It does not establish zero external traffic for the whole machine.

## Docker Compose profile

The native Python-server setup is the simplest initial profile on either OS. A Compose profile is also supplied, but its full application image and LAN integration have not been exercised on both target platforms.

The application container joins an `internal: true` network. A separate TCP relay has access to the LAN and forwards only to the configured Mac IP and LM Studio port. The backend's Docker registry file points to the fixed internal relay address. The relay must be prepared in advance. Neither a Docker internal network nor a relay configuration alone proves isolation of the Mac.

Preparation while connected:

```sh
docker build -f infra/sandbox.Dockerfile -t chaturya-sandbox:local .
docker compose build
docker pull alpine/socat:latest
```

The `latest` relay image must be resolved and pinned by digest in your deployment manifest before reproducible pilot deployment. Build the image for the deployment CPU architecture. Record image IDs/digests in the offline bundle.

Set `WORKBENCH_SANDBOX_MOUNT_ROOT` to the absolute host path backing `./data`, expressed in the form accepted by the Docker daemon. The sandbox launcher translates its `/app/data` paths into that host path before launching sibling sandbox containers. Docker Desktop path sharing must allow that folder. Native Windows paths passed from a Linux container may require the Docker Desktop daemon path; verify this profile on the selected host.

```sh
docker compose up --pull never
docker compose exec workbench python -m workbench create-admin administrator
```

The published API port binds loopback by default. Configure a local HTTPS reverse proxy for other users rather than exposing the daemon or model management ports.

The backend currently has access to the host Docker socket to create sandboxes. This makes the backend a trusted controller with powerful daemon access. The socket is never mounted into generated-code containers. A narrow, separately hardened sandbox broker is a production hardening item; this profile should not be described as a hardened multi-tenant security boundary.

## Transfer an offline bundle

Run preparation on each matching OS/CPU target. Download wheels for the full dependency set, include build dependencies, prepare the frontend export, preserve exact package locks, export Docker images and copy locally prepared model/OCR artifacts. Install from local wheels with `--no-index --find-links` and load images with `docker load`; do not run dependency installation commands that can contact registries during runtime.

```sh
docker save -o chaturya-images.tar chaturya-workbench:local chaturya-sandbox:local alpine/socat:latest
# On the matching isolated target:
docker load -i chaturya-images.tar
docker compose up --pull never
```

Image exports can be large; keep them outside the source checkout and record hashes. The repository does not include model weights, OCR weights or an offline wheel bundle.

## Validate on the actual network

- Start all services after disconnecting Internet access while preserving the allowed LAN route. Exercise login, upload, inference, retrieval, sandbox execution and document download.
- Independently capture traffic on the workbench host and inference Macs across startup, warm and cold inference, failures and shutdown. Distinguish local traffic, denied external attempts and successful external traffic; include IPv4, IPv6 and DNS.
- Execute a controlled external-connectivity test from the relevant host/container contexts and retain the firewall denial evidence. Do not infer success merely from an empty application log.
- Check Docker Desktop, LM Studio, OS services and browser behavior separately. The backend monitor samples only the backend process, at intervals, and reports no external byte total.
- Record the capture scope, duration, packet counters, firewall configuration, software/model versions and exact workload before making an isolation claim.

## Pilot operating limits

Accounts, session records and job metadata are stored in SQLite; report files and page images are stored on disk. Passwords are hashed; reports and database contents are not encrypted by the application. Use the host's encrypted storage and a restricted server account. This implementation has retained history but no automated retention/deletion policy or account-revocation UI yet.

Back up `data/` while the service is stopped, or use a SQLite-consistent backup procedure and coordinate it with Qdrant/file snapshots. Do not copy only the SQLite main file while WAL writes are active. Job state is saved after each graph node; the system does not resume a partially executed node after a crash. In-flight runs are marked interrupted for explicit retry.

Document extraction consumes untrusted file data. The pilot bounds file sizes/pages and generated-code execution; stronger document-parser isolation, a sandbox broker, account lifecycle management, TLS, migration tooling, backup/restore drills and host-level enforcement remain hardening work.
