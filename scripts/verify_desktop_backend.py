"""Offline packaged-backend smoke: temp data only; never calls a provider."""
import argparse
import http.cookiejar
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import urllib.request


def verify(executable):
    with tempfile.TemporaryDirectory(prefix="ai-team-desktop-smoke-") as directory:
        env = dict(os.environ, AI_TEAM_DATA_ROOT=directory)
        command = [str(Path(executable).resolve())]
        for _ in range(2):
            child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, env=env, text=True)
            try:
                ready = queue.Queue()
                threading.Thread(target=lambda: ready.put(child.stdout.readline()), daemon=True).start()
                message = json.loads(ready.get(timeout=30))
                assert message["protocol"] == 1
                url = f"http://127.0.0.1:{message['port']}"
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}),
                    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                with opener.open(url + "/", timeout=5) as response:
                    assert response.status == 200 and b'root' in response.read()
                with opener.open(url + "/api/overview", timeout=5) as response:
                    data = json.load(response)
                    assert data["runs"] == []
                assert not (Path(directory) / "runs").exists()
                child.stdin.close()
                assert child.wait(timeout=10) == 0
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)
        print("PACKAGED_BACKEND_SMOKE_PASS: two launches, no task/data creation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("executable")
    verify(parser.parse_args().executable)
