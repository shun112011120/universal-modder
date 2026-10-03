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

    def __init__(self, replies, caps=("completion", "tools")):
        self.replies, self.requests, self.caps, self.unloaded = list(replies), [], list(caps), []
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

            def _json(self, obj):
                body = json.dumps(obj).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/api/show":
                    return self._json({"capabilities": fake.caps})
                if self.path == "/api/generate":
                    fake.unloaded.append(body)
                    return self._json({})
                fake.requests.append(body)
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
    assert [s["function"]["name"] for s in schemas] == [t for t in app.TOOLS if t not in app.SCREEN_ONLY]
    assert "generate_image" in app.text_tools_prompt() and "comfy_use_last" not in app.text_tools_prompt()
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
    assert {"type": "mode", "mode": "native"} in events
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


def test_portable_keeps_everything_in_the_app_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("UM_HOME", raising=False)
    monkeypatch.setenv("UM_PORTABLE", str(tmp_path / "Universal Modder"))
    from um import common
    assert common.data_dir() == tmp_path / "Universal Modder" / "data"
    assert app.config_path().parent == tmp_path / "Universal Modder" / "data"
    assert app.load_config()["workspace"] == str(tmp_path / "Universal Modder" / "My Mods")


# --------------------------------------------------------------------------- text tools (models without tool calling, e.g. Gemma 3)

def test_parse_text_call_variants():
    assert app.parse_text_call('Let me look.\n<tool>{"name": "scan_game", "arguments": {"game": "Terraria"}}</tool>') == \
        ("Let me look.", "scan_game", {"game": "Terraria"})
    assert app.parse_text_call('```json\n{"name": "list_games", "arguments": {}}\n```')[1] == "list_games"
    assert app.parse_text_call('{"tool": "kb_search", "args": {"query": "unity"}}')[1:] == ("kb_search", {"query": "unity"})
    assert app.parse_text_call('<tool>{"name": "read_file", "arguments": "{\\"path\\": \\"a.txt\\"}"}</tool>')[2] == {"path": "a.txt"}
    assert app.parse_text_call("Here is C#:\n```cs\nclass A {}\n```") is None          # code is not a tool call
    assert app.parse_text_call('<tool>{"name": "rm_rf", "arguments": {}}</tool>') is None  # unknown tools are ignored
    assert app.parse_text_call('<tool>{"name": "comfy_use_last", "arguments": {}}</tool>') is None


def test_chat_uses_text_tools_for_models_without_tool_calling(home):
    (home / "ws").mkdir(exist_ok=True)
    (home / "ws" / "notes.txt").write_text("hello mod")
    fake = FakeOllama([say('I will read it.\n<tool>{"name": "read_|file", "arguments": {"path": "notes.txt"}}</tool>'), say("It says |hello mod.")],
                      caps=["completion"])
    events = []
    try:
        new = app.chat_turn([{"role": "user", "content": "read my notes"}], events.append, dict(app.load_config(), ollama_url=fake.url))
    finally:
        fake.close()
    shown = "".join(e["text"] for e in events if e["type"] == "delta")
    assert "<tool>" not in shown and "I will read it." in shown and shown.endswith("It says hello mod.")
    assert {"type": "mode", "mode": "text"} in events
    assert all("tools" not in r for r in fake.requests)
    assert "<tool>" in fake.requests[0]["messages"][0]["content"]                       # tools described in the prompt
    assert new[1] == {"role": "user", "content": '<tool_result name="read_file">\nhello mod\n</tool_result>'}
    assert next(e for e in events if e["type"] == "tool_result")["ok"]


def test_tool_results_shrink_with_small_context():
    assert app.result_limit(4096) < app.result_limit(8192) < app.result_limit(65536) == app.MAX_TOOL_CHARS
    assert app.as_text("x" * 5000, 2000).startswith("x" * 2000) and "more characters cut" in app.as_text("x" * 5000, 2000)


# --------------------------------------------------------------------------- art (ComfyUI)

QWEN_GRAPH = {  # shaped like a Qwen-Image GGUF workflow: one encoder feeds both positive and negative
    "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "qwen-image.gguf"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl.safetensors", "type": "qwen_image"}},
    "3": {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["2", 0], "prompt": "a ghoul in a T-pose", "resolution": 1024}},
    "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 768, "batch_size": 1}},
    "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["3", 0], "negative": ["3", 1], "latent_image": ["4", 0],
                                               "seed": 42, "steps": 20, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
    "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["7", 0]}},
    "7": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_vae.safetensors"}},
    "8": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "ghoul_tpose"}},
}


