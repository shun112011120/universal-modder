"""The Universal Modder desktop app: an AI chat that mods games with this toolkit, plus buttons for the tools.

    um app                                   # open the app window
    um app --no-window                       # only serve it; open the printed URL in any browser
    um app --ollama http://localhost:11434 --model qwen3-coder
    um app --self-test                       # start the server, call it, print the results (used by CI)

The chat runs on a model in your own Ollama (https://ollama.com). Its tools are this toolkit's commands (scan,
knowledge base, backups, publish check), reading files, writing mod files into your workspace folder, running
build commands and making art with your ComfyUI. Models with tool calling (qwen3, llama3.1, ...) use it
directly; models without it (Gemma 3, custom GGUF imports) get the tools as text instructions instead
("text tools", picked automatically). Restoring a backup, writing outside the workspace and running a command
always wait for you to click Allow.

Art: the app runs a ComfyUI workflow you already use (taken from ComfyUI's history, or an API-format export),
filling in the prompt, size and seed, then cuts out, fits and pixelates the result into a game sprite. On a
small GPU it unloads the chat model before generating and frees ComfyUI's memory afterwards.

The window is the app's own server on 127.0.0.1 (random port, a fresh token per launch) shown in an Edge or
Chrome app window, or pywebview when it is installed. Settings live in ~/.universal-modder/app.json; when
portable (UM_PORTABLE, set by the Windows app and `Universal Modder.cmd`) settings, backups, the window's
browser profile and the workspace ("My Mods") all stay inside the app folder.
"""
from __future__ import annotations

import datetime as dt
import hmac
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from um import __version__
from um.common import data_dir, is_mac, is_windows, is_wsl, portable_root

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                       # the repo (or the PyInstaller bundle): skills/ and knowledge/ live here
UI = HERE / "app_ui"
FONTS = HERE / "fonts"
NO_WINDOW = 0x08000000 if is_windows() else 0      # CREATE_NO_WINDOW: no console flashes for tool processes
MAX_TOOL_CHARS = 12_000
MAX_STEPS = 16
DEFAULTS = dict(ollama_url="http://localhost:11434", model="", num_ctx=32768, workspace="", tool_mode="auto",
                comfy_url="http://127.0.0.1:8188", free_vram=True)
TOOL_MODES = ("auto", "native", "text")


# --------------------------------------------------------------------------- settings

def config_path() -> Path:
    return data_dir() / "app.json"


def default_workspace() -> str:
    if portable_root():
        return str(portable_root() / "My Mods")
    docs = Path.home() / "Documents"
    return str((docs if docs.is_dir() else Path.home()) / "Universal Modder")


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    try:
        cfg.update({k: v for k, v in json.loads(config_path().read_text()).items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    cfg["workspace"] = cfg["workspace"] or default_workspace()
    return cfg


def save_config(cfg: dict) -> dict:
    cur = load_config()
    for k, v in cfg.items():
        if k == "num_ctx":
            cur[k] = max(2048, min(int(v), 1 << 20))
        elif k == "free_vram":
            cur[k] = bool(v)
        elif k == "tool_mode":
            cur[k] = v if v in TOOL_MODES else "auto"
        elif k in DEFAULTS and isinstance(v, str):
            cur[k] = v.strip()
    config_path().write_text(json.dumps(cur, indent=1))
    return cur


# --------------------------------------------------------------------------- running `um`

class ToolError(Exception):
    pass


def um_cmd() -> list[str]:
    """How to call the toolkit CLI from here: `python -m um`, or um.exe next to a frozen app."""
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).with_name("um.exe" if is_windows() else "um"))]
    return [sys.executable, "-m", "um"]


def _um(args: list[str], timeout: float) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if not getattr(sys, "frozen", False):
        env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        return subprocess.run(um_cmd() + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, env=env, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise ToolError(f"`um {' '.join(map(str, args[:2]))}` took longer than {timeout:.0f}s")


def run_um(args: list[str], timeout: float = 600) -> str:
    r = _um(args, timeout)
    if r.returncode:
        msg = (r.stderr.strip() or r.stdout.strip() or f"exit code {r.returncode}").removeprefix("um: ")
        raise ToolError(msg[-3000:])
    return r.stdout


def run_um_json(args: list[str], timeout: float = 600):
    out = run_um(args, timeout)
    try:
        return json.loads(out)
    except ValueError:
        raise ToolError(f"unexpected output from `um {' '.join(args[:2])}`: {out[:500]}")


# --------------------------------------------------------------------------- tools (shared by the buttons and the AI)

def _workspace() -> Path:
    ws = Path(load_config()["workspace"]).expanduser()
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def _path(p: str) -> Path:
    q = Path(os.path.expandvars(str(p or "").strip().strip('"'))).expanduser()
    return q if q.is_absolute() else _workspace() / q


def _inside(p: Path, folder: Path) -> bool:
    try:
        p.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def t_list_games():
    return run_um_json(["scan", "--list", "--json"], timeout=120)


def t_scan_game(game: str):
    return run_um_json(["scan", game, "--json"], timeout=300)


def t_kb_search(query: str = "", game: str = ""):
    return run_um_json(["kb", "search", *query.split(), *(["--game", game] if game else []), "--json"], timeout=120)


def t_kb_show(note: str):
    return run_um(["kb", "show", note], timeout=120)


def guides() -> dict[str, Path]:
    out = {}
    for p in sorted((ROOT / "skills").glob("*/SKILL.md")):
        out[p.parent.name] = p
    for p in sorted((ROOT / "skills" / "mod-any-game" / "references").rglob("*.md")):
        rel = p.relative_to(ROOT / "skills" / "mod-any-game" / "references").with_suffix("").as_posix()
        out[rel] = p
    return out


def t_read_guide(name: str):
    g = guides()
    key = name.strip().removesuffix(".md").removeprefix("references/")
    if key not in g:
        key = next((k for k in g if k.endswith("/" + key) or k == "engines/" + key), "")
    if not key:
        return f"no guide {name!r}. Available: {', '.join(g)}"
    return g[key].read_text(encoding="utf-8", errors="replace")


def t_list_files(path: str):
    p = _path(path)
    if not p.is_dir():
        raise ToolError(f"not a folder: {p}")
    rows = []
    for c in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower()))[:300]:
        try:
            rows.append(c.name + "/" if c.is_dir() else f"{c.name}  ({c.stat().st_size:,} bytes)")
        except OSError:
            rows.append(c.name + "  (unreadable)")
    more = sum(1 for _ in p.iterdir()) - len(rows)
    return f"{p}\n" + "\n".join(rows) + (f"\n... and {more} more" if more > 0 else "")


