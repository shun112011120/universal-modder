"""The desktop app's server and chat loop, against a fake Ollama (no GPU, no network).

    uv run --with pytest pytest -q tests/test_app.py
"""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from um import app  # noqa: E402


class FakeOllama:
    """Streams scripted /api/chat replies (one list of chunks per request) and records what it was sent."""

    def __init__(self, replies):
        self.replies, self.requests = list(replies), []
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                body = json.dumps({"models": [{"name": "fake-model:7b", "size": 1, "details": {"parameter_size": "7B"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                fake.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                chunks = fake.replies.pop(0)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                for c in chunks:
                    self.wfile.write((json.dumps(c) + "\n").encode())

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


def say(text):
    return [{"message": {"role": "assistant", "content": t}, "done": False} for t in text.split("|")] + [{"message": {}, "done": True}]


def call(name, **args):
    return [{"message": {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]}, "done": False},
            {"message": {}, "done": True}]


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("UM_HOME", str(tmp_path / "home"))
    ws = tmp_path / "ws"
    app.save_config({"workspace": str(ws), "model": "fake-model:7b"})
    return tmp_path


def test_tool_schemas_are_complete():
    schemas = app.tool_schemas()
    assert [s["function"]["name"] for s in schemas] == list(app.TOOLS)
    for s in schemas:
        params = s["function"]["parameters"]
        assert set(params["required"]) <= set(params["properties"])


def test_write_file_needs_approval_only_outside_workspace(home):
    assert not app.needs_approval("write_file", {"path": "MyMod/Mod.cs"})
    assert not app.needs_approval("write_file", {"path": str(home / "ws" / "a.txt")})
    assert app.needs_approval("write_file", {"path": str(home / "elsewhere" / "a.txt")})
    assert app.needs_approval("write_file", {"path": "../escape.txt"})
    assert app.needs_approval("run_command", {"command": "dir"}) and app.needs_approval("backup_restore", {"name": "x"})
    assert not app.needs_approval("scan_game", {"game": "x"})


def test_chat_runs_tools_and_streams(home):
    (home / "ws").mkdir(exist_ok=True)
    (home / "ws" / "notes.txt").write_text("hello mod")
    fake = FakeOllama([call("read_file", path="notes.txt"), call("write_file", path="MyMod/build.txt", content="ok"), say("All |done.")])
    events = []
    try:
        new = app.chat_turn([{"role": "user", "content": "read my notes"}], events.append,
                            dict(app.load_config(), ollama_url=fake.url))
    finally:
        fake.close()
    assert (home / "ws" / "MyMod" / "build.txt").read_text() == "ok"
    types = [e["type"] for e in events]
    assert types.count("tool") == 2 and types.count("tool_result") == 2 and "approve" not in types
    assert "".join(e["text"] for e in events if e["type"] == "delta") == "All done."
    assert [m["role"] for m in new] == ["assistant", "tool", "assistant", "tool", "assistant"]
    assert new[1]["content"] == "hello mod" and new[1]["tool_name"] == "read_file"
    first = fake.requests[0]
    assert first["messages"][0]["role"] == "system" and "Universal Modder" in first["messages"][0]["content"]
    assert first["tools"] and first["options"]["num_ctx"] == app.load_config()["num_ctx"] and first["model"] == "fake-model:7b"
    assert fake.requests[2]["messages"][-1]["role"] == "tool"          # results go back to the model


def test_chat_waits_for_approval_and_respects_deny(home):
    fake = FakeOllama([call("run_command", command="echo hi"), say("OK, I won't.")])
    events = []

    def emit(ev):
        events.append(ev)
        if ev["type"] == "approve":
            assert app.APPROVALS.answer(ev["approval"], False)

    try:
        new = app.chat_turn([{"role": "user", "content": "build it"}], emit, dict(app.load_config(), ollama_url=fake.url))
    finally:
        fake.close()
    approved = next(e for e in events if e["type"] == "approved")
    assert approved["ok"] is False
    assert "denied" in new[1]["content"] and new[-1]["content"] == "OK, I won't."


def test_chat_explains_missing_ollama(home):
    with pytest.raises(app.ToolError, match="can't reach Ollama"):
        app.chat_turn([{"role": "user", "content": "hi"}], lambda e: None, dict(app.load_config(), ollama_url="http://127.0.0.1:9"))


def test_server_checks_token_host_and_serves_tools(home):
    srv = app.App().start()
    base = f"http://127.0.0.1:{srv.port}"

    def req(path, body=None, token=srv.token, host=None):
        r = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                   headers={"X-UM-Token": token, "Content-Type": "application/json", **({"Host": host} if host else {})})
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    try:
        assert req("/")[0] == 200 and b"Universal Modder" in req("/")[1]
        assert req("/app.js")[0] == 200 and req("/fonts/SpaceGrotesk-Bold.ttf")[0] == 200
        assert req("/../app.py")[0] == 404
        assert req("/api/status", token="nope")[0] == 401
        assert req("/api/status", host="evil.example:80")[0] == 403          # DNS rebinding
        code, body = req("/api/status")
        st = json.loads(body)
        assert code == 200 and st["config"]["model"] == "fake-model:7b" and "scan_game" in st["tools"]
        code, body = req("/api/tool", {"name": "read_guide", "args": {"name": "engines/unity"}})
        assert json.loads(body)["ok"] and "Unity" in json.loads(body)["result"]
        code, body = req("/api/tool", {"name": "kb_search", "args": {"query": "terraria"}})
        res = json.loads(body)
        assert res["ok"] and res["result"] and "terraria" in res["result"][0]["path"]
        code, body = req("/api/tool", {"name": "backup_list", "args": {}})
        assert json.loads(body) == {"ok": True, "result": []}
        code, body = req("/api/tool", {"name": "scan_game", "args": {}})
        assert not json.loads(body)["ok"] and "missing" in json.loads(body)["error"]
        code, body = req("/api/config", {"num_ctx": 65536})
        assert json.loads(body)["config"]["num_ctx"] == 65536
    finally:
        srv.stop()


def test_backup_roundtrip_through_tools(home):
    saves = home / "saves"
    saves.mkdir()
    (saves / "world.wld").write_text("v1")
    app.call_tool("backup_create", {"folder": str(saves), "name": "test-saves"})
    (saves / "world.wld").write_text("v2")
    assert app.call_tool("backup_diff", {"name": "test-saves"})["changed"] == ["world.wld"]
    rows = app.call_tool("backup_list", {})
    assert rows[0]["name"] == "test-saves" and rows[0]["files"] == 1
    app.call_tool("backup_restore", {"name": "test-saves"})
    assert (saves / "world.wld").read_text() == "v1"
