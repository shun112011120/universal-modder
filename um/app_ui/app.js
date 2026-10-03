"use strict";
// Universal Modder app: talks to the local server (um/app.py). Every API call carries the per-launch token.

const TOKEN = new URLSearchParams(location.search).get("t") || "";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
let STATUS = null;

// ------------------------------------------------------------------ helpers

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid instanceof Node ? kid : String(kid));
  return el;
}

async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "X-UM-Token": TOKEN, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401) throw new Error("This window lost its connection to the app. Close it and open the app again.");
  return res.json();
}

async function tool(name, args = {}) {
  const r = await api("/api/tool", { name, args });
  if (!r.ok) throw new Error(r.error || "failed");
  return r.result;
}

function toast(text, kind = "") {
  const t = h("div", { class: `toast ${kind}` }, text);
  $("#toasts").append(t);
  setTimeout(() => t.remove(), kind === "err" ? 9000 : 4500);
}

function confirmBox(title, body, yes = "Yes") {
  const d = $("#confirm");
  $("#confirm-title").textContent = title;
  $("#confirm-body").textContent = body;
  $("#confirm-yes").textContent = yes;
  d.returnValue = "";
  d.showModal();
  return new Promise((res) => d.addEventListener("close", () => res(d.returnValue === "yes"), { once: true }));
}

async function busy(btn, fn) {
  const label = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Working…";
  try { return await fn(); }
  catch (e) { toast(e.message, "err"); }
  finally { btn.disabled = false; btn.textContent = label; }
}

const fmtBytes = (n) => n > 1 << 30 ? (n / 2 ** 30).toFixed(1) + " GB" : n > 1 << 20 ? (n / 2 ** 20).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB";

function fmtStamp(s) {   // 20261003-214512 -> 2026-10-03 21:45
  const m = /^(\d{4})(\d\d)(\d\d)-(\d\d)(\d\d)/.exec(s || "");
  return m ? `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}` : s || "";
}