def t_read_file(path: str):
    p = _path(path)
    if not p.is_file():
        raise ToolError(f"no such file: {p}")
    with open(p, "rb") as f:
        head = f.read(200_000)
    if b"\0" in head[:8192]:
        return f"{p} is a binary file ({p.stat().st_size:,} bytes); only text files can be read"
    txt = head.decode("utf-8", errors="replace")
    return txt[:30_000] + ("\n... (truncated)" if len(txt) > 30_000 or p.stat().st_size > len(head) else "")


def t_write_file(path: str, content: str):
    p = _path(path)
    existed = p.exists()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"{'overwrote' if existed else 'wrote'} {p} ({len(content.encode()):,} bytes)"


def t_run_command(command: str, folder: str = ""):
    cwd = _path(folder) if folder else _workspace()
    if not cwd.is_dir():
        raise ToolError(f"not a folder: {cwd}")
    try:
        r = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=900, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise ToolError("the command ran longer than 15 minutes and was stopped")
    out = (r.stdout + ("\n" + r.stderr if r.stderr.strip() else "")).strip()
    return f"exit code {r.returncode}\n{out[-10_000:]}"


def t_backup_list():
    return run_um_json(["backup", "list", "--json"], timeout=120)


def t_backup_create(folder: str, name: str = "", note: str = ""):
    return run_um(["backup", "create", folder, *(["--name", name] if name else []), "--note", note or "from the Universal Modder app"],
                  timeout=1800).strip()


def t_backup_diff(name: str):
    return run_um_json(["backup", "diff", name], timeout=600)


def t_backup_restore(name: str, snapshot: str = ""):
    return run_um(["backup", "restore", name, *(["--snapshot", snapshot] if snapshot else []), "--yes"], timeout=1800).strip()


def t_publish_check(folder: str, game: str = ""):
    r = _um(["publish", "check", str(_path(folder)), *(["--game", game] if game else [])], timeout=1800)
    if r.returncode not in (0, 1) or not r.stdout.strip():
        raise ToolError((r.stderr.strip() or "publish check failed").removeprefix("um: "))
    lines = r.stdout.strip().splitlines()
    return dict(passed=r.returncode == 0, summary=lines[-1], findings=lines[:-1])


# --------------------------------------------------------------------------- art (ComfyUI)

ART_STYLES = {
    "item": ", a single game item, centered, whole object in frame, plain flat light grey background, no text, no shadow",
    "character": ", full body character, front view, T-pose, centered, plain flat light grey background, no text",
    "texture": ", seamless tileable texture, flat even lighting, top-down, fills the whole frame",
    "none": "",
}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def comfy_template_path() -> Path:
    return data_dir() / "comfy_workflow.json"


