import hashlib
import json
import re
import shutil
import sqlite3
import threading
from pathlib import Path

from ai_team.memory.database import Database
from ai_team.kernel.task_manager import TaskManager
from ai_team.kernel.event_bus import EventBus
from ai_team.agents.agent import Team, Project
from ai_team.protocol.task import Task
from ai_team.providers.workbuddy.config import configuration_status

TABLES = ("projects", "tasks", "messages", "events", "artifacts", "decisions", "agents", "providers")
REPORTS = (
    "V0_1_3_FINAL_ACCEPTANCE_REPORT.md", "V0_1_5_1_ACCEPTANCE_REPORT.md",
    "V0_2_0_ACCEPTANCE_REPORT.md", "docs/dsh-desktop-reuse.md",
    "docs/workbuddy-real-setup.md", "docs/workbuddy-open-platform-questions.md",
)
ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
SECRET_KEY = re.compile(r"(password|passwd|secret|token|cookie|authorization|apikey|credential)", re.I)


class ConsoleError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status
        super().__init__(code)


def clean(value, depth=0):
    """Conservative presentation filter; never return database objects unchanged."""
    if depth > 16:
        return "[内容层级过深]"
    if isinstance(value, dict):
        return {str(k): "[已隐藏]" if SECRET_KEY.search(re.sub(r"[^a-z]", "", str(k).lower()))
                and str(k) not in {"output_tokens", "max_tokens"}
                and not (str(k) == "authorization" and isinstance(v, str) and v in {"UNKNOWN", "AUTH_REQUIRED", "CONFIGURED", "UNAVAILABLE"})
                and not (str(k).endswith("_present") and type(v) is bool)
                else clean(v, depth + 1)
                for k, v in list(value.items())[:200]}
    if isinstance(value, list):
        return [clean(v, depth + 1) for v in value[:1000]]
    if not isinstance(value, str):
        return value
    text = value[:32_000]
    if text.lstrip().startswith(("{", "[")):
        try:
            return json.dumps(clean(json.loads(text), depth + 1), ensure_ascii=False)
        except (ValueError, RecursionError):
            pass
    text = re.sub(r"-----BEGIN .*?PRIVATE KEY-----.*?(?:-----END .*?PRIVATE KEY-----|$)",
                  "[已隐藏私钥]", text, flags=re.S)
    text = re.sub(r"""(?im)^.*\b(?:password|passwd|secret|token|client_secret|access_token|refresh_token|api[_-]?key|cookie|authorization)["']?\s*[=:].*$""",
                  "[已隐藏敏感行]", text)
    text = re.sub(r"(?i)\bBearer\s+[^\s\"'<>]+", "Bearer [已隐藏]", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}|\beyJ[\w-]+\.[\w-]+\.[\w-]+", "[已隐藏凭证]", text)
    return text


def valid_id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ConsoleError("INVALID_ID")
    return value


