# College workspace interface

The supplied industrial demo was used as a visual reference only. The college workspace preserves its dark zinc panels, compact navigation, floating composer, transitions and dotted processing orb. The reference directory was not modified. No refinery records, timed replies, generated charts, fake users or simulated security readings were carried into the interface.

## Open and use it

Open `http://127.0.0.1:8000` while the local Python workbench is running and sign in with an existing local account. No default credentials are embedded in the interface. On smaller screens use the navigation button; the source inspector opens as a side sheet so the work area remains readable.

1. **Knowledge library:** faculty, staff and administrators can upload an actual PDF, Word document, text file, Markdown document or image, up to 20 MB. Uploads start as private drafts. Extraction and indexing happen locally, without a fabricated progress percentage. An empty installation displays an empty library.
2. **People & access:** administrators create real accounts, assign exact department/course memberships and deactivate accounts. Deactivation revokes sessions. The interface does not pretend to offer unsupported remote password resets or role changes.
3. **Document access:** administrators inspect the original and indexed transcript, then set audience, department, course, version and publication status. Publishing an unverified scan requires explicit transcript verification. Archiving excludes it from retrieval.
4. **Workspace:** choose a tool, enter an actual request and select sources if appropriate. Open Settings for language, evidence basis, letter facts or code tests. Submit with the arrow or Ctrl/Cmd+Enter. Ctrl/Cmd+K starts a new task. Each run is an independent task; prior chat turns are not silently supplied as context.
5. **Inspector:** Sources shows retrieved excerpts and original-file links; Files offers completed Word, Markdown, JSON or Python downloads; Activity shows actual recorded events, routing reasons and timing fields. Probabilities appear only if returned by the router.
6. **History:** browse or search retained runs. Status and failures are preserved. Failed/interrupted jobs can be retried as a new run. Authorized faculty/staff can record review comments; these comments are not approvals or signatures.
7. **System & audit:** inspect configured models, worker limits, allowed destinations, observed connections and retained audit events. Administrators can probe actual model availability and run the application’s blocked-call check.

## College uses

| Tool | Intended use | Required real inputs |
| --- | --- | --- |
| Ask documents | Explain handbook provisions, syllabus topics or accessible notices with excerpts | Actual accessible local documents; unsupported questions return insufficient evidence |
| Study support | Explain engineering concepts and prepare revision material | Local course sources, or an explicitly selected general educational knowledge mode |
| Teaching material | Draft lesson plans, lab guidance and practice material | Faculty/admin role and at least one selected actual course document |
| Office drafts | Prepare correspondence for human review | Authorized role; recipient, subject, purpose and actual supporting facts; local policy sources when selected |
| Code lab | Generate and execute Python inside the local Docker sandbox | Task description; optional input/expected-output cases (up to ten) |

Without supplied code cases, execution is labelled as having no correctness tests. Passing cases establishes only those cases. Drafts must be reviewed before use; the workbench does not issue college decisions, grades or official letters.

## Real data and limits

- Accounts, document counts, source excerpts, run states, routing decisions, model responses, reviews and downloads come from same-origin authenticated APIs. There are no seeded college policies, student records or mock response fallbacks.
- The development history and reference documents have been cleared from the active application. The library and history start empty. Only your subsequent uploads and submitted tasks populate them. A local recovery copy is outside active storage and is neither indexed nor served.
- Model entries describe configuration. Availability checks query the local server; enabled does not mean loaded. Laya is labelled unconfigured when its endpoint is absent.
- Network counters describe logged application activity. External byte accounting is unavailable and displays **Not measured**. A blocked-call check stops at the application policy; it does not certify operating-system firewall enforcement or whole-host air-gapping.
- Sessions remain in HttpOnly cookies. The UI does not store passwords or tokens in browser storage. Access failures clear protected run content; source visibility is enforced by the backend on reads and downloads.
- No external fonts, media, analytics or CDN scripts are required. Markdown does not render raw HTML or load remote images. The reference’s external integrations and voice button are not included.
- Public college handbooks and actual course material have not been supplied. The interface cannot invent them. Upload authorized source material before evaluating college-specific answers.

## Rebuild on Windows or macOS

During preparation, install Node.js 24, then run from the project directory:

```text
npm --prefix frontend ci
npm --prefix frontend run build:local
```

The second command builds a static Next.js export and copies it into `college-console/`. Start the existing Python workbench normally. No separate frontend server is needed. Rebuild after editing UI source and refresh the browser. Keep `NEXT_TELEMETRY_DISABLED=1` in the preparation environment; runtime uses only the exported assets.

The backend Dockerfile includes a Node build stage and copies the export into the Python image. Prepare dependencies and images before disconnecting. For an already prepared image, rebuild/export the UI first, then use the existing offline-update Dockerfile. This update path depends on the prepared runtime and does not download dependencies.

The basic recovery console remains at `/basic.html`. The API contract at `/api/schema` and the Python workflow layer remain available for a later design replacement.