class Comfy:
    """Just enough of ComfyUI's HTTP API: queue a graph, wait for it, fetch the images, free memory."""

    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def _req(self, path: str, body=None, timeout: float = 30, raw: bool = False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method="POST" if data is not None else "GET",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            try:
                d = json.loads(detail)
                err = d.get("error") or {}
                detail = (err.get("message") if isinstance(err, dict) else str(err)) or detail
                for nid, ne in (d.get("node_errors") or {}).items():
                    detail += f"; node {nid} ({ne.get('class_type')}): " + ", ".join(x.get("message", "") for x in ne.get("errors", []))
            except ValueError:
                pass
            raise ToolError(f"ComfyUI: {detail[:1500]}")
        except (urllib.error.URLError, OSError) as e:
            raise ToolError(f"ComfyUI isn't reachable at {self.url} ({getattr(e, 'reason', e)}). Start it (ComfyUI.bat) "
                            "and keep its window open, or fix the address in Settings.")
        return payload if raw else (json.loads(payload) if payload else {})

    def ok(self) -> bool:
        try:
            self._req("/system_stats", timeout=3)
            return True
        except ToolError:
            return False

    def history(self, max_items: int = 64) -> dict:
        return self._req(f"/history?max_items={max_items}")

    def run(self, graph: dict, timeout: float = 1800, on_wait=None) -> list[dict]:
        pid = self._req("/prompt", {"prompt": graph, "client_id": "universal-modder"}).get("prompt_id")
        if not pid:
            raise ToolError("ComfyUI didn't accept the workflow")
        t0 = time.time()
        while time.time() - t0 < timeout:
            h = self._req(f"/history/{pid}").get(pid)
            if h:
                st = h.get("status") or {}
                if st.get("status_str") == "error":
                    msgs = [m[1].get("exception_message", "") for m in st.get("messages", []) if m and m[0] == "execution_error"]
                    raise ToolError("ComfyUI failed: " + ("; ".join(msgs) or "see its console window"))
                imgs = [i for out in (h.get("outputs") or {}).values() for i in out.get("images", []) if i.get("type") == "output"]
                if imgs or st.get("completed"):
                    return imgs
            if on_wait:
                on_wait(time.time() - t0)
            time.sleep(2)
        raise ToolError(f"ComfyUI didn't finish within {timeout / 60:.0f} minutes (prompt {pid})")

    def image(self, img: dict) -> bytes:
        q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")})
        return self._req(f"/view?{q}", raw=True, timeout=120)

    def free(self):
        try:
            self._req("/free", {"unload_models": True, "free_memory": True}, timeout=30)
        except ToolError:
            pass


def _link(v) -> str | None:
    return str(v[0]) if isinstance(v, list) and len(v) == 2 and isinstance(v[1], int) else None


def _text_key(node: dict) -> str | None:
    ins = node.get("inputs") or {}
    return next((k for k in ("prompt", "text", "positive", "positive_prompt", "text_g") if isinstance(ins.get(k), str)), None)


def prompt_node(graph: dict) -> str | None:
    """The node that holds the positive prompt: what a sampler's `positive` input points at, else the first text encoder."""
    for node in graph.values():
        pos = _link((node.get("inputs") or {}).get("positive"))
        if pos and pos in graph and _text_key(graph[pos]):
            return pos
    enc = [nid for nid, n in graph.items() if "encode" in str(n.get("class_type", "")).lower() and _text_key(n)]
    return enc[0] if enc else None


def fill_workflow(graph: dict, prompt: str, width: int, height: int, seed: int, prefix: str) -> dict:
    g = json.loads(json.dumps(graph))
    nid = prompt_node(g)
    if not nid:
        raise ToolError("couldn't find the prompt in this ComfyUI workflow (no text-encode node with a prompt/text input)")
    g[nid]["inputs"][_text_key(g[nid])] = prompt
    for node in g.values():
        ins, cls = node.get("inputs") or {}, str(node.get("class_type", ""))
        for k in ("seed", "noise_seed"):
            if isinstance(ins.get(k), int):
                ins[k] = seed
        if "latent" in cls.lower() and "empty" in cls.lower() and isinstance(ins.get("width"), int):
            ins["width"], ins["height"] = width, height
        if cls == "SaveImage":
            ins["filename_prefix"] = f"universal-modder/{prefix}"
    return g


def _is_txt2img(graph: dict) -> bool:
    classes = {str(n.get("class_type", "")) for n in graph.values()}
    return "SaveImage" in classes and prompt_node(graph) is not None and "LoadImage" not in classes


def t_comfy_status():
    cfg = load_config()
    t = None
    try:
        d = json.loads(comfy_template_path().read_text())
        g = d["graph"]
        t = dict(source=d.get("source"), saved=d.get("saved"), nodes=sorted({n.get("class_type") for n in g.values()}),
                 prompt=(g[prompt_node(g)]["inputs"][_text_key(g[prompt_node(g)])][:200] if prompt_node(g) else None))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return dict(url=cfg["comfy_url"], running=Comfy(cfg["comfy_url"]).ok(), template=t)


def _save_template(graph: dict, source: str):
    comfy_template_path().write_text(json.dumps(dict(graph=graph, source=source, saved=dt.datetime.now().isoformat(timespec="seconds")), indent=1))


def t_comfy_use_last():
    hist = Comfy(load_config()["comfy_url"]).history()
    items = sorted(hist.values(), key=lambda h: -((h.get("prompt") or [0])[0] or 0))
    for h in items:
        graph = (h.get("prompt") or [None, None, None])[2]
        if isinstance(graph, dict) and _is_txt2img(graph) and (h.get("status") or {}).get("status_str", "success") == "success":
            _save_template(graph, "the last text-to-image job in ComfyUI's history")
            return t_comfy_status()
    raise ToolError("no finished text-to-image job in ComfyUI's history. Make one image the way you normally do "
                    "(your ComfyUI page), then try again. History resets when ComfyUI restarts.")


def t_comfy_load_workflow(path: str):
    p = _path(path)
    try:
        graph = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ToolError(f"can't read {p}: {e}")
    if "nodes" in graph and "links" in graph:
        raise ToolError("that's a UI workflow; in ComfyUI use Workflow > Export (API) and pick that file instead")
    if not isinstance(graph, dict) or prompt_node(graph) is None:
        raise ToolError("no prompt node found in that workflow")
    _save_template(graph, p.name)
    return t_comfy_status()


def _unique(folder: Path, stem: str, ext: str = ".png") -> Path:
    stem = re.sub(r"[^\w\- ]+", "", stem).strip().replace(" ", "_")[:60] or "art"
    p, n = folder / f"{stem}{ext}", 1
    while p.exists():
        n += 1
        p = folder / f"{stem}_{n}{ext}"
    return p


def t_generate_image(prompt: str, name: str = "", style: str = "item", size: str = "1024x1024", folder: str = ""):
    cfg = load_config()
    try:
        tpl = json.loads(comfy_template_path().read_text())["graph"]
    except (OSError, ValueError, KeyError):
        raise ToolError("no ComfyUI workflow set up yet: open the Art screen and click 'Use my last ComfyUI image'")
    w, _, h = size.lower().partition("x")
    try:
        width, height = int(w), int(h or w)
    except ValueError:
        width = height = 1024
    width, height = (max(256, min(2048, v)) // 16 * 16 for v in (width, height))
    comfy = Comfy(cfg["comfy_url"])
    if not comfy.ok():
        raise ToolError(f"ComfyUI isn't running at {cfg['comfy_url']}: start it (ComfyUI.bat) and keep its window open")
    if cfg["free_vram"] and cfg["model"]:
        Ollama(cfg["ollama_url"]).unload(cfg["model"])        # 8 GB cards can't hold the chat model and the image model
    full = prompt.strip() + ART_STYLES.get(style, "")
    stem = name or "_".join(re.sub(r"[^a-z0-9 ]", "", prompt.lower()).split()[:4]) or "art"
    graph = fill_workflow(tpl, full, width, height, secrets.randbelow(2**31), re.sub(r"[^\w\-]+", "_", stem)[:40])
    t0 = time.time()
    try:
        imgs = comfy.run(graph)
    finally:
        if cfg["free_vram"]:
            comfy.free()
    if not imgs:
        raise ToolError("ComfyUI finished but saved no image")
    out = _path(folder) if folder else _workspace() / "art"
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for img in imgs:
        dst = _unique(out, stem, Path(img["filename"]).suffix or ".png")
        dst.write_bytes(comfy.image(img))
        files.append(str(dst))
    return dict(files=files, seconds=round(time.time() - t0), size=f"{width}x{height}", prompt=full)


def t_make_sprite(image: str, size: str = "", pixel_art: str = "yes", colors: str = "24", cut_out: str = "yes"):
    src = _path(image)
    if not src.is_file():
        raise ToolError(f"no such image: {src}")
    yes = lambda v: str(v).strip().lower() not in ("no", "false", "0", "off", "")
    cur, steps = src, []
    stem = src.stem
    if yes(cut_out):
        cut = src.with_name(f"{stem}_cut.png")
        run_um(["sprite", "cutout", cur, cut])
        cur, steps = cut, steps + ["background removed"]
    if size.strip():
        out = src.with_name(f"{stem}_sprite_{size.strip().lower()}.png")
        if yes(pixel_art):
            run_um(["sprite", "pixelate", cur, out, "--size", size.strip(), "--colors", str(int(colors or 0)), "--outline"])
            steps.append(f"pixelated to {size} with {colors} colours")
        else:
            run_um(["sprite", "fit", cur, out, "--size", size.strip(), "--smooth"])
            steps.append(f"fitted to {size}")
        cur = out
    return dict(output=str(cur), steps=steps or ["nothing to do"])


def t_list_art():
    folder = _workspace() / "art"
    if not folder.is_dir():
        return []
    files = sorted((p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXT), key=lambda p: -p.stat().st_mtime)[:120]
    return [dict(name=p.name, path=str(p), bytes=p.stat().st_size, modified=p.stat().st_mtime) for p in files]


# --------------------------------------------------------------------------- the games you own

_GAMES = dict(at=0.0, names=[])


def owned_games(max_age: float = 600) -> list[str]:
    """Installed game names for the system prompt, cached so a chat turn doesn't rescan every time."""
    if time.time() - _GAMES["at"] > max_age:
        try:
            _GAMES["names"] = sorted({g.get("name") or Path(g["path"]).name for g in t_list_games()}, key=str.lower)
        except (ToolError, KeyError, TypeError):
            _GAMES["names"] = []
        _GAMES["at"] = time.time()
    return _GAMES["names"]


S, I = "string", "integer"
TOOLS = {
    # name: (function, description, {param: (type, description)}, required, needs the user's approval in chat)
    "list_games": (t_list_games, "List the games installed on this PC (Steam, Epic, Xbox) with their install folders.", {}, [], False),
    "scan_game": (t_scan_game, "Fingerprint one game: engine and version, anti-cheat, installed mod loaders, save folders, "
                               "ranked modding routes and which playbook to read. Always do this before modding a game.",
                  {"game": (S, "game name (fuzzy) or its install folder")}, ["game"], False),
    "kb_search": (t_kb_search, "Search the knowledge base of field notes on how games were modded before (exact versions, routes, gotchas).",
                  {"query": (S, "words to search for, e.g. a game or engine name"), "game": (S, "optional: only notes about this game")},
                  ["query"], False),
    "kb_show": (t_kb_show, "Read one knowledge-base note in full.", {"note": (S, "the note's path from kb_search")}, ["note"], False),
    "read_guide": (t_read_guide, "Read a modding guide: 'mod-any-game' (the overall method), 'game-recon', 'reverse-engineering', "
                                 "'publish-mod', 'safety', or an engine playbook such as 'engines/unity', 'engines/unreal', "
                                 "'engines/dotnet-xna', 'engines/bethesda', 'engines/godot', 'engines/source', 'engines/minecraft'.",
                   {"name": (S, "guide name")}, ["name"], False),
    "list_files": (t_list_files, "List a folder's files and subfolders (read-only). Relative paths are inside the workspace.",
                   {"path": (S, "folder path")}, ["path"], False),
    "read_file": (t_read_file, "Read a text file (read-only, up to 30,000 characters).", {"path": (S, "file path")}, ["path"], False),
    "write_file": (t_write_file, "Create or overwrite a text file (mod code, configs, manifests). Relative paths go into the workspace "
                                 "folder; writing anywhere else asks the user first. Never write into the game's own install files.",
                   {"path": (S, "file path"), "content": (S, "the full file content")}, ["path", "content"], "outside-workspace"),
    "run_command": (t_run_command, "Run a shell command, e.g. a build (`dotnet build`). The user must approve every command.",
                    {"command": (S, "the command line"), "folder": (S, "working folder (default: the workspace)")}, ["command"], True),
    "backup_list": (t_backup_list, "List the save backups (snapshots) made so far.", {}, [], False),
    "backup_create": (t_backup_create, "Snapshot a folder (usually the game's save folder from scan_game) before anything changes it.",
                      {"folder": (S, "folder to back up"), "name": (S, "short backup name, e.g. 'terraria-saves'"), "note": (S, "optional note")},
                      ["folder"], False),
    "backup_diff": (t_backup_diff, "Show what changed in a backed-up folder since its latest snapshot.", {"name": (S, "backup name")}, ["name"], False),
    "backup_restore": (t_backup_restore, "Restore a backup over the folder it came from (the current state is snapshotted first). Asks the user first.",
                       {"name": (S, "backup name"), "snapshot": (S, "optional: a specific snapshot file")}, ["name"], True),
    "publish_check": (t_publish_check, "Check a mod folder before sharing it: copied game files, decompiled code, leaked keys, missing README.",
                      {"folder": (S, "the mod folder"), "game": (S, "optional: the game's install folder, to catch copied game files")},
                      ["folder"], False),
    "generate_image": (t_generate_image, "Make a picture with the user's ComfyUI (3-6 minutes each on a small GPU, so ask before making "
                                         "several). style: 'item' (one object on a plain background, for sprites and icons), "
                                         "'character' (full body, T-pose), 'texture' (seamless) or 'none'. Saves into the workspace's art folder.",
                       {"prompt": (S, "what to draw, in plain words"), "name": (S, "short file name, e.g. 'golden_hoe'"),
                        "style": (S, "item, character, texture or none"), "size": (S, "1024x1024 (default) or 768x768 (faster)")},
                       ["prompt"], False),
    "make_sprite": (t_make_sprite, "Turn an image into a game sprite: remove its plain background, then scale it to the game's exact size. "
                                   "pixel_art 'yes' pixelates with a small palette (Terraria, Stardew...), 'no' scales smoothly (HD games).",
                    {"image": (S, "image path, e.g. from generate_image"), "size": (S, "target size like 32x32; empty = only remove the background"),
                     "pixel_art": (S, "yes or no"), "colors": (S, "palette size for pixel art, e.g. 16")}, ["image"], False),
    # used by the app's screens, not offered to the AI
    "list_art": (t_list_art, "Images in the workspace's art folder.", {}, [], False),
    "comfy_status": (t_comfy_status, "ComfyUI connection and the saved workflow.", {}, [], False),
    "comfy_use_last": (t_comfy_use_last, "Save ComfyUI's last text-to-image job as the workflow to use.", {}, [], False),
    "comfy_load_workflow": (t_comfy_load_workflow, "Load an API-format workflow file.", {"path": (S, "the .json file")}, ["path"], False),
}
SCREEN_ONLY = {"list_art", "comfy_status", "comfy_use_last", "comfy_load_workflow"}


def tool_schemas() -> list[dict]:
    out = []
    for name, (_, desc, params, required, _) in TOOLS.items():
        if name in SCREEN_ONLY:
            continue
        props = {k: {"type": t, "description": d} for k, (t, d) in params.items()}
        out.append({"type": "function", "function": {"name": name, "description": desc,
                                                       "parameters": {"type": "object", "properties": props, "required": required}}})
    return out


def call_tool(name: str, args: dict):
    if name not in TOOLS:
        raise ToolError(f"unknown tool {name!r}; available: {', '.join(TOOLS)}")
    fn, _, params, required, _ = TOOLS[name]
    # small models sometimes send numbers or null for string arguments
    args = {k: v if isinstance(v, str) else "" if v is None else json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            for k, v in (args or {}).items() if k in params}
    missing = [k for k in required if k != "content" and not args.get(k, "").strip()]
    if missing:
        raise ToolError(f"missing argument(s): {', '.join(missing)}")
    return fn(**args)


def needs_approval(name: str, args: dict) -> bool:
    rule = TOOLS[name][4] if name in TOOLS else False
    if rule == "outside-workspace":
        return not _inside(_path(args.get("path", "")), _workspace())
    return bool(rule)


def as_text(result, limit: int = MAX_TOOL_CHARS) -> str:
    s = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, separators=(",", ":"), default=str)
    return s if len(s) <= limit else s[:limit] + f"\n... ({len(s) - limit:,} more characters cut)"


def result_limit(num_ctx: int) -> int:
    """Keep one tool result to about a quarter of the context (roughly 3.5 characters per token)."""
    return max(2000, min(MAX_TOOL_CHARS, int(num_ctx * 0.9)))


# --------------------------------------------------------------------------- the chat (Ollama)

def os_name() -> str:
    if is_windows():
        return f"Windows {platform.release()}"
    if is_wsl():
        return "Linux under WSL (games run on the Windows side)"
    return "macOS" if is_mac() else platform.system()


TEXT_TOOLS = """
## Using tools
You can't run anything yourself: you ask the app to run a tool. To use one, reply with exactly this and nothing else:
<tool>{"name": "scan_game", "arguments": {"game": "Terraria"}}</tool>
One tool per reply. The app answers with <tool_result>; read it, then either use another tool or, when you're done,
answer the user normally (no <tool> tag). Never make up tool results. Arguments marked ? are optional.

Tools:
"""


def text_tools_prompt() -> str:
    lines = []
    for name, (_, desc, params, required, _) in TOOLS.items():
        if name not in SCREEN_ONLY:
            lines.append(f"- {name}({', '.join(k + ('' if k in required else '?') for k in params)}): {desc}")
    return TEXT_TOOLS + "\n".join(lines)


def system_prompt(text_tools: bool = False) -> str:
    games = owned_games()
    owned = (f"Games installed on this PC (the user owns these): {', '.join(games[:80])}." if games
             else "No Steam/Epic/Xbox games were found; ask the user for the game's install folder.")
    art = ("Art: generate_image makes pictures with the user's ComfyUI; make_sprite turns one into a game-ready sprite."
           if comfy_template_path().exists() else
           "Art: ComfyUI isn't set up in the app yet; the user can do it on the Art screen.")
    prompt = f"""You are Universal Modder, an assistant that mods PC games the user owns. You run on the user's own computer and act through tools.
Computer: {os_name()}. Workspace folder for new mod files: {_workspace()}. Today: {dt.date.today().isoformat()}.
{owned}
{art}

How to work:
1. Find the game: scan_game gives the engine, anti-cheat, mod loaders, save folders and the best route.
   Asked what could be added to their games? Suggest a few mods that fit each game's route.
2. Search earlier notes: kb_search with the game or engine name; read useful hits with kb_show.
3. Read the method and the playbook for the route: read_guide("mod-any-game") and the engine playbook, e.g. read_guide("engines/unity").
4. Before anything changes the game or its saves, back up the save folder from the scan with backup_create.
5. Build the smallest working version first (one item, one change). Write the files with write_file, and tell the user
   exactly how to load and test it in the game. Build with run_command when the route needs it. Make its art with
   generate_image + make_sprite when art is set up.
6. Before the user shares a mod, run publish_check on its folder.

Rules (from the toolkit's safety guide):
- Only games the user owns, single-player or offline. Never mod an online game protected by anti-cheat, never write
  multiplayer cheats, never bypass anti-cheat, DRM or ownership checks.
- Never copy game files or decompiled game code into a mod. Never write into the game's own install files.
- Some tools ask the user first. If the user denies one, do not retry it; ask what they want instead.

Be concise and practical. Use the tools instead of guessing paths, versions or engines. Reply in the user's language."""
    return prompt + ("\n" + text_tools_prompt() if text_tools else "")


class Ollama:
    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def _open(self, path: str, body=None, timeout: float = 10):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method="POST" if data else "GET",
                                     headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=timeout)

    def models(self) -> list[dict]:
        with self._open("/api/tags", timeout=5) as r:
            ms = json.load(r).get("models", [])
        return [dict(name=m.get("name"), size=m.get("size"), family=(m.get("details") or {}).get("family"),
                     params=(m.get("details") or {}).get("parameter_size")) for m in ms]

    def capabilities(self, model: str) -> list[str] | None:
        """What the model can do (Ollama reports e.g. ["completion", "tools", "vision"]); None if unknown."""
        try:
            with self._open("/api/show", {"model": model}, timeout=10) as r:
                caps = json.load(r).get("capabilities")
            return caps if isinstance(caps, list) else None
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def unload(self, model: str):
        """Free the GPU memory the model holds (it reloads by itself on the next chat)."""
        try:
            self._open("/api/generate", {"model": model, "keep_alive": 0}, timeout=30).close()
        except (urllib.error.URLError, OSError):
            pass

    def chat(self, model: str, messages: list[dict], tools: list[dict] | None, num_ctx: int):
        """Yields the streamed chunks' messages."""
        body = dict(model=model, messages=messages, stream=True, options=dict(num_ctx=num_ctx))
        if tools:
            body["tools"] = tools
        try:
            r = self._open("/api/chat", body, timeout=900)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            try:
                detail = json.loads(detail).get("error", detail)
            except ValueError:
                pass
            raise ToolError(f"Ollama: {detail}")
        except (urllib.error.URLError, OSError) as e:
            raise ToolError(f"can't reach Ollama at {self.url} ({getattr(e, 'reason', e)}). Is it running? Start it, or fix the URL in Settings.")
        with r:
            for line in r:
                if not line.strip():
                    continue
                d = json.loads(line)
                if d.get("error"):
                    raise ToolError(f"Ollama: {d['error']}")
                yield d.get("message") or {}, d.get("done", False)


