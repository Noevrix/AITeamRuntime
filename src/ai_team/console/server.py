import argparse
import json
import mimetypes
import secrets
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .service import ConsoleService, ConsoleError


def make_server(root, port=8765, web_root=None, enable_models=False):
    from .collaboration import Collaboration
    collaboration = Collaboration(root, enabled=enable_models)
    service = ConsoleService(root)
    service.execution_enabled = enable_models
    web_root = Path(web_root).resolve() if web_root else Path(root).resolve() / "console" / "dist"
    session = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log URLs, bodies, cookies or exception text.

        def reply(self, status, data, content_type="application/json", bootstrap=False):
            payload = json.dumps(data, ensure_ascii=False).encode() if content_type == "application/json" else data
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self'; style-src 'self'; "
                             "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
                             "base-uri 'none'; form-action 'self'")
            if bootstrap:
                self.send_header("Set-Cookie", f"team_console={session}; HttpOnly; SameSite=Strict; Path=/")
            self.end_headers()
            self.wfile.write(payload)

        def validate(self, api=False, write=False):
            host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != host:
                raise ConsoleError("INVALID_HOST", 403)
            origin = self.headers.get("Origin")
            if origin is not None and origin != "http://" + host:
                raise ConsoleError("INVALID_ORIGIN", 403)
            if self.headers.get("Sec-Fetch-Site") not in {None, "same-origin", "none"}:
                raise ConsoleError("CROSS_SITE_DENIED", 403)
            if api:
                cookie = SimpleCookie()
                try:
                    cookie.load(self.headers.get("Cookie", ""))
                    value = cookie.get("team_console")
                except Exception:
                    value = None
                if value is None or not secrets.compare_digest(value.value, session):
                    raise ConsoleError("SESSION_REQUIRED", 401)
            if write:
                if (origin != "http://" + host or
                    not secrets.compare_digest(self.headers.get("X-Console-CSRF", ""), csrf)):
                    raise ConsoleError("CSRF_DENIED", 403)

        def do_GET(self):
            try:
                url = urlsplit(self.path)
                parts = url.path.strip("/").split("/")
                api = parts[0] == "api"
                self.validate(api=api)
                if url.query:
                    raise ConsoleError("QUERY_NOT_SUPPORTED")
                if api:
                    if parts == ["api", "session"]:
                        result = {"csrf": csrf, "execution_enabled": enable_models}
                    elif parts == ["api", "conversations"]:
                        result = collaboration.list()
                    elif len(parts) == 3 and parts[1] == "conversations":
                        result = collaboration.read(parts[2])
                    elif parts == ["api", "overview"]:
                        result = service.overview()
                    elif parts == ["api", "agents"]:
                        result = service.agents()
                    elif parts == ["api", "diagnostics"]:
                        result = service.diagnostics()
                    elif len(parts) == 3 and parts[1] == "runs":
                        result = service.snapshot(parts[2])
                    elif len(parts) == 5 and parts[1] == "runs" and parts[3] == "tasks":
                        result = service.task_detail(parts[2], parts[4])
                    elif len(parts) == 6 and parts[1] == "runs" and parts[3] == "artifacts" and parts[5] == "hash":
                        result = service.artifact_hash(parts[2], parts[4])
                    elif len(parts) == 3 and parts[1] == "reports":
                        result = service.report(parts[2])
                    else:
                        raise ConsoleError("NOT_FOUND", 404)
                    self.reply(200, result)
                else:
                    relative = "index.html" if url.path == "/" else url.path.lstrip("/")
                    if relative != "index.html" and not relative.startswith("assets/"):
                        raise ConsoleError("NOT_FOUND", 404)
                    target = web_root / relative
                    if (not target.resolve().is_relative_to(web_root.resolve()) or target.is_symlink() or
                        ".." in Path(relative).parts or not target.is_file()):
                        raise ConsoleError("NOT_FOUND", 404)
                    self.reply(200, target.read_bytes(), mimetypes.guess_type(str(target))[0] or
                               "application/octet-stream", bootstrap=relative == "index.html")
            except ConsoleError as exc:
                self.reply(exc.status, {"error": exc.code})
            except Exception:
                self.reply(500, {"error": "INTERNAL_ERROR"})

        def do_POST(self):
            try:
                if self.headers.get("Transfer-Encoding"):
                    raise ConsoleError("INVALID_BODY")
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    raise ConsoleError("INVALID_BODY") from None
                if not 0 < length <= 40_000:
                    raise ConsoleError("INVALID_BODY", 413)
                self.connection.settimeout(5)
                raw = self.rfile.read(length)
                # Drain only a bounded body before rejection so Windows does not
                # reset the socket with unread bytes instead of delivering 403/404.
                self.validate(api=True, write=True)
                if self.headers.get("Content-Type") != "application/json":
                    raise ConsoleError("JSON_REQUIRED", 415)
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise ConsoleError("INVALID_BODY")
                parts = self.path.strip("/").split("/")
                if self.path == "/api/drafts":
                    result = service.create_draft(body)
                elif self.path == "/api/conversations":
                    result = collaboration.create(body)
                elif len(parts) == 4 and parts[:2] == ["api", "conversations"]:
                    key, action = parts[2:]
                    if action == "comment":
                        result = collaboration.comment(key, body)
                    elif action == "cancel":
                        result = collaboration.cancel(key)
                    elif action in {"discuss", "execute"}:
                        result = collaboration.start(key, action, body)
                    elif action == "plan":
                        result = collaboration.edit_plan(key, body)
                    else:
                        raise ConsoleError("NOT_FOUND", 404)
                else:
                    raise ConsoleError("NOT_FOUND", 404)
                self.reply(201, result)
            except ConsoleError as exc:
                self.reply(exc.status, {"error": exc.code})
            except (ValueError, UnicodeError):
                self.reply(400, {"error": "INVALID_JSON"})
            except Exception:
                self.reply(500, {"error": "INTERNAL_ERROR"})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.collaboration = collaboration
    return server


def main():
    parser = argparse.ArgumentParser(description="Local Console; models disabled unless explicitly enabled.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--enable-models", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if not (root / "console/dist/index.html").is_file():
        parser.error("Build frontend first: cd console; npm ci; npm run build")
    server = make_server(root, args.port, enable_models=args.enable_models)
    print(f"AI Team Console: http://127.0.0.1:{server.server_port}  [models enabled: {args.enable_models}]", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.collaboration.close()
        server.server_close()


if __name__ == "__main__":
    main()
