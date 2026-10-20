import io
import json
import threading
import http.client
from pathlib import Path
import pytest
from ai_team.console.desktop import data_root, serve


def test_user_data_root_is_explicit_and_separate(tmp_path):
    assert data_root({"LOCALAPPDATA": str(tmp_path)}) == tmp_path / "AI Team Runtime"
    assert data_root({"AI_TEAM_DATA_ROOT": str(tmp_path)}) == tmp_path
    with pytest.raises(ValueError):
        data_root({"AI_TEAM_DATA_ROOT": "../private"})
    with pytest.raises(ValueError):
        data_root({})


def test_desktop_lifecycle_and_existing_data_preserved(tmp_path):
    web = tmp_path / "assets"
    web.mkdir()
    (web / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    root = tmp_path / "data"
    root.mkdir()
    sentinel = root / "existing.sqlite"
    sentinel.write_bytes(b"existing user data")
    for _ in range(2):
        stop, ready = threading.Event(), threading.Event()
        class Pipe:
            def read(self):
                assert stop.wait(5)
        class Output(io.StringIO):
            def flush(self):
                ready.set()
        output = Output()
        worker = threading.Thread(target=serve, args=(root, web, Pipe(), output))
        worker.start()
        try:
            assert ready.wait(5)
            port = json.loads(output.getvalue())["port"]
            client = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            client.request("GET", "/")
            response = client.getresponse()
            cookie = response.getheader("Set-Cookie").split(";")[0]
            assert response.status == 200
            response.read()
            client.request("GET", "/api/overview", headers={"Cookie": cookie})
            response = client.getresponse()
            assert response.status == 200 and json.loads(response.read())["runs"] == []
            client.close()
            assert not (root / "runs").exists()
        finally:
            stop.set()
            worker.join(timeout=5)
        assert not worker.is_alive()
        assert sentinel.read_bytes() == b"existing user data"


def test_missing_frontend_cannot_start(tmp_path):
    with pytest.raises(ValueError, match="FRONTEND_MISSING"):
        serve(tmp_path, tmp_path, io.BytesIO(), io.StringIO())
    assert list(tmp_path.iterdir()) == []


def test_packaging_uses_explicit_data_allowlist():
    import runpy
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/build_desktop.py"))
    command = module["build_command"]()
    data = [command[i+1] for i, arg in enumerate(command) if arg == "--add-data"]
    assert len(data) == 3
    assert all("runs" not in path and ".env" not in path and "sqlite" not in path for path in data)
    assert "console" in data[0] and "dist" in data[0]