class Approvals:
    def __init__(self):
        self.lock = threading.Lock()
        self.pending: dict[str, dict] = {}

    def ask(self, timeout: float = 900) -> tuple[str, threading.Event, dict]:
        aid = secrets.token_hex(6)
        slot = dict(ok=False)
        ev = threading.Event()
        with self.lock:
            self.pending[aid] = dict(event=ev, slot=slot)
        return aid, ev, slot

    def answer(self, aid: str, ok: bool) -> bool:
        with self.lock:
            p = self.pending.pop(aid, None)
        if not p:
            return False
        p["slot"]["ok"] = bool(ok)
        p["event"].set()
        return True


APPROVALS = Approvals()


TOOL_MARK = re.compile(r"<tool|```|\{\s*\"(?:name|tool)\"")
_MODES: dict[tuple, str] = {}


def parse_text_call(text: str):
    """A tool call written as text: <tool>{...}</tool>, a ```json block or a bare {"name": ...} object.
    Returns (text before it, name, arguments) or None."""
    for m in TOOL_MARK.finditer(text):
        start = text.find("{", m.start())
        if start < 0:
            continue
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[start:])
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("name") or obj.get("tool") or obj.get("function")
        args = obj.get("arguments", obj.get("args", obj.get("parameters", {})))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        if isinstance(name, str) and name in TOOLS and name not in SCREEN_ONLY:
            return text[:m.start()].rstrip(), name, args if isinstance(args, dict) else {}
    return None


