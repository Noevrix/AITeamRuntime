# AI Team Runtime — V0.2.2

Local multi-agent collaboration runtime with a React team console and Windows
Tauri desktop build pipeline. The console runs locally; desktop lifecycle code is
prepared, but **the Windows shell and installer have not yet been built or
launch-verified on this machine**.

## Current scope

The goal is traceable Agent collaboration through tasks, messages and a shared
Blackboard. React/Tauri connects to a loopback API, which reuses TaskManager,
EventBus, SQLite and the existing Provider architecture.

| Provider | Actual state |
| --- | --- |
| DSH | Historical real planning and independent review verified |
| Codex | Historical real implementation, tests and revision verified |
| WorkBuddy | PARTIAL / AUTH_REQUIRED; API/OAuth code exists, real Smoke Test NOT_RUN |

DSH + Codex passed staged verification after the first review failed from an
output limit. The first continuous E2E did not pass. Three-agent real E2E has
not run. Historical success does not imply current online status.

## Console features

- Team Overview: task counts, recent runs and evidence-backed Agent status.
- Task Board: filters, details, related records and explicit draft creation.
- Agent Management: capabilities, configuration, historical validation and failures.
- Workflow Timeline: persisted events only, with missing fields left unknown.
- Blackboard Explorer: projects, tasks, messages, decisions and artifact hashes.
- Settings & Diagnostics: non-sensitive presence checks and allowlisted reports.

Opening, refreshing or closing the UI never starts, resubmits or cancels model
tasks. Drafts do not execute. There is no workflow execution or OAuth UI endpoint.

## Windows development

