# Windows desktop — 0.2.1

The application is named **AI Team Runtime**. The existing React UI is reused.
Desktop build and launch have not been verified on the current machine.

## Build prerequisites

Install only if you choose to build locally:

1. Use the official [Rust installer](https://www.rust-lang.org/tools/install)
   and stable `x86_64-pc-windows-msvc` toolchain.
2. Follow [Tauri Windows prerequisites](https://v2.tauri.app/start/prerequisites/)
   for Visual Studio C++ Build Tools and WebView2. Open a new terminal and verify
   `rustc --version` and `cargo --version`.
3. Use an isolated Python 3.13 virtual environment for reproducible packaging,
   install `.[test]` and `pyinstaller==6.22.3`; install locked frontend dependencies
   using Node 24 and `npm ci --ignore-scripts`.
4. Run the build commands in README. Run `npm run desktop` only after building
   the frontend and packaged backend; no separate browser server is required.

The application never installs these system tools itself.

## Lifecycle and paths

- `scripts/build_desktop.py` explicitly includes production frontend, license
  and generated third-party notices. It does not glob the checkout or runs.
- PyInstaller onedir output is bundled using Tauri's documented resource map.
  `kernel/ai-team-kernel.exe` owns the HTTP service; end users need no Python.
- The child binds `127.0.0.1:0`, reports the allocated port through a private
  stdout pipe and keeps its parent stdin pipe open. No existing port is reused
  and no unrelated process is killed. Readiness timeout is 30 seconds.
- Tauri loads the production UI from this service, preserving same-origin
  Cookie/CSRF protections. No frontend shell/filesystem commands are registered.
- Single-instance plugin focuses the first window. Window reload only rereads
  API data. Parent exit closes the child pipe; after a bounded graceful wait,
  only that owned child is terminated.
- Startup failure shows a static message. Backend failure after startup becomes
  a UI request error; it is not automatically restarted. There is no model task
  started by this desktop backend, so stopping it cannot cancel an Agent run.
- Default data directory is `%LOCALAPPDATA%\AI Team Runtime`, not Program Files
  or the packaged resource directory. User data is not an installer resource.
- `AI_TEAM_DATA_ROOT` is an optional absolute path supplied by the user in the
  launching process environment. It is not persisted or set system-wide.
- An existing checkout can be selected to inspect historical databases.
  Close other writers first. No migration, history copy or database cleanup occurs.

## CI and artifacts

`.github/workflows/windows-build.yml` uses `windows-2022`, Node 24, Python 3.13
and stable Rust. The runner image supplies MSVC/Windows SDK; Tauri manages its
NSIS build dependency. No provider SDK or real credentials are needed for tests.
All critical steps fail the job. Native DPAPI is included.

The job tests the packaged backend's two launches, loopback API and clean exit
against a temporary empty data directory. This is **not** a GUI/installer launch
test. It then builds the Tauri EXE and unsigned per-user NSIS installer and uploads
them as artifacts, together with resolved dependency records.

There is currently no generated Cargo.lock. The first successful CI must retain
its resolved lockfile for review and a later explicit source commit; current Rust
dependency ranges mean builds are not yet fully locked/reproducible.
Artifact creation is not a formal GitHub Release.

After CI succeeds, manually install into a test Windows user, verify UI/history,
refresh/relaunch, close/reopen, backend failure behavior and data retention.
Confirm the archive excludes private records, and audit transitive notices before
distributing. The standalone shell EXE is not a portable single-file application.

## Icon and notices

A small original geometric placeholder icon is generated deterministically by
the packaging script. No vendor artwork or existing brand files are overwritten.
The icon is provisional. Python and React license files are bundled. Rust resolved
metadata is retained by CI; binary redistribution review remains a release gate.

## Official references

- [Tauri bundled resources](https://v2.tauri.app/develop/resources/)
- [Single-instance plugin](https://v2.tauri.app/plugin/single-instance/)
- [Windows installer](https://v2.tauri.app/distribute/windows-installer/)
- [PyInstaller spec/data files](https://pyinstaller.org/en/stable/spec-files.html)
- [Windows runner image software](https://github.com/actions/runner-images/blob/main/images/windows/Windows2022-Readme.md)