def tool_mode(llm: "Ollama", cfg: dict) -> str:
    """native (the model's own tool calling) or text (tools described in the prompt, for models like Gemma 3)."""
    if cfg.get("tool_mode") in ("native", "text"):
        return cfg["tool_mode"]
    key = (llm.url, cfg["model"])
    if key not in _MODES:
        caps = llm.capabilities(cfg["model"])
        _MODES[key] = "text" if caps is not None and "tools" not in caps else "native"
    return _MODES[key]


def run_tool(name: str, args: dict, emit, limit: int) -> str:
    """Run one tool call from the model, asking the user first where needed. Returns the text for the model."""
    cid = secrets.token_hex(4)
    emit(dict(type="tool", id=cid, name=name, args=args))
    if name in SCREEN_ONLY:
        result = f"error: unknown tool {name!r}"
        emit(dict(type="tool_result", id=cid, name=name, ok=False, text=result))
        return result
    if name in TOOLS and needs_approval(name, args):
        aid, ev, slot = APPROVALS.ask()
        emit(dict(type="approve", id=cid, approval=aid, name=name, args=args))
        ok = ev.wait(900) and slot["ok"]
        APPROVALS.answer(aid, False)          # drop it if it timed out
        emit(dict(type="approved", id=cid, ok=ok))
        if not ok:
            result = "The user denied this. Don't retry it; ask them what to do instead."
            emit(dict(type="tool_result", id=cid, name=name, ok=False, text=result))
            return result
    try:
        result, okay = as_text(call_tool(name, args), limit), True
    except ToolError as e:
        result, okay = f"error: {e}", False
    except Exception as e:  # a tool bug must not end the conversation
        result, okay = f"error: {type(e).__name__}: {e}", False
    emit(dict(type="tool_result", id=cid, name=name, ok=okay, text=result[:4000]))
    return result