// Small, safe Markdown: everything is escaped first, then a few constructs are re-enabled.
function md(src) {
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, "$1<i>$2</i>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  const out = [];
  const parts = src.split(/^```[^\n]*\n?/m);
  parts.forEach((part, i) => {
    if (i % 2) { out.push(`<pre><code>${esc(part.replace(/\n$/, ""))}</code></pre>`); return; }
    let list = null;
    const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
    let para = [];
    const flush = () => { if (para.length) { out.push(`<p>${para.map(inline).join("<br>")}</p>`); para = []; } };
    for (const line of part.split("\n")) {
      let m;
      if (!line.trim()) { flush(); close(); }
      else if ((m = /^(#{1,4})\s+(.*)/.exec(line))) { flush(); close(); out.push(`<h4>${inline(m[2])}</h4>`); }
      else if ((m = /^\s*[-*•]\s+(.*)/.exec(line))) { flush(); if (list !== "ul") { close(); out.push("<ul>"); list = "ul"; } out.push(`<li>${inline(m[1])}</li>`); }
      else if ((m = /^\s*\d+[.)]\s+(.*)/.exec(line))) { flush(); if (list !== "ol") { close(); out.push("<ol>"); list = "ol"; } out.push(`<li>${inline(m[1])}</li>`); }
      else { close(); para.push(line); }
    }
    flush(); close();
  });
  return out.join("");
}

// ------------------------------------------------------------------ navigation + status

function show(view) {
  $$(".nav").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + view));
  if (view === "backups") loadBackups();
  if (view === "settings") fillSettings();
}
$$(".nav").forEach((b) => b.addEventListener("click", () => show(b.dataset.view)));
$("#ollama-status").addEventListener("click", () => show("settings"));

async function refreshStatus() {
  try {
    STATUS = await api("/api/status");
  } catch (e) {
    toast(e.message, "err");
    return;
  }
  $("#version").textContent = `v${STATUS.version} · ${STATUS.os}`;
  const st = $("#ollama-status");
  const cfg = STATUS.config;
  st.classList.toggle("ok", STATUS.ollama.ok && !!cfg.model);
  st.classList.toggle("bad", !STATUS.ollama.ok);
  $(".txt", st).textContent = !STATUS.ollama.ok ? "Ollama not running" : cfg.model ? cfg.model : "Pick a model";
  const key = JSON.stringify([cfg.model, STATUS.ollama.ok, STATUS.ollama.models.map((m) => m.name)]);
  if (key === refreshStatus.key) return;          // don't reset a dropdown the user is in the middle of changing
  refreshStatus.key = key;
  for (const sel of [$("#model-pick"), $("#set-model")]) {
    sel.replaceChildren();
    const names = STATUS.ollama.models.map((m) => m.name);
    if (cfg.model && !names.includes(cfg.model)) names.unshift(cfg.model);
    if (!names.length) sel.append(h("option", { value: "" }, STATUS.ollama.ok ? "No models: run `ollama pull qwen3-coder`" : "Ollama not reachable"));
    else if (!cfg.model) sel.append(h("option", { value: "" }, "Choose a model…"));
    for (const n of names) {
      const m = STATUS.ollama.models.find((x) => x.name === n);
      sel.append(h("option", { value: n, selected: n === cfg.model }, m && m.params ? `${n} (${m.params})` : n));
    }
  }
}

$("#model-pick").addEventListener("change", async (e) => {
  if (!e.target.value) return;
  await api("/api/config", { model: e.target.value });
  await refreshStatus();
  toast(`Chatting with ${e.target.value}`, "ok");
});

// keep the app alive while this window is open; tell it when the window closes
setInterval(() => api("/api/ping").catch(() => {}), 5000);
addEventListener("pagehide", () => navigator.sendBeacon(`/api/bye?t=${encodeURIComponent(TOKEN)}`));

// folder pickers
document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-browse]");
  if (!b) return;
  const r = await api("/api/pick-folder", { title: "Choose a folder" });
  if (r.ok && r.path) $("#" + b.dataset.browse).value = r.path;
  else if (!r.ok) toast(r.error, "err");
});

// ------------------------------------------------------------------ chat

let history = [];
let controller = null;
let pendingApprovals = new Set();
const chatEl = $("#chat");
const promptEl = $("#prompt");

function scrollChat() { chatEl.scrollTop = chatEl.scrollHeight; }

function argSummary(name, args) {
  const v = args.command || args.path || args.game || args.query || args.folder || args.name || args.note || "";
  return typeof v === "string" ? v : JSON.stringify(v);
}

function setSending(on) {
  $("#send").textContent = on ? "Stop" : "Send";
  $("#send").classList.toggle("danger", on);
  $("#send").classList.toggle("primary", !on);
}

async function send(text) {
  if (controller) return;
  text = text.trim();
  if (!text) return;
  if (!STATUS || !STATUS.config.model) {
    toast("Pick an Ollama model first (Settings).", "err");
    show("settings");
    return;
  }
  $("#welcome")?.remove();
  chatEl.append(h("div", { class: "msg user" }, text));
  history.push({ role: "user", content: text });
  promptEl.value = "";
  autosize();

  const turn = h("div", { class: "msg ai" });
  const typing = h("div", { class: "typing" }, "Thinking");
  turn.append(typing);
  chatEl.append(turn);
  scrollChat();

  let textEl = null, textBuf = "", partial = "";
  const cards = {};
  controller = new AbortController();
  setSending(true);
  try {
    const res = await fetch("/api/chat", {
      method: "POST", signal: controller.signal,
      headers: { "X-UM-Token": TOKEN, "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    if (!res.ok) throw new Error(res.status === 401 ? "Lost the connection to the app; reopen it." : `HTTP ${res.status}`);
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i);
        buf = buf.slice(i + 1);
        if (!line.trim()) continue;
        const ev = JSON.parse(line);
        if (ev.type === "delta") {
          if (!textEl) { textEl = h("div", { class: "md" }); turn.insertBefore(textEl, typing); textBuf = ""; }
          textBuf += ev.text;
          partial += ev.text;
          textEl.innerHTML = md(textBuf);
        } else if (ev.type === "thinking") {
          typing.textContent = "Thinking";
        } else if (ev.type === "tool") {
          textEl = null;
          typing.textContent = "Working";
          const card = h("details", { class: "tool" },
            h("summary", {}, h("span", {}, "🔧"), h("span", { class: "name" }, ev.name), h("span", { class: "arg" }, argSummary(ev.name, ev.args)),
              h("span", { class: "state run" })),
            h("pre", {}, JSON.stringify(ev.args, null, 1)));
          cards[ev.id] = card;
          turn.insertBefore(card, typing);
        } else if (ev.type === "approve") {
          const box = approvalBox(ev);
          cards[ev.id + ":approve"] = box;
          turn.insertBefore(box, typing);
          typing.textContent = "Waiting for you";
        } else if (ev.type === "approved") {
          cards[ev.id + ":approve"]?.remove();
        } else if (ev.type === "tool_result") {
          const card = cards[ev.id];
          if (card) {
            const st = $(".state", card);
            st.className = "state " + (ev.ok ? "ok" : "err");
            st.textContent = ev.ok ? "✓" : /^The user denied/.test(ev.text) ? "denied" : "✗";
            card.append(h("pre", {}, ev.text));
          }
          typing.textContent = "Thinking";
        } else if (ev.type === "done") {
          history.push(...ev.messages);
          partial = "";
        } else if (ev.type === "error") {
          turn.insertBefore(h("div", { class: "error-msg" }, ev.message), typing);
        }
        scrollChat();
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") turn.insertBefore(h("div", { class: "error-msg" }, e.message), typing);
    else turn.insertBefore(h("div", { class: "muted small" }, "Stopped."), typing);
  } finally {
    if (partial) history.push({ role: "assistant", content: partial });   // keep what was said before Stop/error
    for (const a of pendingApprovals) api("/api/approve", { approval: a, ok: false }).catch(() => {});
    pendingApprovals.clear();
    typing.remove();
    controller = null;
    setSending(false);
    scrollChat();
    promptEl.focus();
  }
}

function approvalBox(ev) {
  pendingApprovals.add(ev.approval);
  const what = {
    run_command: ["The AI wants to run a command", `${ev.args.command || ""}${ev.args.folder ? `\n\nin: ${ev.args.folder}` : ""}`],
    backup_restore: ["The AI wants to restore a backup", `backup: ${ev.args.name || ""}${ev.args.snapshot ? `\nsnapshot: ${ev.args.snapshot}` : ""}\n\nThe current files are snapshotted first.`],
    write_file: ["The AI wants to write a file outside your workspace", `${ev.args.path || ""}\n\n${String(ev.args.content || "").slice(0, 1500)}`],
  }[ev.name] || [`The AI wants to use ${ev.name}`, JSON.stringify(ev.args, null, 1)];
  const answer = async (ok) => {
    pendingApprovals.delete(ev.approval);
    box.querySelectorAll("button").forEach((b) => (b.disabled = true));
    await api("/api/approve", { approval: ev.approval, ok });
  };
  const box = h("div", { class: "approve" },
    h("h4", {}, "⚠ " + what[0]),
    h("pre", {}, what[1]),
    h("div", { class: "row" },
      h("button", { class: "btn primary sm", onclick: () => answer(true) }, "Allow"),
      h("button", { class: "btn ghost sm", onclick: () => answer(false) }, "Deny")));
  return box;
}

function autosize() {
  promptEl.style.height = "auto";
  promptEl.style.height = Math.min(promptEl.scrollHeight, 200) + "px";
}

$("#composer").addEventListener("submit", (e) => {
  e.preventDefault();
  if (controller) controller.abort();
  else send(promptEl.value);
});
promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!controller) send(promptEl.value); }
});
promptEl.addEventListener("input", autosize);
$$(".chip").forEach((c) => c.addEventListener("click", () => send(c.textContent)));
$("#new-chat").addEventListener("click", () => {
  if (controller) controller.abort();
  history = [];
  chatEl.replaceChildren(h("div", { class: "welcome", id: "welcome" }, h("h2", {}, "New chat"),
    h("p", { class: "muted" }, "Tell the AI which game you want to mod and what you'd like to add or change.")));
});

function askAI(text) {
  show("chat");
  promptEl.value = text;
  autosize();
  promptEl.focus();
}

// ------------------------------------------------------------------ games

let GAMES = [];

function renderGames() {
  const q = $("#game-filter").value.toLowerCase();
  const list = $("#games-list");
  const rows = GAMES.filter((g) => !q || (g.name || "").toLowerCase().includes(q) || g.path.toLowerCase().includes(q));
  list.className = rows.length ? "" : "empty muted";
  list.replaceChildren(...(rows.length ? rows.map((g) =>
    h("div", { class: "game", onclick: (e) => scanGame(g.path, e.currentTarget) },
      h("span", { class: "store" }, g.store || "folder"),
      h("div", { class: "g-main" }, h("div", { class: "g-name" }, g.name || "?"), h("div", { class: "g-path" }, g.path))))
    : [GAMES.length ? "No game matches the filter." : "No Steam, Epic or Xbox games found. Use “Scan a folder…” for other games."]));
}

$("#find-games").addEventListener("click", (e) => busy(e.target, async () => {
  GAMES = (await tool("list_games")).sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  renderGames();
  toast(`Found ${GAMES.length} game${GAMES.length === 1 ? "" : "s"}`, "ok");
}));
$("#game-filter").addEventListener("input", renderGames);
$("#scan-folder").addEventListener("click", async () => {
  const r = await api("/api/pick-folder", { title: "Choose the game's install folder" });
  if (r.ok && r.path) scanGame(r.path);
  else if (!r.ok) {
    const p = prompt("Game install folder:");
    if (p) scanGame(p);
  }
});

async function scanGame(path, row) {
  $$(".game").forEach((g) => g.classList.toggle("active", g === row));
  const panel = $("#scan-panel");
  panel.replaceChildren(h("div", { class: "empty muted" }, "Scanning… (big games can take a minute)"));
  try {
    renderReport(await tool("scan_game", { game: path }));
  } catch (e) {
    panel.replaceChildren(h("div", { class: "error-msg" }, e.message));
  }
}

function renderReport(r) {
  const e = r.engine;
  const extras = Object.entries(e).filter(([k]) => !["key", "label", "confidence", "evidence"].includes(k));
  const sec = (title, ...kids) => h("div", { class: "sec" }, h("b", {}, title), ...kids);
  const tags = (items, kind, none) => items.length ? items.map((x) => h("span", { class: `tag ${kind}` }, x)) : [h("span", { class: "muted" }, none)];
  const panel = $("#scan-panel");
  panel.replaceChildren(h("div", { class: "report" },
    h("h2", {}, r.name),
    h("div", { class: "path" }, r.path),
    h("div", { class: "row" },
      h("button", { class: "btn primary", onclick: () => askAI(`Help me mod ${r.name}. I'd like to `) }, "Ask the AI to mod this"),
      h("button", { class: "btn ghost", onclick: () => api("/api/open-folder", { path: r.path }).then((x) => x.ok || toast(x.error, "err")) }, "Open folder")),
    ...r.warnings.map((w) => h("div", { class: "warn-box" + (/online|anti-cheat/i.test(w) ? " bad" : "") }, w)),
    sec("Engine", h("div", {}, h("span", { class: "tag accent" }, e.label), ` ${e.confidence}% sure`),
      extras.length ? h("div", { class: "muted small" }, extras.map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ")) : null,
      h("div", { class: "muted small" }, "Evidence: " + e.evidence.join(", "))),
    sec("Anti-cheat", ...tags(r.anti_cheat, "bad", "None found")),
    sec("Mod loaders installed", ...tags(r.mod_loaders_installed, "good", "None yet")),
    r.mod_folders.length ? sec("Mod folders", ...tags(r.mod_folders, "", "")) : null,
    sec("Save folders", ...(r.saves.length ? r.saves.map((s) => h("div", { class: "save-row" }, h("span", { class: "path" }, s),
      h("button", { class: "btn sm", onclick: (ev) => busy(ev.target, async () => {
        toast(await tool("backup_create", { folder: s, name: r.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + "-saves" }), "ok");
      }) }, "Back up"))) : [h("span", { class: "muted" }, "None found automatically")])),
    sec("How to mod it", h("ol", { class: "routes" }, r.routes.map((rt) => h("li", {}, rt.route, h("div", { class: "muted small" }, `${rt.why} · guide: ${rt.playbook}`))))),
  ));
}

