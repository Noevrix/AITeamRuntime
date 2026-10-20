import hashlib
import http.client
import json
import threading
from pathlib import Path
import pytest
from ai_team.console.service import ConsoleService, ConsoleError, clean
from ai_team.console.server import make_server
from ai_team.memory.database import Database


@pytest.fixture
def console(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_team.console.service.configuration_status", lambda: {"status": "NOT_CONFIGURED"})
    monkeypatch.setattr("ai_team.console.service.shutil.which", lambda _: None)
    root = tmp_path / "project"
    root.mkdir()
    dist = root / "console/dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text('<html><div id="root">Console</div></html>')
    service = ConsoleService(root)
    return service


def seed(service, mock=False):
    root = service.runs / "sample"
    db = Database(root / "blackboard.sqlite")
    task = {"id":"fc7dafe937ad4b8299c541cc9eebff85", "project_id":"p", "title":"Plan",
            "assigned_to":"architect", "status":"FAILED", "task_type":"PLAN",
            "description":"API_KEY=synthetic-sensitive", "revision_count":1}
    db.put("projects", {"id":"p","goal":"sample"})
    db.put("tasks", task)
    db.put("agents", {"id":"architect","provider_id":"DSH","name":"DSH"})
    db.put("providers", {"id":"DSH","mock":mock,"access_token":"synthetic-sensitive"})
    db.put("messages", {"id":"m","project_id":"p","task_id":task["id"],"from_agent":"architect",
                        "type":"PROPOSE","content":'{"password":"synthetic-sensitive","plan":"safe"}',
                        "metadata":{"mock":mock}})
    db.put("decisions", {"id":"d","project_id":"p","content":"safe plan"})
    db.put("decisions", {"id":"unlinked","project_id":"p","content":"unlinked"})
    db.put("events", {"id":"e","project_id":"p","task_id":task["id"],"type":"BLACKBOARD_VERIFIED",
                      "metadata":{"decision_id":"d"}})
    db.put("events", {"id":"failure","project_id":"p","task_id":task["id"],"type":"PROVIDER_FAILURE",
                      "metadata":{"diagnostic":{"code":"MODEL_MAX_TOKENS"}}})
    (root / "workspace").mkdir()
    (root / "workspace/todo.py").write_text("print('safe')")
    digest = hashlib.sha256((root / "workspace/todo.py").read_bytes()).hexdigest()
    db.put("artifacts", {"id":"a","project_id":"p","task_id":task["id"],"path":"todo.py","sha256":digest})
    db.close()
    return next(iter(service.databases())), task["id"]


def test_empty_overview_no_write_no_model(console, monkeypatch):
    # The console never instantiates a provider; fail loudly if regression imports execute.
    from ai_team.kernel.team_kernel import TeamKernel
    monkeypatch.setattr(TeamKernel, "execute", lambda *_: pytest.fail("model execution"))
    assert console.overview()["runs"] == []
    assert not console.runs.exists()
    agents = console.agents()
    assert [a["status"] for a in agents] == ["UNKNOWN", "UNKNOWN", "PARTIAL"]
    assert all(a["live_status"] == "UNKNOWN" for a in agents)
    assert agents[-1]["authorization"] == "AUTH_REQUIRED"


def test_history_is_readonly_linked_and_redacted(console):
    run, task = seed(console)
    db_path=console.path(run)[1]
    before=db_path.read_bytes()
    for _ in range(2):
        overview=console.overview()
        snapshot=console.snapshot(run)
        detail=console.task_detail(run, task)
    assert db_path.read_bytes()==before
    assert overview["counts"]["FAILED"]==1
    assert detail["task"]["status"]=="FAILED"
    assert [d["id"] for d in detail["decisions"]]==["d"]
    assert detail["retry_count"] is None
    assert "timestamp" not in snapshot["tables"]["events"][0]
    assert "synthetic-sensitive" not in json.dumps(snapshot)
    dsh=overview["agents"][0]
    assert dsh["status"]=="REAL_VERIFIED" and dsh["live_status"]=="UNKNOWN"
    assert dsh["failures"][0]["diagnostic"]["diagnostic"]["code"]=="MODEL_MAX_TOKENS"


def test_mock_never_establishes_real_verification(console):
    run,_=seed(console, mock=True)
    assert console.agents()[0]["status"]=="UNKNOWN"
    assert console.snapshot(run)["tables"]["messages"][0]["metadata"]["mock"] is True


def test_draft_creation_uses_existing_task_manager_and_is_idempotent(console):
    body={"title":"draft","description":"do later","agent":"Codex","request_id":"draft-1"}
    first=console.create_draft(body)
    assert first["status"]=="PENDING" and first["task_type"]=="DRAFT"
    assert console.create_draft(body)==first
    run=next(iter(console.databases()))
    data=console.read(run)["tables"]
    assert len(data["tasks"])==1 and len(data["events"])==1
    assert data["events"][0]["type"]=="TASK_CREATED"
    assert data["messages"]==[]
    with pytest.raises(ConsoleError,match="REQUEST_CONFLICT"):
        console.create_draft({**body,"title":"different"})
    with pytest.raises(ConsoleError):
        console.create_draft({**body,"execute":True})
    assert console.agents()[1]["history"][0]["task_id"]=="draft-1"
    with pytest.raises(ConsoleError,match="INVALID_DRAFT"):
        console.create_draft({**body,"agent":[]})


def test_artifact_hash_and_traversal_rejection(console):
    run,_=seed(console)
    assert console.artifact_hash(run,"a")["status"]=="MATCH"
    path=console.path(run)[1]
    db=Database(path)
    db.put("artifacts",{"id":"bad","path":"../../.env"})
    db.close()
    with pytest.raises(ConsoleError,match="RESOURCE_DENIED"):
        console.artifact_hash(run,"bad")
    with pytest.raises(ConsoleError):
        console.task_detail(run,"../secret")
    with pytest.raises(ConsoleError):
        console.report("../../.env")


@pytest.mark.parametrize("value",[
    {"api_key":"synthetic-sensitive"}, {"nested":[{"Cookie":"synthetic-sensitive"}]},
    'Authorization: Bearer synthetic-sensitive',
    '{"access_token":"synthetic-sensitive"}',
    'password=synthetic-sensitive',
    'unstructured log {"api_key":"synthetic-sensitive"}',
    'https://example.invalid/callback?token=synthetic-sensitive',
])
def test_sensitive_fields_never_in_projection(value):
    assert "synthetic-sensitive" not in json.dumps(clean(value))


@pytest.fixture
def http_server(console):
    server=make_server(console.root,0)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join()


def request(server,method,path,body=None,headers=None):
    connection=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=3)
    connection.request(method,path,body=body,headers=headers or {})
    response=connection.getresponse()
    result=(response.status, dict(response.getheaders()),response.read())
    connection.close()
    return result


