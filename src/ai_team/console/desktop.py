"""Packaged local backend. No provider activation, shell or OAuth."""
import json
import os
import sys
import threading
from pathlib import Path
from .server import make_server


def data_root(environ=None):
    env = os.environ if environ is None else environ
    explicit = env.get("AI_TEAM_DATA_ROOT")
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            raise ValueError("DATA_ROOT_MUST_BE_ABSOLUTE")
        return path.resolve()
    local = env.get("LOCALAPPDATA")
    if not local or not Path(local).is_absolute():
        raise ValueError("LOCALAPPDATA_REQUIRED")
    return Path(local).resolve() / "AI Team Runtime"


def serve(root, web_root, parent_input, output):
    if not (Path(web_root) / "index.html").is_file():
        raise ValueError("FRONTEND_MISSING")
    server = make_server(root, 0, web_root=web_root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        output.write(json.dumps({"port": server.server_port, "protocol": 1}) + "\n")
        output.flush()
        # EOF on the parent's private pipe stops this service, never tasks/data.
        parent_input.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main():
    try:
        resources = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
        serve(data_root(), resources / "console" / "dist", sys.stdin.buffer, sys.stdout)
    except Exception:
        print('{"error":"BACKEND_START_FAILED"}', flush=True)
        return 1
    return 0
