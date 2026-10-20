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
| GITHUB_SOURCE | PUSHED |
| GITHUB_COMMIT | `5164515fb97f06ed5a141297dd836ffd19638702` (tested source commit) |
| WINDOWS_CI | PASS — run `39455293746` on the exact source SHA |
| WINDOWS_INSTALLER | GENERATED — unsigned NSIS, version 0.3.0 |
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

## Final GitHub and Windows acceptance

- Source commit: [5164515fb97f06ed5a141297dd836ffd19638702](https://github.com/Noevrix/AITeamRuntime/commit/5164515fb97f06ed5a141297dd836ffd19638702).
- CI: [run 39455293746](https://github.com/Noevrix/AITeamRuntime/actions/runs/39455293746), completed SUCCESS, matching head SHA.
- Windows CI Python tests: 176 passed, 0 failed, 1 skipped (optional SDK contract).
- Windows CI frontend: 9 passed. React production build PASS.
- Packaged backend lifecycle smoke PASS, Tauri release EXE PASS, NSIS installer PASS.
- Artifact: `ai-team-runtime-windows-unsigned`, ID `12280162617`, 39,227,355 bytes, not expired at verification.
- Server-reported ZIP digest: `sha256:4fe33048c305b10a763fc0c14f7c7add851b8d2af50a9de330528d62d7e05a11`.
- Installer: `AI Team Runtime_0.3.0_x64-setup.exe`. This turn does not install it or replace V0.2.2.
- Local browser smoke: V0.3.0 collaboration workspace loaded, model endpoints disabled. No tasks submitted.
- Protection check: 138 baseline files checked; 14 changed files all in the explicit release allowlist, no unexpected changes; 15 database files unchanged.

This final report is a documentation-only follow-up to the tested source commit.
Its commit uses `[skip ci]` to avoid rebuilding identical application sources.
CI PASS refers specifically to the linked source SHA, not to a new unrun build.
Original development work remains uncommitted on its original HEAD; only the
separate public copy is committed and pushed. No Release or tag was created.

Artifact download verification: PASS. Downloaded using the authenticated GitHub
CLI from the exact successful run into a fresh local directory. Installer size
17,533,071 bytes, ProductVersion 0.3.0, Authenticode NotSigned. Installer SHA-256:
`84E638D7C9FEC23D475910A9AD9CA487A67A0E0C32560FBC33840AD32656C617`.
No installer was executed. Remote ZIP digest is reported as metadata, not a
locally recomputed ZIP checksum.
