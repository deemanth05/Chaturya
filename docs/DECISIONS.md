# Accepted project decisions

Recorded 17 October 2026.

| Area | Decision |
| --- | --- |
| Delivery | Pilot using real inspection reports; deadline not yet supplied |
| Clients | Mac and Windows browsers |
| Deployment | One shared workbench server; five users; two active jobs |
| Inference | Mac-hosted LM Studio over a local network |
| Primary model | `google/gemma-4-12b-qat`, hosted on the Mac and exposed through Windows LM Studio at `http://127.0.0.1:1234` using the existing LM Link connection; the supplied direct Mac address is `http://192.168.1.18:1234` |
| Candidate hardware | MacBook Air M5, 24 GB RAM, 512 GB storage; Mac mini M2, 8 GB RAM, 256 GB storage, as stated by the user |
| Preparation | Dependency and weight downloads permitted before isolated operation |
| Decision rules | Draft only; no approval verdict until approved formulas, thresholds, units and standard editions are supplied |
| Initial data | Clearly labelled synthetic fixtures and a basic draft template |
| Priorities | Inspection-to-Word first; accounts, concurrency and retained history immediately |
| Laya | Support the linked Laya-MLX project and compatible typed-decision endpoints |
| Embeddings | Use installed `text-embedding-nomic-embed-text-v1.5` for the pilot, as approved; retain BGE-M3 as a configurable later option |

## Architecture changes from the original plan

The deployment boundary is now an isolated local network containing the workbench server, clients and inference Macs. An allowed call to a separate inference Mac is local service traffic, not external Internet egress. The original single-GPU workstation layout is no longer the deployment assumption.

Two active jobs do not imply two simultaneous generations. The initial model-call limit is one. Waiting and other workflow steps can overlap while the Mac processes a model request.

The MLX runtime must run natively on macOS. Docker hosts the application and isolated code execution; it does not provide Apple Metal inference to Laya-MLX.

The current registry has one enabled generation model. A second model and verified image capability remain deployment prerequisites for the original routing and vision acceptance claims. Qwen and DeepSeek are not assumed to be installed.

## Remaining decisions and gates

- The supplied LM Studio address is reachable and its model list is verified. Confirm the installed server version and evaluate capabilities on representative real reports.
- Supply approved engineering formulas, thresholds, units and standard editions before enabling any approval logic.
- Supply permitted SOP/manual files, representative real reports and the required Word template before a real-data pilot evaluation.
- Choose the host for the shared server and its stable browser-facing address, HTTPS setup and local disk/backup policy.
- Evaluate the configured Nomic dense plus BM25 retrieval on the actual corpus; BGE-M3 is not required for this first pilot after the user's update.
- Evaluate a second generation model and Laya on representative routing prompts; probability values are model outputs rather than guarantees of accuracy.
- Set the pilot deadline and performance target using measurements on the actual Macs.
- Validate OS firewall enforcement and packet capture on every relevant host before claiming isolated operation.

## Deferred scope

Standalone image Q&A, Excel output, PowerPoint output, hash-chained audit records and automated engineering approval are not enabled in this first implementation. The CSV is an input fixture, not an Excel export feature. Code verification is implemented as a JSON-in/JSON-out workflow with user-supplied expected results.

