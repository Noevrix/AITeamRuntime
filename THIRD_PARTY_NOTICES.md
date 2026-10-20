# Third-party dependencies

AI Team Runtime source remains Apache-2.0. This document does not replace the
license text shipped with each dependency or assert ownership of vendor software.

| Component | License / use |
| --- | --- |
| React, React DOM, scheduler | MIT; frontend runtime |
| Vite, Vitest, jsdom | MIT; development/test tools |
| Tauri and its single-instance plugin | MIT OR Apache-2.0; desktop shell |
| CPython | Python Software Foundation license and bundled third-party notices |
| Pydantic, Rich, Typer and their dependencies | Individual installed license texts collected during packaging |
| PyInstaller | GPL with bootloader exception; packaging tool |
| DSH SDK | Optional provider dependency; not required by console build; license must be checked before redistributing optional SDK/runtime |

The build helper collects installed Python distribution license files and
metadata, CPython LICENSE.txt and React runtime license files into `build/notices`.
Use a clean virtual environment; collecting notices from a global Python
environment can include unrelated installed-package names.
The resulting backend bundle includes these notices.

Node versions are locked in package-lock.json. Rust metadata and generated
Cargo.lock are retained as CI artifacts, but have not yet been generated here.
Transitive Rust notices and the final packaged dependency set need review before
a public binary release. Source license is confirmed; final binary compliance
is not yet certified.

No OpenAI, DeepSeek or WorkBuddy client, authentication data or model weights are
included. The application is independent of those vendors.

References: [Tauri license](https://github.com/tauri-apps/tauri/blob/dev/LICENSE_MIT),
[PyInstaller license exception](https://pyinstaller.org/en/stable/license.html),
[React license](https://github.com/facebook/react/blob/main/LICENSE).