def chat_turn(history: list[dict], emit, cfg: dict | None = None):
    """One user turn: call the model, run its tool calls (asking for approval where needed), repeat.
    `emit(event)` streams progress to the window; returns the new messages to append to the history."""
    cfg = cfg or load_config()
    if not cfg.get("model"):
        raise ToolError("no model chosen: open Settings and pick an Ollama model")
    llm = Ollama(cfg["ollama_url"])
    mode = tool_mode(llm, cfg)
    limit, ctx = result_limit(int(cfg["num_ctx"])), int(cfg["num_ctx"])
    past = [m for m in history if m.get("role") != "system"]
    new: list[dict] = []
    emit(dict(type="mode", mode=mode))
    for _ in range(MAX_STEPS):
        msgs = [{"role": "system", "content": system_prompt(text_tools=mode == "text")}] + past + new
        text, calls, shown = "", [], 0
        try:
            for m, _done in llm.chat(cfg["model"], msgs, tool_schemas() if mode == "native" else None, ctx):
                if m.get("thinking"):
                    emit(dict(type="thinking"))
                if m.get("content"):
                    text += m["content"]
                    if mode == "native":
                        emit(dict(type="delta", text=m["content"]))
                    else:                      # hold back anything that may be the start of a tool call
                        mk = TOOL_MARK.search(text, shown)
                        safe = mk.start() if mk else max(shown, len(text) - 12)
                        if safe > shown:
                            emit(dict(type="delta", text=text[shown:safe]))
                            shown = safe
                calls += m.get("tool_calls") or []
        except ToolError as e:
            if mode == "native" and not text and "does not support tools" in str(e):
                mode = _MODES[(llm.url, cfg["model"])] = "text"      # e.g. Gemma 3: describe the tools instead
                emit(dict(type="mode", mode=mode))
                continue
            raise
        if mode == "text":
            call = parse_text_call(text)
            visible = call[0] if call else text
            if len(visible) > shown:
                emit(dict(type="delta", text=visible[shown:]))
            new.append({"role": "assistant", "content": text})
            if not call:
                return new
            result = run_tool(call[1], call[2], emit, limit)
            new.append({"role": "user", "content": f'<tool_result name="{call[1]}">\n{result}\n</tool_result>'})
            continue
        msg = {"role": "assistant", "content": text}
        if calls:
            msg["tool_calls"] = calls
        new.append(msg)
        if not calls:
            return new
        for c in calls:
            fn = c.get("function") or {}
            name, args = fn.get("name", ""), fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except ValueError:
                    args = {}
            new.append({"role": "tool", "tool_name": name, "content": run_tool(name, args, emit, limit)})
    new.append({"role": "assistant", "content": f"(Stopped after {MAX_STEPS} steps. Say 'continue' to go on.)"})
    emit(dict(type="delta", text=new[-1]["content"]))
    return new


