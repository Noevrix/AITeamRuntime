# Public release manifest — V0.2.2

Independent source snapshot; no original Git objects/history imported.
Apache-2.0 retained. Original private workspace and all user data remain untouched.
No model/OAuth/API smoke calls were performed. WorkBuddy remains PARTIAL / AUTH_REQUIRED.
Historical reports are records of past verification, not current online status.
Windows CI/EXE/installer were not yet verified when preparing this initial snapshot.

Every included source file was read and checked for credential signatures, local paths,
private artifacts, size, file purpose and allowed location. Heuristic checks do not
guarantee detection of arbitrary unlabeled secrets. No known credential risk remains
in this source snapshot. Binary distribution and transitive Rust notices still require
review after a successful build.

## File-by-file disposition

| Path | Review status | Purpose / changes / exclusion reason |
| --- | --- | --- |
| `.env.example` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `.github/workflows/windows-build.yml` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `.gitignore` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `GITHUB_RELEASE_READINESS.md` | EXCLUDED | Local release audit; superseded by public manifest |
| `LICENSE` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `README.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `SECURITY.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `THIRD_PARTY_NOTICES.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `V0_1_1_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `V0_1_2_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `V0_1_3_1_DIAGNOSTIC_REPORT.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `V0_1_3_2_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `V0_1_3_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `V0_1_3_FINAL_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `V0_1_4_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `V0_1_5_1_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `V0_1_5_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `V0_1_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `V0_2_0_ACCEPTANCE_REPORT.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `V0_2_1_ACCEPTANCE_REPORT.md` | EXCLUDED | Local environment/working-tree diagnostic; retained privately |
| `console/index.html` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/package-lock.json` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/package.json` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/src-tauri/Cargo.toml` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/src-tauri/build.rs` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/src-tauri/src/main.rs` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/src-tauri/tauri.conf.json` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/src/App.jsx` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/src/App.test.jsx` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/src/main.jsx` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/src/style.css` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `console/vite.config.js` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `docs/architecture.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `docs/codex-integration.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `docs/console.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `docs/dsh-auth-setup.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `docs/dsh-desktop-reuse.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `docs/dsh-investigation.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `docs/windows-desktop.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `docs/workbuddy-integration.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `docs/workbuddy-open-platform-questions.md` | REVIEWED | Public technical documentation; historical claims retained as historical |
| `docs/workbuddy-real-setup.md` | REVIEWED | Public technical document; local absolute paths replaced by placeholders |
| `examples/three_agent_demo.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `pyproject.toml` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `scripts/Test-DshPlan.ps1` | REVIEWED | Removed private installation fallback; explicit DshBin/environment remains supported |
| `scripts/audit_release.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `scripts/build_desktop.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `scripts/check_workbuddy_config.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `scripts/desktop_kernel.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `scripts/dsh_plan_probe.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `scripts/dsh_review_probe.py` | REVIEWED | Removed machine-specific launcher; adapter uses explicit environment or official SDK default |
| `scripts/dual_real_validation.py` | REVIEWED | Removed machine-specific launcher; adapter uses explicit environment or official SDK default |
| `scripts/team_console.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `scripts/verify_desktop_backend.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `scripts/workbuddy_auth.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `scripts/workbuddy_smoke_test.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/agents/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/agents/agent.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/agents/registry.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/agents/role.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/cli.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/config.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/console/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/console/desktop.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/console/server.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/console/service.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/kernel/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/kernel/event_bus.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/kernel/message_bus.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/kernel/task_manager.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/kernel/team_kernel.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/memory/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/memory/blackboard.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/memory/database.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/orchestration/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/orchestration/demo_files.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/orchestration/dual_real.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/orchestration/workflow.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/protocol/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/protocol/artifact.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/protocol/event.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/protocol/message.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/protocol/task.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/base.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/codex/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/codex/adapter.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/codex/app_server.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/demo_engineer.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/diagnostics.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/dsh/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/dsh/adapter.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/dsh/auth.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/dsh/mock_adapter.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/dsh/probe.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/dsh/review_probe.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/dsh/runtime.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/mock.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/workbuddy/__init__.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/workbuddy/adapter.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/workbuddy/auth.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/workbuddy/client.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/workbuddy/config.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/workbuddy/mock_adapter.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/workbuddy/probe.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `src/ai_team/providers/workbuddy/store.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/conftest.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/e2e/test_workflow.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/integration/test_codex_protocol.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_console.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_core.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_desktop.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_dsh_adapter.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_dsh_auth.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_dsh_probe.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_dsh_review_probe.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_dual_real.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_provider_diagnostics.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_review_evidence.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_workbuddy_api.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `tests/unit/test_workbuddy_preparation.py` | REVIEWED | Source/configuration/offline test reviewed; no private data |
| `PUBLIC_RELEASE_MANIFEST.md` | REVIEWED | This publication inventory; no local machine identifiers |

## Excluded by design (not copied)

Original `.git/`; `.env` and private configuration; SQLite/WAL/SHM; `runs/`;
`.local/`; logs; virtual environments; node_modules; dist/build/target; generated
icons and caches; local authentication stores; client installations; model weights.
No recursive whole-project copy was used.

## Validation of this publication snapshot

- Backend unit/integration: **157 passed, 1 skipped**.
- Frontend: **6 passed**; React production build passed.
- Total: **163 passed, 0 failed, 1 skipped** (light-test repeats not counted).
- The skipped test is the optional DSH SDK parameter-contract test: the private
  SDK directory was deliberately not copied, and optional SDK is not installed
  in this clean snapshot. No model was called. Native synthetic DPAPI passed.
- Original history scan checked 76 reachable blobs and found no recognized
  credential signature. None of those original Git objects are imported.

## Release-only changes

- Version metadata/display updated to 0.2.2.
- Local paths in documentation replaced with generic placeholders.
- Live DSH helper scripts no longer assume a private installation location.
  No live helper was executed.
- Original commit authors/emails/history are not imported. New commits use the
  authenticated owner's GitHub noreply identity.