class ConsoleService:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.runs = self.root / "runs"
        self.lock = threading.Lock()

    def databases(self):
        result = {}
        if not self.runs.is_dir() or self.runs.is_symlink():
            return result
        # Existing per-run layout only; never scan SDK homes or the entire disk.
        for directory in sorted(self.runs.iterdir()):
            if directory.is_dir() and not directory.is_symlink():
                path = directory / "blackboard.sqlite"
                if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(self.runs.resolve()):
                    key = hashlib.sha256(directory.name.encode()).hexdigest()[:20]
                    result[key] = (directory.name, path)
        return result

    def path(self, run_id):
        valid_id(run_id)
        found = self.databases().get(run_id)
        if not found:
            raise ConsoleError("RUN_NOT_FOUND", 404)
        return found

    def read(self, run_id):
        name, path = self.path(run_id)
        try:
            db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
            try:
                db.execute("PRAGMA query_only=ON")
                data = {}
                truncated = []
                for table in TABLES:
                    rows = db.execute(f"SELECT data FROM {table} ORDER BY rowid DESC LIMIT 1001").fetchall()
                    if len(rows) > 1000:
                        truncated.append(table)
                    data[table] = [json.loads(row[0]) for row in rows[:1000]]
                return {"id": run_id, "name": name, "tables": data, "truncated": truncated}
            finally:
                db.close()
        except (sqlite3.Error, ValueError, OSError):
            raise ConsoleError("DATABASE_UNAVAILABLE", 503) from None

    def overview(self):
        runs, totals = [], {}
        for key, (name, _) in self.databases().items():
            try:
                data = self.read(key)
                tasks = data["tables"]["tasks"]
                counts = {}
                for task in tasks:
                    status = task.get("status", "UNKNOWN")
                    counts[status] = counts.get(status, 0) + 1
                    totals[status] = totals.get(status, 0) + 1
                times = [str(e.get("timestamp", "")) for e in data["tables"]["events"]]
                runs.append({"id": key, "name": name, "counts": counts,
                             "projects": clean(data["tables"]["projects"]),
                             "last_event": max(times, default=""), "truncated": data["truncated"],
                             "database_status": "READABLE"})
            except ConsoleError:
                runs.append({"id": key, "name": name, "database_status": "UNAVAILABLE",
                             "counts": {}, "projects": [], "last_event": "", "truncated": []})
        runs.sort(key=lambda v: v["last_event"], reverse=True)
        return clean({"runs": runs, "counts": totals, "agents": self.agents(),
                      "execution_enabled": False, "record_limit_per_table": 1000})

    def agents(self):
        # Verified task IDs from the accepted historical evidence chain, not live probes.
        expected = {"DSH": {"fc7dafe937ad4b8299c541cc9eebff85", "18e6faac47e7484083e0388b2a68c523"},
                    "Codex": {"d3ba8800093a45a5ba0f3bf1de47813a"}}
        evidence = {"DSH": [], "Codex": [], "WorkBuddy": []}
        histories = {k: [] for k in evidence}
        failures = {k: [] for k in evidence}
        for run_id in self.databases():
            try:
                data = self.read(run_id)["tables"]
            except ConsoleError:
                continue
            agents = {a["id"]: a.get("provider_id") for a in data["agents"]}
            tasks = {t["id"]: t for t in data["tasks"]}
            for t in tasks.values():
                provider = agents.get(t.get("assigned_to"))
                if provider in histories:
                    histories[provider].append({"run_id": run_id, "task_id": t["id"],
                                                "status": t.get("status"), "stage": t.get("task_type"),
                                                "time": t.get("updated_at")})
            for msg in data["messages"]:
                provider = agents.get(msg.get("from_agent"))
                if (provider in expected and msg.get("task_id") in expected[provider] and
                    msg.get("metadata", {}).get("mock") is False and
                    msg.get("type") in {"PROPOSE", "COMPLETE", "APPROVE"}):
                    evidence[provider].append({"run_id": run_id, "task_id": msg["task_id"],
                                               "message_id": msg["id"], "result": msg["type"],
                                               "time": msg.get("timestamp")})
            for e in data["events"]:
                provider = agents.get(tasks.get(e.get("task_id"), {}).get("assigned_to"))
                if provider in failures and e.get("type") == "PROVIDER_FAILURE":
                    failures[provider].append({"run_id": run_id, "task_id": e.get("task_id"),
                                               "time": e.get("timestamp"), "diagnostic": e.get("metadata")})
        try:
            wb = configuration_status()
        except Exception:
            wb = {"status": "UNKNOWN"}
        result = []
        for name, role in [("DSH", "Architect"), ("Codex", "Engineer"), ("WorkBuddy", "Reviewer")]:
            result.append({
                "id": name, "role": role,
                "status": "PARTIAL" if name == "WorkBuddy" else "REAL_VERIFIED" if evidence[name] else "UNKNOWN",
                "live_status": "UNKNOWN",
                "authorization": ("CONFIGURED" if wb.get("status") == "CONFIGURED" else "AUTH_REQUIRED")
                if name == "WorkBuddy" else "UNKNOWN",
                "configuration": wb if name == "WorkBuddy" else {
                    "executable_on_path": bool(shutil.which("codex" if name == "Codex" else "dsh")),
                    "note": "仅 PATH 存在性；不验证登录，不启动客户端"},
                "capabilities": {"DSH": ["历史真实规划", "历史独立审核"],
                                 "Codex": ["历史代码实现", "历史实际测试", "返工接口"],
                                 "WorkBuddy": ["HTTP/OAuth 代码", "有界消息观察", "正式审核阻断"]}[name],
                "limits": {"DSH": "曾因 4096 输出上限失败；独立审核 reasoning_effort=off 后通过。",
                           "Codex": "历史成功不代表当前在线或额度可用。",
                           "WorkBuddy": "缺少已确认的任务关联与终态协议；不自动 OAuth。"}[name],
                "evidence": evidence[name],
                "history": sorted(histories[name], key=lambda h: h.get("time") or "", reverse=True)[:20],
                "failures": sorted(failures[name], key=lambda h: h.get("time") or "", reverse=True)[:5],
                "default_mode": "MOCK" if name == "WorkBuddy" else "EXPLICIT_SELECTION",
            })
        return clean(result)

    def snapshot(self, run_id):
        data = self.read(run_id)
        # Never expose credentials in provider/session records; session tables are excluded.
        data["tables"]["providers"] = [
            {k: p[k] for k in ("id", "mock", "capabilities") if k in p}
            for p in data["tables"]["providers"]]
        return clean(data)

    def task_detail(self, run_id, task_id):
        valid_id(task_id)
        data = self.read(run_id)["tables"]
        task = next((t for t in data["tasks"] if t["id"] == task_id), None)
        if task is None:
            raise ConsoleError("TASK_NOT_FOUND", 404)
        messages = [m for m in data["messages"] if m.get("task_id") == task_id]
        events = [e for e in data["events"] if e.get("task_id") == task_id]
        # Only explicit event references establish a task/decision relationship.
        refs = {e.get("metadata", {}).get("decision_id") for e in events}
        decisions = [d for d in data["decisions"] if d["id"] in refs]
        return clean({"task": task, "messages": messages, "events": events,
                      "decisions": decisions,
                      "artifacts": [a for a in data["artifacts"] if a.get("task_id") == task_id],
                      "application_attempts": sum(e.get("type") == "TURN_RESERVED" for e in events),
                      "retry_count": None, "revision_count": task.get("revision_count", 0)})

    def artifact_hash(self, run_id, artifact_id):
        valid_id(artifact_id)
        data = self.read(run_id)["tables"]
        artifact = next((a for a in data["artifacts"] if a["id"] == artifact_id), None)
        if artifact is None:
            raise ConsoleError("ARTIFACT_NOT_FOUND", 404)
        _, db_path = self.path(run_id)
        base = db_path.parent / "workspace"
        relative = Path(artifact.get("path", ""))
        if (relative.is_absolute() or ".." in relative.parts or not relative.parts or
            any(part.startswith(".") for part in relative.parts) or
            relative.suffix.lower() not in {".py", ".txt", ".md", ".json"}):
            raise ConsoleError("RESOURCE_DENIED", 403)
        target = base / relative
        if (not target.resolve().is_relative_to(base.resolve()) or base.is_symlink() or
            any(p.is_symlink() for p in [target, *target.parents] if p != self.root)):
            raise ConsoleError("RESOURCE_DENIED", 403)
        if not target.is_file():
            return {"status": "MISSING", "stored_sha256": artifact.get("sha256")}
        if target.stat().st_size > 2_000_000:
            raise ConsoleError("RESOURCE_TOO_LARGE", 413)
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        return clean({"status": "MATCH" if actual == artifact.get("sha256") else "MISMATCH",
                      "stored_sha256": artifact.get("sha256"), "actual_sha256": actual})

    def report(self, index):
        if not str(index).isdigit() or int(index) >= len(REPORTS):
            raise ConsoleError("RESOURCE_DENIED", 403)
        path = self.root / REPORTS[int(index)]
        if path.is_symlink() or not path.resolve().is_relative_to(self.root) or not path.is_file():
            raise ConsoleError("REPORT_NOT_FOUND", 404)
        return {"name": REPORTS[int(index)], "content": clean(path.read_text(encoding="utf-8")[:32_000])}

    def diagnostics(self):
        return {"data_directory": str(self.runs), "sqlite": "READ_ONLY_HISTORY",
                "reports": [{"id": str(i), "name": name, "exists": (self.root / name).is_file()}
                            for i, name in enumerate(REPORTS)],
                "model_execution": "DISABLED", "oauth": "DISABLED", "agents": self.agents(),
                "test_note": "测试数字来自标注版本的验收报告；不代表后台自动执行了测试。"}

    def create_draft(self, body):
        if not isinstance(body, dict) or set(body) != {"title", "description", "agent", "request_id"}:
            raise ConsoleError("INVALID_DRAFT")
        if (not isinstance(body["title"], str) or not 1 <= len(body["title"].strip()) <= 160 or
            not isinstance(body["description"], str) or len(body["description"]) > 8000 or
            not isinstance(body["agent"], str) or body["agent"] not in {"DSH", "Codex", "WorkBuddy"}):
            raise ConsoleError("INVALID_DRAFT")
        request_id = valid_id(body["request_id"])
        # Request ID becomes the task ID: repeat clicks/retries return same pending task.
        root = self.runs / "console"
        if self.runs.is_symlink() or root.is_symlink() or (root / "blackboard.sqlite").is_symlink():
            raise ConsoleError("RESOURCE_DENIED", 403)
        with self.lock:
            db = Database(root / "blackboard.sqlite")
            try:
                existing = db.get("tasks", request_id)
                if existing:
                    if (existing["title"] != body["title"].strip() or
                        existing["description"] != body["description"] or
                        existing["assigned_to"] != body["agent"]):
                        raise ConsoleError("REQUEST_CONFLICT", 409)
                    return clean(existing)
                team = Team(id="console-team", name="Console drafts", agent_ids=["DSH", "Codex", "WorkBuddy"])
                project = Project(id="console-project", team_id=team.id, goal="用户显式创建的待执行草稿")
                db.put("teams", team)
                db.put("projects", project)
                for name, role in (("DSH", "ARCHITECT"), ("Codex", "ENGINEER"), ("WorkBuddy", "REVIEWER")):
                    db.put("agents", {"id": name, "provider_id": name, "name": name, "role": role})
                task = Task(id=request_id, project_id=project.id, title=body["title"].strip(),
                            description=body["description"], created_by="user",
                            assigned_to=body["agent"], task_type="DRAFT")
                TaskManager(db, EventBus(db)).create(task)
                return clean(task.model_dump(mode="json"))
            finally:
                db.close()