// ------------------------------------------------------------------ backups

async function loadBackups() {
  const list = $("#backups-list");
  list.replaceChildren(h("div", { class: "muted" }, "Loading…"));
  let rows;
  try { rows = await tool("backup_list"); }
  catch (e) { list.replaceChildren(h("div", { class: "error-msg" }, e.message)); return; }
  if (!rows.length) { list.replaceChildren(h("div", { class: "panel empty muted" }, "No backups yet.")); return; }
  const groups = {};
  for (const r of rows) (groups[r.name] ||= []).push(r);
  list.replaceChildren(...Object.entries(groups).map(([name, snaps]) => {
    snaps.sort((a, b) => b.file.localeCompare(a.file));
    const diffEl = h("div", { class: "bk-diff" });
    return h("div", { class: "panel bk-group" },
      h("h3", {}, name, h("span", { class: "muted small" }, `${snaps.length} snapshot${snaps.length > 1 ? "s" : ""}`),
        h("span", { class: "acts" },
          h("button", { class: "btn sm", onclick: (e) => busy(e.target, () => showDiff(name, diffEl)) }, "What changed?"),
          h("button", { class: "btn sm danger", onclick: () => restore(name, null, snaps[0]) }, "Restore latest"))),
      h("div", { class: "path muted small" }, snaps[0].source),
      ...snaps.map((s) => h("div", { class: "bk-row" },
        h("span", {}, fmtStamp(s.created || s.file)), h("span", { class: "muted" }, `${s.files} files`), h("span", { class: "muted" }, fmtBytes(s.bytes)),
        h("span", { class: "muted small" }, s.note || ""),
        h("button", { class: "btn sm ghost", onclick: () => restore(name, s.snapshot, s) }, "Restore"))),
      diffEl);
  }));
}