# --------------------------------------------------------------------------- the server

CTYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
          ".svg": "image/svg+xml", ".png": "image/png", ".ttf": "font/ttf", ".ico": "image/x-icon", ".jpg": "image/jpeg",
          ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}


class App:
    def __init__(self, port: int = 0, token: str | None = None):
        self.token = token or secrets.token_urlsafe(24)
        self.last_seen = 0.0
        self.bye_at = 0.0
        self.busy = 0
        self.busy_lock = threading.Lock()
        app = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "UniversalModder"

            def log_message(self, *a):
                pass

            def _send(self, code: int, body: bytes, ctype: str = "application/json"):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)

            def _json(self, obj, code: int = 200):
                self._send(code, json.dumps(obj, default=str).encode())

            def _allowed(self) -> bool:
                host = self.headers.get("Host", "")
                port = self.server.server_address[1]
                if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                    return False
                origin = self.headers.get("Origin")
                return not origin or origin in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")

            def _authed(self) -> bool:
                return hmac.compare_digest(self.headers.get("X-UM-Token", ""), app.token)

            def do_GET(self):
                if not self._allowed():
                    return self._send(403, b"forbidden", "text/plain")
                path, _, query = self.path.partition("?")
                if path == "/api/file":
                    return self._file(urllib.parse.parse_qs(query))
                if path.startswith("/api/"):
                    if not self._authed():
                        return self._json({"error": "bad token"}, 401)
                    return self._api_get(path)
                if path == "/":
                    path = "/index.html"
                base, rel = (FONTS, path[len("/fonts/"):]) if path.startswith("/fonts/") else (UI, path.lstrip("/"))
                f = (base / rel).resolve()
                if not _inside(f, base) or not f.is_file():
                    return self._send(404, b"not found", "text/plain")
                self._send(200, f.read_bytes(), CTYPES.get(f.suffix, "application/octet-stream"))

            def do_POST(self):
                if not self._allowed():
                    return self._send(403, b"forbidden", "text/plain")
                path, _, query = self.path.partition("?")
                if path == "/api/bye" and hmac.compare_digest(query, "t=" + app.token):
                    app.bye_at = time.time()            # sendBeacon from a closing (or reloading) window
                    return self._json({"ok": True})
                if not self._authed():
                    return self._json({"error": "bad token"}, 401)
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                    body = json.loads(self.rfile.read(n) or b"{}") if n else {}
                except ValueError:
                    return self._json({"error": "bad JSON"}, 400)
                app.last_seen = time.time()
                if path == "/api/chat":
                    return self._chat(body)
                if path == "/api/tool":
                    if body.get("name") in ("run_command", "write_file"):   # only the chat runs these, behind Allow
                        return self._json({"ok": False, "error": "not available from the buttons"})
                    try:
                        return self._json({"ok": True, "result": call_tool(body.get("name", ""), body.get("args") or {})})
                    except ToolError as e:
                        return self._json({"ok": False, "error": str(e)})
                    except Exception as e:
                        return self._json({"ok": False, "error": f"{type(e).__name__}: {e}"})
                if path == "/api/approve":
                    return self._json({"ok": APPROVALS.answer(str(body.get("approval", "")), bool(body.get("ok")))})
                if path == "/api/config":
                    try:
                        _MODES.clear()                  # a new model or tool mode: decide again
                        return self._json({"ok": True, "config": save_config(body)})
                    except (ValueError, OSError) as e:
                        return self._json({"ok": False, "error": str(e)})
                if path == "/api/pick-folder":
                    return self._json(pick_folder(body.get("title") or "Choose a folder"))
                if path == "/api/pick-file":
                    return self._json(pick_folder(body.get("title") or "Choose a file", file=True))
                if path == "/api/open-folder":
                    return self._json(open_folder(body.get("path", "")))
                self._json({"error": "unknown endpoint"}, 404)

            def _file(self, q):
                """An image from the workspace, for previews in the window."""
                if not hmac.compare_digest((q.get("t") or [""])[0], app.token):
                    return self._send(401, b"bad token", "text/plain")
                f = _path((q.get("path") or [""])[0])
                if f.suffix.lower() not in IMAGE_EXT or not f.is_file() or not _inside(f, _workspace()):
                    return self._send(404, b"not found", "text/plain")
                self._send(200, f.read_bytes(), CTYPES.get(f.suffix.lower(), "image/png"))

            def _api_get(self, path):
                app.last_seen = time.time()
                if path == "/api/ping":
                    return self._json({"ok": True})
                if path == "/api/status":
                    cfg = load_config()
                    llm = Ollama(cfg["ollama_url"])
                    try:
                        models, err = llm.models(), None
                    except (urllib.error.URLError, OSError, ValueError) as e:
                        models, err = [], str(getattr(e, "reason", e))
                    mode = tool_mode(llm, cfg) if cfg["model"] and err is None else None
                    return self._json(dict(version=__version__, os=os_name(), windows=is_windows() or is_wsl(), config=cfg,
                                           ollama=dict(ok=err is None, error=err, models=models, tool_mode=mode),
                                           comfy=dict(running=Comfy(cfg["comfy_url"]).ok(), template=comfy_template_path().exists()),
                                           tools=list(TOOLS)))
                self._json({"error": "unknown endpoint"}, 404)

            def _chat(self, body):
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.close_connection = True
                lock = threading.Lock()

                def emit(ev):
                    with lock:
                        self.wfile.write((json.dumps(ev, default=str) + "\n").encode())
                        self.wfile.flush()
                    app.last_seen = time.time()

                with app.busy_lock:
                    app.busy += 1
                try:
                    msgs = [m for m in body.get("messages") or [] if isinstance(m, dict) and m.get("role") in ("user", "assistant", "tool")]
                    emit(dict(type="done", messages=chat_turn(msgs, emit)))
                except ToolError as e:
                    try:
                        emit(dict(type="error", message=str(e)))
                    except OSError:
                        pass
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass                                   # the user pressed Stop / closed the window
                except Exception as e:
                    try:
                        emit(dict(type="error", message=f"{type(e).__name__}: {e}"))
                    except OSError:
                        pass
                finally:
                    with app.busy_lock:
                        app.busy -= 1

        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/?t={self.token}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def pick_folder(title: str, file: bool = False) -> dict:
    """A native folder (or file) dialog (tkinter), for the Browse buttons. Falls back to typing the path."""
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = (filedialog.askopenfilename(title=title, parent=root, filetypes=[("Workflow", "*.json"), ("All files", "*.*")]) if file
                else filedialog.askdirectory(title=title, mustexist=True, parent=root))
        root.destroy()
        return {"ok": True, "path": str(Path(path)) if path else ""}
    except Exception as e:  # no display / no tkinter
        return {"ok": False, "error": f"no folder dialog here ({type(e).__name__}); type the path instead"}