def session(server):
    status,headers,_=request(server,"GET","/")
    assert status==200 and "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    cookie=headers["Set-Cookie"].split(";")[0]
    _,_,body=request(server,"GET","/api/session",headers={"Cookie":cookie})
    return {"Cookie":cookie,"X-Console-CSRF":json.loads(body)["csrf"],
            "Origin":f"http://127.0.0.1:{server.server_port}","Content-Type":"application/json"}


def test_http_page_refresh_never_executes_or_creates(console,http_server):
    headers=session(http_server)
    for _ in range(2):
        assert request(http_server,"GET","/api/overview",headers=headers)[0]==200
    assert not console.runs.exists()
    for path in ["/api/execute","/api/oauth","/api/shell","/api/files"]:
        assert request(http_server,"POST",path,"{}",headers)[0]==404
    assert not console.runs.exists()


def test_http_access_boundaries_and_safe_errors(console,http_server):
    assert request(http_server,"GET","/api/overview")[0]==401
    headers=session(http_server)
    assert request(http_server,"GET","/api/overview",headers={**headers,"Origin":"https://evil.example"})[0]==403
    assert request(http_server,"GET","/",headers={"Host":"evil.example"})[0]==403
    assert request(http_server,"GET","/assets/../../.env",headers=headers)[0]==404
    assert request(http_server,"POST","/api/drafts","{}",{**headers,"X-Console-CSRF":"wrong"})[0]==403
    assert request(http_server,"POST","/api/drafts","not-json",headers)[0]==400
    assert not console.runs.exists()


def test_http_draft_is_only_explicit_mutation(console,http_server):
    headers=session(http_server)
    body=json.dumps({"title":"draft","description":"later","agent":"DSH","request_id":"repeat"})
    for _ in range(2):
        assert request(http_server,"POST","/api/drafts",body,headers)[0]==201
    run=next(iter(console.databases()))
    assert len(console.read(run)["tables"]["tasks"])==1
    assert request(http_server,"GET",f"/api/runs/{run}/tasks/absent",headers=headers)[0]==404
    assert console.read(run)["tables"]["tasks"][0]["status"]=="PENDING"


def test_conversation_http_persistence_consent_and_csrf(console, http_server):
    headers = session(http_server)
    assert request(http_server, "GET", "/api/conversations", headers=headers)[0] == 200
    assert not console.runs.exists()
    body = json.dumps({"goal": "Build an offline tool", "request_id": "one"})
    assert request(http_server, "POST", "/api/conversations", body,
                   {**headers, "X-Console-CSRF": "wrong"})[0] == 403
    assert not console.runs.exists()
    assert request(http_server, "POST", "/api/conversations", body, headers)[0] == 201
    assert request(http_server, "POST", "/api/conversations/one/comment",
                   json.dumps({"content": "Add tests"}), headers)[0] == 201
    _, _, raw = request(http_server, "GET", "/api/conversations/one", headers=headers)
    data = json.loads(raw)
    assert data["conversation"]["comments"] == ["Add tests"]
    assert len(data["messages"]) == 2
    assert request(http_server, "POST", "/api/conversations/one/discuss",
                   '{"confirm_model_calls":true}', headers)[0] == 403
    assert request(http_server, "POST", "/api/conversations/one/cancel", "{}", headers)[0] == 201
