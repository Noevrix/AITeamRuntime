# V0.3.0 — Conversational Multi-Agent Collaboration

Date: 2026-10-21. Development and acceptance are offline; no real model calls.

| Item | Result |
| --- | --- |
| CONVERSATIONAL_TASK_CREATION | PASS — backend persistence, clarification, plan edits and explicit confirmation |
| AGENT_MESSAGE_RELAY | PASS — offline verified through existing adapters' generic message interface and Kernel; real workflow NOT_RUN |
| DSH_REAL | NOT_RUN — prior versions verified; current Python lacks optional SDK |
| CODEX_REAL | NOT_RUN — prior versions verified; new workflow not invoked |
| WORKBUDDY_REAL | AUTH_REQUIRED |
| PARALLEL_EXECUTION | NOT_SUPPORTED — bounded serial scheduling |
| CROSS_REVIEW | PASS — offline actual fixture files/command evidence and strict decisions; real review NOT_RUN |
| OFFLINE_TESTS | Targeted backend 44 passed; frontend 9 passed; original unit/integration 177 passed; public-copy regression 176 passed, 0 failed, 1 skipped |
| GITHUB_SOURCE | NOT_RUN — pending final audit |
| GITHUB_COMMIT | NOT_CREATED |
| WINDOWS_CI | NOT_RUN |
| WINDOWS_INSTALLER | NOT_GENERATED for V0.3.0 |
| REAL_MODEL_CALLS | 0 |

## What changed

- Default collaboration workspace; existing dashboards remain.
- Persisted goals and user supplements, DSH questions and same-conversation
  clarification. Exact plan-version confirmation; edits invalidate old approval.
- DSH proposal → Codex critique reading a stored message → DSH revised plan
  reading both messages. Maximum two explicit discussion cycles.
- Dependency-ordered Codex implementation in a conversation-specific workspace.
- App-server commandExecution receipts, bounded real file contents and hashes
  passed to DSH cross review, with post-review hash verification.
- Explicit status/errors, cancellation, interrupted-run detection and no
  automatic model retries or restart replay.
- Reused SQLite collections, TaskManager, EventBus, Blackboard and TeamKernel;
  no schema migration or deletion of historic records.
- Original DSH/WorkBuddy adapters unchanged. Codex retains old behavior by
  default; optional read-only discussion policy and command receipt capture added.

Core files: `src/ai_team/console/collaboration.py`, `server.py`, `service.py`,
`desktop.py`, `src/ai_team/providers/codex/adapter.py`,
`console/src/Collaboration.jsx`, `App.jsx`, `style.css`.
Tests: `tests/unit/test_collaboration.py`, `test_console.py`,
`console/src/Collaboration.test.jsx`, `App.test.jsx`.
Version metadata: Python, npm lock/package, Tauri Cargo/config.
Documentation: README, this report and `docs/conversational-workspace.md`.

## Verification and evidence boundaries

The offline workflow uses injected Mock providers. It proves durable message
relay, input references, exact plan consumption and evidence plumbing, not
successful paid model execution. All real task inputs use the same existing
send_message adapter path; no front-end generated agent responses are inserted.

Codex's readOnly policy and commandExecution fields were checked against the
existing locally generated app-server JSON schema. DSH uses the established
account route and 4096/off settings. The current default Python environment
does not have the optional SDK; no SDK was installed and no runtime started.

Tests exercise consent, CSRF, duplicate starts, clarification limits, dependency
validation, recovery, unavailable providers, timeouts, cancellation, failed
tests, invalid reviews and secret-shaped data rejection. Frontend checks cover
read-only opening, explicit model consent, rapid duplicate submit protection
and agent provenance. React production build passed.

## Limitations

No simultaneous execution, native pause/resume, automatic rework, broad
research toolchain or verified three-Agent workflow. DSH no-tools prompts are
advisory; the SDK profile retains its tool permissions. Users must close other
DSH processes sharing the home and explicitly opt into trusted real work.
The host does not independently rerun Codex tests. Artifact and test-command
allowlists target small code tasks; missing evidence stops approval.

The Windows package intentionally omits optional DSH SDK/runtime; real
collaboration currently requires the source environment with that dependency.
This is not a claim that the installer can run real DSH out of the box.

## Source protection and release

Original HEAD remains `479e433db9f4da402cdace76738844bd618964a9`.
Existing uncommitted development work is retained. The separate public copy
starts at `d4e9483781a13f41596b4740ee2289c7f2479d30`; its history and sanitized
documents are preserved. Only explicitly reviewed changed files are selected.
No database, run history, credential, private configuration or build cache is
part of the public change. Apache-2.0 remains unchanged.

See [workspace startup and limits](docs/conversational-workspace.md) for exact
commands. Opening the workspace does not call models; no real smoke test has
been performed for this release.

Regression environment note: sandbox run had 176 pass / 1 Windows DPAPI failure.
A normal-user attempt encountered shared pytest temporary-directory permissions
(69 pass / 108 setup errors). A new unique temporary directory under the normal
user resolved both environment issues: 177 passed. No code or test was weakened.

Public-copy regression: 176 passed / 0 failed / 1 skipped. The skipped SDK
parameter-contract test requires the optional SDK. The original project has a
local SDK under ignored runs/dsh-sdk used by that test only; it is deliberately
not copied to the public release. The source runtime still needs an importable SDK.

Security audit: 127 candidate files, 112 reachable history blobs. No history
pattern findings. The only working-tree match is a synthetic credential literal
in the new redaction regression test, reviewed as test data. Apache-2.0 bytes
match the existing public license. No private absolute paths or runtime data
are included in this update. Heuristic scanning is not a universal secret proof.