async function showDiff(name, el) {
  const d = await tool("backup_diff", { name });
  const n = d.added.length + d.removed.length + d.changed.length;
  const block = (label, items) => items.length ? h("div", {}, h("b", {}, `${label} (${items.length})`), h("pre", {}, items.slice(0, 300).join("\n"))) : null;
  el.replaceChildren(n ? h("div", {}, block("Changed", d.changed), block("New since the backup", d.added), block("Missing since the backup", d.removed))
    : h("div", { class: "muted" }, "Nothing changed since the latest snapshot."));
}

async function restore(name, snapshot, s) {
  const ok = await confirmBox(`Restore “${name}”?`,
    `This puts the files from ${fmtStamp(s.created || s.file)} back into ${s.source}. The current files are snapshotted first, so you can undo it.`,
    "Restore");
  if (!ok) return;
  try {
    toast(await tool("backup_restore", snapshot ? { name, snapshot } : { name }), "ok");
    loadBackups();
  } catch (e) { toast(e.message, "err"); }
}

$("#refresh-backups").addEventListener("click", loadBackups);
$("#bk-create").addEventListener("click", (e) => busy(e.target, async () => {
  const folder = $("#bk-folder").value.trim();
  if (!folder) throw new Error("Choose a folder to back up.");
  toast(await tool("backup_create", { folder, name: $("#bk-name").value.trim(), note: $("#bk-note").value.trim() }), "ok");
  loadBackups();
}));

