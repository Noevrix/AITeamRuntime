"""Explicit packaging allowlist. Never bundle project root, runs or credentials."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def write_icon(path):
    """Generate a neutral original geometric icon, without vendor artwork."""
    width = 32
    pixels = bytearray()
    for y in reversed(range(width)):
        for x in range(width):
            mark = (8 <= x <= 11 and 8 <= y <= 24 or
                    20 <= x <= 23 and 8 <= y <= 24 or
                    8 <= x <= 23 and (8 <= y <= 11 or 16 <= y <= 19))
            r, g, b = (18, 23, 31) if mark else (184, 220, 137)
            pixels.extend((b, g, r, 255))
    dib = struct.pack("<IIIHHIIIIII", 40, width, width * 2, 1, 32, 0, len(pixels), 0, 0, 0, 0)
    payload = dib + pixels + bytes(width * 4)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<HHH", 0, 1, 1) +
                     struct.pack("<BBBBHHII", width, width, 0, 0, 1, 32, len(payload), 22) + payload)


def build_command(root=ROOT):
    return [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir",
            "--name", "ai-team-kernel", "--paths", str(root / "src"),
            "--distpath", str(root / "build/desktop-kernel"),
            "--workpath", str(root / "build/pyinstaller"),
            "--specpath", str(root / "build"),
            "--add-data", str(root / "console/dist") + os.pathsep + "console/dist",
            "--add-data", str(root / "LICENSE") + os.pathsep + ".",
            "--add-data", str(root / "build/notices") + os.pathsep + "notices",
            str(root / "scripts/desktop_kernel.py")]


def notices():
    """Include installed dependency license files; no environment/config values."""
    target = ROOT / "build/notices"
    target.mkdir(parents=True, exist_ok=True)
    inventory = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name", "unknown")
        inventory.append({"name": name, "version": dist.version,
                          "license": dist.metadata.get("License-Expression") or dist.metadata.get("License", "UNKNOWN")})
        for file in dist.files or []:
            if (".dist-info/" in str(file).replace("\\", "/") and
                    any(part.lower().startswith(("license", "copying", "notice"))
                        for part in file.parts)):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    dest = target / name / Path(file).name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(source.read_bytes())
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        (target / "PYTHON-LICENSE.txt").write_bytes(python_license.read_bytes())
    (target / "python-dependencies.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    lock = json.loads((ROOT / "console/package-lock.json").read_text(encoding="utf-8"))
    entries = [{"package": key, "version": value.get("version"), "license": value.get("license", "UNKNOWN")}
               for key, value in lock["packages"].items()]
    (target / "node-dependencies.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
    for package in ("react", "react-dom", "scheduler"):
        source = ROOT / "console/node_modules" / package / "LICENSE"
        if not source.is_file():
            raise RuntimeError("FRONTEND_LICENSE_MISSING")
        (target / (package + "-LICENSE.txt")).write_bytes(source.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if not (ROOT / "console/dist/index.html").is_file():
        parser.error("Run npm run build in console first")
    write_icon(ROOT / "console/src-tauri/icons/icon.ico")
    if args.prepare_only:
        print("Packaging paths and generated icon prepared; no EXE built.")
        return
    notices()
    subprocess.run(build_command(), cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