def test_fill_workflow_sets_prompt_size_seed_and_prefix():
    g = app.fill_workflow(QWEN_GRAPH, "a golden hoe", 1024, 512, 7, "golden_hoe")
    assert g["3"]["inputs"]["prompt"] == "a golden hoe" and g["3"]["inputs"]["clip"] == ["2", 0]
    assert (g["4"]["inputs"]["width"], g["4"]["inputs"]["height"]) == (1024, 512)
    assert g["5"]["inputs"]["seed"] == 7 and g["8"]["inputs"]["filename_prefix"] == "universal-modder/golden_hoe"
    assert QWEN_GRAPH["3"]["inputs"]["prompt"] == "a ghoul in a T-pose"                   # the template is untouched
    classic = {"1": {"class_type": "CLIPTextEncode", "inputs": {"text": "neg"}}, "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "pos"}},
               "3": {"class_type": "KSampler", "inputs": {"positive": ["2", 0], "negative": ["1", 0], "seed": 1}},
               "4": {"class_type": "SaveImage", "inputs": {}}}
    g = app.fill_workflow(classic, "sword", 512, 512, 3, "s")
    assert g["2"]["inputs"]["text"] == "sword" and g["1"]["inputs"]["text"] == "neg"


class FakeComfy:
    def __init__(self, png: bytes):
        self.prompts, self.freed = [], 0
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, body, ctype="application/json"):
                body = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path.startswith("/system_stats"):
                    return self._send({"system": {}})
                if self.path.startswith("/history/"):
                    pid = self.path.rsplit("/", 1)[1]
                    return self._send({pid: {"status": {"status_str": "success", "completed": True},
                                             "outputs": {"8": {"images": [{"filename": "x_00001_.png", "subfolder": "universal-modder", "type": "output"}]}}}})
                if self.path.startswith("/history"):
                    edit = json.loads(json.dumps(QWEN_GRAPH))
                    edit["9"] = {"class_type": "LoadImage", "inputs": {"image": "a.png"}}
                    return self._send({"old": {"prompt": [1, "old", QWEN_GRAPH, {}, ["8"]], "status": {"status_str": "success"}},
                                       "newer-edit": {"prompt": [2, "newer-edit", edit, {}, ["8"]], "status": {"status_str": "success"}}})
                if self.path.startswith("/view"):
                    return self._send(png, "image/png")

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/prompt":
                    fake.prompts.append(body["prompt"])
                    return self._send({"prompt_id": "p1"})
                if self.path == "/free":
                    fake.freed += 1
                    return self._send({})

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


def test_art_from_comfy_history_to_sprite(home):
    import io
    from PIL import Image
    im = Image.new("RGB", (256, 256), (200, 200, 200))
    for x in range(96, 160):
        for y in range(64, 192):
            im.putpixel((x, y), (200, 160, 30))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    comfy, ollama = FakeComfy(buf.getvalue()), FakeOllama([])
    app.save_config({"comfy_url": comfy.url, "ollama_url": ollama.url})
    try:
        with pytest.raises(app.ToolError, match="no ComfyUI workflow"):
            app.call_tool("generate_image", {"prompt": "a golden hoe"})
        st = app.call_tool("comfy_use_last", {})
        assert st["running"] and "TextEncodeQwenImage21" in st["template"]["nodes"] and "LoadImage" not in st["template"]["nodes"]
        res = app.call_tool("generate_image", {"prompt": "a golden hoe", "name": "golden hoe", "size": "768x768"})
        sent = comfy.prompts[0]
        assert sent["3"]["inputs"]["prompt"].startswith("a golden hoe, a single game item") and sent["4"]["inputs"]["width"] == 768
        assert ollama.unloaded == [{"model": "fake-model:7b", "keep_alive": 0}] and comfy.freed == 1   # 8 GB cards: one at a time
        art = Path(res["files"][0])
        assert art.parent == home / "ws" / "art" and art.name == "golden_hoe.png" and art.read_bytes() == buf.getvalue()
        assert app.call_tool("list_art", {})[0]["name"] == "golden_hoe.png"
        sprite = app.call_tool("make_sprite", {"image": str(art), "size": "32x32", "colors": "8"})
        out = Image.open(sprite["output"])
        assert out.size == (32, 32) and out.mode == "RGBA" and out.getpixel((0, 0))[3] == 0      # background cut out
    finally:
        comfy.close()
        ollama.close()