// ------------------------------------------------------------------ publish check

$("#pub-run").addEventListener("click", (e) => busy(e.target, async () => {
  const folder = $("#pub-folder").value.trim();
  if (!folder) throw new Error("Choose the mod folder.");
  const r = await tool("publish_check", { folder, game: $("#pub-game").value.trim() });
  const kind = r.passed ? (r.findings.length ? "warn" : "pass") : "fail";
  $("#pub-result").replaceChildren(h("div", { class: "panel", style: "max-width:820px" },
    h("div", { class: `verdict ${kind}` }, { pass: "✓ Ready to share", warn: "⚠ OK, with warnings", fail: "✗ Don't share yet" }[kind]),
    h("div", { class: "muted small" }, r.summary),
    ...r.findings.map((f) => h("div", { class: "finding " + (f.startsWith("FAIL") ? "fail" : "warn") }, f))));
}));

// ------------------------------------------------------------------ settings

function fillSettings() {
  if (!STATUS) return;
  const c = STATUS.config;
  $("#set-url").value = c.ollama_url;
  $("#set-ws").value = c.workspace;
  const ctx = $("#set-ctx");
  if (![...ctx.options].some((o) => +o.value === c.num_ctx)) ctx.append(h("option", { value: c.num_ctx }, `${Math.round(c.num_ctx / 1024)}k`));
  ctx.value = String(c.num_ctx);
  $("#set-msg").textContent = STATUS.ollama.ok ? `Connected · ${STATUS.ollama.models.length} model(s)` : `Can't reach Ollama: ${STATUS.ollama.error}`;
}

async function saveSettings() {
  const r = await api("/api/config", { ollama_url: $("#set-url").value, model: $("#set-model").value, num_ctx: +$("#set-ctx").value, workspace: $("#set-ws").value });
  if (!r.ok) throw new Error(r.error);
  await refreshStatus();
  fillSettings();
}

$("#set-save").addEventListener("click", (e) => busy(e.target, async () => { await saveSettings(); toast("Saved", "ok"); }));
$("#set-test").addEventListener("click", (e) => busy(e.target, async () => {
  await saveSettings();
  toast(STATUS.ollama.ok ? `Ollama is running (${STATUS.ollama.models.length} models)` : `Can't reach Ollama: ${STATUS.ollama.error}`, STATUS.ollama.ok ? "ok" : "err");
}));
$("#set-open-ws").addEventListener("click", async () => {
  const r = await api("/api/open-folder", { path: $("#set-ws").value });
  if (!r.ok) toast(r.error, "err");
});

// ------------------------------------------------------------------ start

refreshStatus().then(() => {
  if (STATUS && (!STATUS.ollama.ok || !STATUS.config.model)) {
    toast(STATUS.ollama.ok ? "Pick a model to chat with (Settings)." : "Ollama isn't running. Start it, or set its address in Settings.", "err");
  }
});
setInterval(refreshStatus, 30000);
promptEl.focus();
