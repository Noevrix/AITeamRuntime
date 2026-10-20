"""Read-only source/history scan; emit paths/categories only, never matched values.

This is a preparation check, not a guarantee that every possible secret is found.
The private inventory is written under ignored .local/, never a release artifact.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "credential_signature": re.compile(rb"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|eyJ[\w-]+\.[\w-]+\.[\w-]+)\b"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "personal_windows_path": re.compile(rb"(?i)[A-Z]:[\\/]+Users[\\/]+(?!Public\b|Default\b)[A-Za-z0-9_.-]+"),
    "absolute_windows_path": re.compile(rb"(?i)(?<![A-Za-z0-9])[A-Z]:[\\/](?![\\/])[^\r\n\"<>]{2,}"),
    "credential_literal_review": re.compile(rb"""(?i)(?:api_key|access_token|refresh_token|client_secret|password)\s*[:=]\s*["'][^"' \r\n]{8,}["']"""),
}


def git(*args):
    return subprocess.check_output(["git", "-c", "safe.directory=" + ROOT.as_posix(), *args], cwd=ROOT)


def risks(path, data):
    found = [name for name, pattern in PATTERNS.items() if pattern.search(data)]
    p = Path(path)
    if (p.name == ".env" or (p.name.startswith(".env.") and p.name != ".env.example") or
            any(part in {"runs", "node_modules", ".venv", "__pycache__", "target"} for part in p.parts) or
            p.suffix.lower() in {".sqlite", ".db", ".log", ".wal", ".shm"}):
        found.append("private_or_generated_file")
    if len(data) > 5_000_000:
        found.append("large_file")
    return found


def main():
    files = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
    inventory, current = [], []
    for path in filter(None, files):
        file = ROOT / path
        if not file.is_file():
            continue
        data = file.read_bytes()
        inventory.append({"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        found = risks(path, data)
        if found:
            current.append({"path": path, "categories": found})
    history, blobs = [], 0
    for item in git("rev-list", "--objects", "--all").decode().splitlines():
        oid, _, path = item.partition(" ")
        if git("cat-file", "-t", oid).strip() != b"blob":
            continue
        blobs += 1
        found = risks(path, git("cat-file", "blob", oid))
        if found:
            history.append({"object": oid, "path": path, "categories": found})
    output = ROOT / ".local/v021-audit"
    output.mkdir(parents=True, exist_ok=True)
    (output / "release-scan.json").write_text(json.dumps({
        "inventory": inventory, "working_tree_risks": current,
        "reachable_history_blob_count": blobs, "history_risks": history,
        "limitation": "Heuristic scan; literal matches require review; no secret values emitted."
    }, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(inventory), "history_blobs": blobs,
                      "working_tree_risk_files": len(current), "history_risk_blobs": len(history),
                      "status": "REVIEW_REQUIRED" if current or history else "NO_PATTERN_MATCHES"}))


if __name__ == "__main__":
    main()