Use Python 3.11+ (CI 3.13), Node 24 and Git. From the checkout root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
Set-Location console
npm.cmd ci --ignore-scripts
npm.cmd run build
Set-Location ..
python scripts/team_console.py --port 8765
```

Open <http://127.0.0.1:8765>; this is local only, not a public service.
For frontend editing, run `npm.cmd run dev` in `console` in another terminal and
refresh after rebuild. No real provider credentials are needed.

## Desktop build

Rust stable/MSVC, Visual Studio C++ Build Tools and WebView2 are required; follow
the [official prerequisites](https://v2.tauri.app/start/prerequisites/).
No system toolchain is installed by the application.

```powershell
# Root, project virtual environment activated; frontend already built:
python -m pip install pyinstaller==6.22.3
python scripts/build_desktop.py
python scripts/verify_desktop_backend.py build/desktop-kernel/ai-team-kernel/ai-team-kernel.exe
Set-Location console
npm.cmd run desktop:build
```

Expected paths after success are
`console/src-tauri/target/release/ai-team-console.exe` and
`console/src-tauri/target/release/bundle/nsis/*-setup.exe`.
They do not currently exist. Use the installer: the shell EXE alone lacks its
`kernel/` resources. Installers are unsigned. No formal Release is automated.

The shell owns a packaged Python backend on an ephemeral loopback port, waits
for readiness, then opens the production React UI. Repeated launch focuses the
existing window. Exit closes only the owned service. No database deletion,
workflow cancellation or automatic model retries occur. See
[desktop details](docs/windows-desktop.md).

Windows Actions is configured to test, build and upload artifacts, but has
**not run**. The intended public repository is Noevrix/AITeamRuntime; CI success must be verified separately.

## Offline tests

```powershell
python -m pytest tests/unit tests/integration -q -p no:cacheprovider
Set-Location console
npm.cmd run test
npm.cmd run build
```

Native Windows DPAPI tests use synthetic in-memory data. Unsupported or unrun
cases must not be counted as passed. These commands exclude E2E and live probes.

## Configuration, storage and backup

`.env.example` documents configuration; `.env` is not automatically loaded.
Provider setup is separate from UI startup. Desktop login is not WorkBuddy OAuth.
The console never extracts client credentials or requires a new DSH API key.

Browser development reads the checkout's `runs/*/blackboard.sqlite`. Desktop
defaults to `%LOCALAPPDATA%\AI Team Runtime\runs`; a fresh installation has no
private history and therefore no evidence-backed REAL_VERIFIED badges.
Set process-local `AI_TEAM_DATA_ROOT` to an absolute existing checkout path before
starting the EXE to view that history. Avoid concurrent writers on the same data.

No schema migration is introduced. Stop writers before backing up the entire run
directory, including artifacts and remaining SQLite WAL/SHM files, or use SQLite's
backup API. Do not copy only a live WAL-mode database file. Closing/uninstalling
does not remove user data.

## Safety and limits

Loopback API validates Host, Origin, session and CSRF. No arbitrary command/file
endpoint is exposed. Sensitive fields and recognizable secret patterns are
filtered, but arbitrary unlabeled secrets cannot be reliably detected: never put
credentials in task text. This is not multi-user network software.

History is limited to 1000 rows per table and 32000 characters per long value.
No realtime push or workflow scheduler is provided. Desktop build/launch remains
unverified here; resolved Rust dependencies need review after the first build.
WorkBuddy still needs official protocol confirmation and user OAuth setup.

## License

[Apache-2.0](LICENSE) remains unchanged. React runtime dependencies use MIT;
Tauri uses MIT/Apache-2.0. Python and other dependencies retain their licenses.
Packaging gathers license texts and dependency metadata; see
[third-party notices](THIRD_PARTY_NOTICES.md). No vendor binaries, models or
private run data are redistributed.

## Archived V0.1 / V0.1.1 notes

The following records earlier behavior and counts, not current instructions or
current Provider status. The V0.1 release was a Python proof of concept without UI.

Independent open-source project, not affiliated with, sponsored by, or endorsed by OpenAI, DeepSeek, or WorkBuddy. No vendor clients or models are redistributed. Users install and authorize their own providers.

```powershell
python -m pip install -e ".[test]"
ai-team demo --mode mock
ai-team doctor
ai-team demo --mode auto
python -m pytest -q
```
Mock mode is deterministic and makes no model calls. Auto mode probes Codex and visibly falls back to mock only if connection fails; a failed real turn fails the run. Real mode requires Codex and never substitutes a mock. DSH and WorkBuddy are explicitly mocked in V0.1.
Runtime outputs and SQLite are stored in `runs/`, excluded from Git. Use a fresh workspace per demo. See docs and the acceptance report for verified scope.

Verified on Windows with Python 3.14.6 and Codex CLI 0.153.4: 20 runtime tests; mixed-provider E2E with real Codex implementation/revision and DSH/WorkBuddy mocks. Both TODO test rounds passed 11 cases. Real Codex requires a normal terminal with access to its official CLI home/login environment. A restricted nested sandbox may fail initialization.

## V0.1.1 DSH integration

35 tests pass, including all original 20 tests. Official DSH SDK/CLI transport and
health checks are verified; the live planning probe failed because the isolated
runtime has no authorized API key. **DSH model inference is not verified.** No
new complete live E2E was run. WorkBuddy remains unchanged and mocked.

DSH real mode is opt-in, preserving the existing Codex REAL + DSH MOCK command:

```powershell
python -m pip install -e ".[test,dsh]"
# Explicit dedicated home; never discover/copy desktop credentials.
$env:DSH_HOME = Join-Path (Get-Location) "runs/dsh-home"
# Optional: absolute path to an official dsh CLI; omitted uses SDK bundled runtime.
# $env:AI_TEAM_DSH_BIN = "<official-dsh-path>"
# Configure DEEPSEEK_API_KEY in the launching environment through your normal secret setup.
ai-team demo --mode real --dsh-mode real
```

Without authorized DSH inference, continue using `ai-team demo --mode real`
(DSH Mock), or `--mode mock` (no inference at all). Explicit real DSH failures are
reported, never silently replaced. `.env` is not automatically loaded.

Final review receives bounded actual source files, test logs, test events and
Blackboard artifact hashes through a persisted task, rather than only status text.
See [V0.1.1 acceptance report](V0_1_1_ACCEPTANCE_REPORT.md) for evidence and limits.