def open_folder(path: str) -> dict:
    p = _path(path)
    if not p.exists():
        return {"ok": False, "error": f"not found: {p}"}
    if is_windows():
        os.startfile(str(p))  # noqa: S606 - opens Explorer on a folder the user picked
    elif is_mac():
        subprocess.Popen(["open", str(p)])
    elif shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", str(p)])
    else:
        return {"ok": False, "error": "no file manager found"}
    return {"ok": True}


# --------------------------------------------------------------------------- the window

def app_browser() -> str | None:
    """Edge or Chrome, which can show a page as its own app window (--app)."""
    cands = []
    if is_windows():
        for env in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                cands += [Path(base) / "Microsoft/Edge/Application/msedge.exe", Path(base) / "Google/Chrome/Application/chrome.exe"]
    elif is_mac():
        cands += [Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                  Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    elif not is_wsl():
        cands += [Path(p) for p in map(shutil.which, ("microsoft-edge", "google-chrome", "chromium", "chromium-browser")) if p]
    return next((str(c) for c in cands if c.is_file()), None)


def open_window(app: App):
    """Show the app. Returns a function that tells whether the window's browser process has exited, or None
    when the window was native (pywebview) and has already been closed."""
    try:
        import webview  # optional: `pip install pywebview` gives a native window; start() blocks until it closes
        webview.create_window("Universal Modder", app.url, width=1320, height=860, min_size=(900, 600))
        webview.start()
        return None
    except ImportError:
        pass
    exe = app_browser()
    if exe:
        profile = data_dir() / "app-window"
        proc = subprocess.Popen([exe, f"--app={app.url}", f"--user-data-dir={profile}", "--window-size=1320,860",
                                 "--no-first-run", "--no-default-browser-check", "--disable-features=Translate"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return lambda: proc.poll() is not None
    import webbrowser
    webbrowser.open(app.url)
    return lambda: True


def serve_until_closed(app: App, browser_gone):
    """Keep running while the window is open. The page pings every few seconds (a minimised window pings slower)
    and says bye when it closes; a reload says bye and pings again right after."""
    started = time.time()
    while True:
        time.sleep(1)
        now = time.time()
        if app.busy:
            continue
        if not app.last_seen:
            if browser_gone() and now - started > 180:
                print("the window never connected; closing. Run `um app --no-window` and open the URL it prints.")
                return
            continue
        if app.bye_at > app.last_seen and now - app.bye_at > 8:
            return
        if browser_gone() and now - app.last_seen > 150:
            return


# --------------------------------------------------------------------------- CLI

def self_test() -> int:
    app = App().start()
    base = f"http://127.0.0.1:{app.port}"
    results, ok = {}, True

    def call(path, body=None, token=app.token):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"X-UM-Token": token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, {}

    try:
        code, st = call("/api/status")
        results["status"] = dict(code=code, version=st.get("version"), ollama=st.get("ollama", {}).get("ok"))
        ok &= code == 200 and st.get("version") == __version__
        code, _ = call("/api/status", token="wrong")
        results["rejects_bad_token"] = code == 401
        ok &= code == 401
        with urllib.request.urlopen(base + "/", timeout=30) as r:
            results["page"] = r.status == 200 and b"Universal Modder" in r.read()
        ok &= results["page"]
        for name, args, check in [("list_games", {}, lambda r: isinstance(r, list)),
                                  ("kb_search", {"query": "terraria"}, lambda r: isinstance(r, list) and len(r) > 0),
                                  ("read_guide", {"name": "engines/unity"}, lambda r: "Unity" in r),
                                  ("backup_list", {}, lambda r: isinstance(r, list))]:
            _, res = call("/api/tool", {"name": name, "args": args})
            good = bool(res.get("ok")) and check(res.get("result"))
            results[name] = good if good else res.get("error") or "unexpected result"
            ok &= good
    finally:
        app.stop()
    print(json.dumps(dict(ok=bool(ok), **results), indent=1))
    return 0 if ok else 1


def main(a):
    if a.ollama or a.model:
        save_config({k: v for k, v in dict(ollama_url=a.ollama, model=a.model).items() if v})
    if a.self_test:
        raise SystemExit(self_test())
    app = App(port=a.port).start()
    print(f"Universal Modder {__version__} is running at {app.url}")
    if a.no_window:
        print("Open that address in a browser. Press Ctrl+C to quit.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    else:
        print("Closing the app window quits it.")
        try:
            gone = open_window(app)
            if gone is not None:
                serve_until_closed(app, gone)
        except KeyboardInterrupt:
            pass
    app.stop()


def register(sub):
    import argparse
    p = sub.add_parser("app", help="open the desktop app: AI chat (Ollama) + buttons for the tools",
                       description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-window", action="store_true", help="only run the server and print its URL")
    p.add_argument("--port", type=int, default=0, help="fixed port (default: a free one)")
    p.add_argument("--ollama", help="Ollama URL (saved), default http://localhost:11434")
    p.add_argument("--model", help="Ollama model to chat with (saved)")
    p.add_argument("--self-test", action="store_true", help="start the server, call it, print the results and exit")
    p.set_defaults(func=main)
