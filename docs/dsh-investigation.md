# DSH investigation — 2026-10-19

Read-only checks of the user-specified DSH installation found:

- DeepSeek Harness.exe (Electron); multiple running processes.
- resources/app.asar and app.asar.unpacked/dsh/node_modules.
- resources/runtime/cli/bin/dsh.cmd; official launcher --help executed successfully.
- CLI advertises profiles, web, headless and tui modes.
- runtime metadata: desktop 0.2.1-rc.2, Node 24.21.0, bundled Python 3.12.14, pnpm 11.28.5.
- Loopback listener 127.0.0.1:65000 belongs to DSH. No requests were sent to undocumented endpoints.
- No deepseek_harness Python module in the development interpreter. No separately confirmed SDK profile/auth configuration was available.

[Official Python SDK](https://github.com/deepseek-ai/deepseek-harness/blob/master/python/sdk/README.md) documents a separately installed SDK/runtime, explicit Harness home, and stdio sessions. Its documented SDK is a valid future integration route; the presence of the desktop CLI alone does not verify SDK availability or authorize desktop credential extraction.

V0.1: DSHMockAdapter active; DSHAdapter returns NOT_CONFIGURED. This is a deliberate downgrade, not a claim that DSH lacks APIs. Next: install the official SDK in a project environment, configure a separate home and authorized provider credentials, verify one bounded structured turn, then implement the adapter. Nothing was modified in the DSH installation or private user data.

## V0.1.1: verified SDK transport, model authorization blocked

Repeated bounded read-only installation checks confirmed CLI/desktop 0.2.1-rc.2,
the same bundled runtime metadata, running desktop processes and loopback 65000.
No desktop HTTP endpoint was called. The installed official dsh.cmd is documented
in the [desktop reference](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/desktop/README.md).

Installed official `deepseek-harness-sdk==0.2.1rc2` with `--no-deps` into the
ignored project `runs/dsh-sdk` directory. It uses the already installed, matching
desktop CLI via the SDK's public `dsh_bin` option, so no additional runtime wheel,
global Python change, desktop profile change or installation-directory write was
needed. The SDK dependency is optional in pyproject.toml. Normal installation of
that extra also installs the SDK's matching runtime dependency.

The public SDK uses `dsh --profile sdk` and newline-delimited JSON-RPC. It requires
an explicit home. The probe used a NEW isolated home under `runs`, never the
desktop's private home. Inspection of the installed SDK source confirmed public
start, start_session, resume_session, Session.run, working-directory and close APIs.

Actual results:

- SDK initialization and working-directory RPC: PASS.
- One bounded planning submission: returned `finish_reason=error`, empty response.
- Its newly generated probe session log reports no API key for provider route
  `deepseek-official`, requiring DEEPSEEK_API_KEY via the official credential
  service or launching environment. No desktop credentials were inspected.
- New DSHAdapter transport smoke: connect, health_check, session handle and status
  PASS; no further inference requested. This is transport readiness, not a model
  entitlement check or a successful plan.
- Real DSH model response: UNAVAILABLE. Effective default remains MOCK.

Local evidence (excluded from Git): `runs/dsh-probe-v011/probe.json` and
`adapter-transport.json`. The isolated session log was inspected only for the
failure of this newly submitted probe; private existing session history was not read.

DSHAdapter now checks finish reason, session identity, JSON Result, nonempty
content, mock flag and stage-specific decision types. Timeout/cancellation closes
the owned SDK runtime to unblock its worker thread. Persistent sessions are
supported by the SDK; real resume/cancel behavior has not been independently
qualified. Per-session cancellation and streaming are not advertised. SDK tooling
capabilities remain present; the architect's no-tools instruction is a prompt rule,
not an OS sandbox or an enforced provider permission policy.

No live complete E2E was attempted after this authorization failure. Supply an
authorized key through the normal launching environment or configure the dedicated
home using official DSH setup; do not send secrets in chat, commit them, or extract
desktop tokens. Then run one planning probe before opting into the real workflow.
The ordinary `--mode real` workflow retains DSH Mock unless `--dsh-mode real` is
explicitly selected. Failure in explicit real mode is never disguised as Mock success.
