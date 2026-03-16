let events = [];
let meta = null;
let idx = -1;

function $(id) { return document.getElementById(id); }

function shareUrl(matchId) {
  const url = new URL(window.location.href);
  url.searchParams.set("match", matchId);
  return url.toString();
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
}

function renderGridArenaSummary(matchMeta, events, idx) {
  const players = matchMeta.players || [];
  const size = 7;
  const state = {};

  if (players.length >= 1) state[players[0]] = { x: 0, y: 0, hp: 5 };
  if (players.length >= 2) state[players[1]] = { x: size - 1, y: size - 1, hp: 5 };
  for (let i = 2; i < players.length; i++) state[players[i]] = { x: 0, y: 0, hp: 5 };

  for (let i = 0; i <= idx && i < events.length; i++) {
    const e = events[i] || {};
    const agentId = e.agent_id;
    const delta = e.delta || {};
    if (agentId && delta.moved_to && state[agentId]) {
      state[agentId].x = delta.moved_to.x;
      state[agentId].y = delta.moved_to.y;
    }
    if (delta.attack_hit && Array.isArray(delta.attack_hit)) {
      for (const t of delta.attack_hit) {
        if (state[t]) state[t].hp -= 1;
      }
    }
  }

  const grid = Array.from({ length: size }, () => Array.from({ length: size }, () => "."));
  for (const [id, s] of Object.entries(state)) {
    const mark = (id || "?").slice(0, 1).toUpperCase();
    if (Number.isInteger(s.x) && Number.isInteger(s.y) && s.x >= 0 && s.x < size && s.y >= 0 && s.y < size) {
      grid[s.y][s.x] = mark;
    }
  }

  const board = grid.map(row => row.join(" ")).join("\n");
  const hpLines = Object.entries(state).map(([id, s]) => `${id}: HP=${s.hp} @ (${s.x},${s.y})`).join("\n");
  return `Grid Arena (MVP summary)\n\n${board}\n\n${hpLines}`;
}

function renderMiniAuctionSummary(matchMeta, events, idx) {
  const settles = [];
  for (let i = 0; i <= idx && i < events.length; i++) {
    const e = events[i] || {};
    const delta = e.delta || {};
    if (delta.settle) settles.push(delta.settle);
  }
  if (!settles.length) return "Mini Auction (MVP summary)\n\n尚未结算（等待所有人出价）";

  const last = settles[settles.length - 1];
  const lines = ["Mini Auction (MVP summary)", ""];
  lines.push(`settles: ${settles.length}`);
  lines.push("");
  lines.push("history:");
  for (const s of settles) {
    lines.push(`- round ${s.round}: winner=${s.winner} price=${s.price} value=${s.winner_value}`);
  }
  lines.push("");
  lines.push("latest scores:");
  lines.push(JSON.stringify(last.scores, null, 2));
  lines.push("");
  lines.push("latest credits:");
  lines.push(JSON.stringify(last.credits, null, 2));
  return lines.join("\n");
}

function renderSummary() {
  if (!meta) return "";
  const gameId = meta.game_id || meta.gameId || "";
  if (gameId === "grid-arena") return renderGridArenaSummary(meta, events, idx);
  if (gameId === "mini-auction") return renderMiniAuctionSummary(meta, events, idx);
  return "No summary available.";
}

function render() {
  $("meta").textContent = meta ? JSON.stringify(meta, null, 2) : "";
  $("cursor").textContent = events.length ? `事件 ${Math.max(0, idx + 1)}/${events.length}` : "无事件";
  $("event").textContent = (idx >= 0 && idx < events.length) ? JSON.stringify(events[idx], null, 2) : "";
  $("summary").textContent = renderSummary();
}

async function loadReplay(matchId) {
  const res = await fetch(`/v1/matches/${matchId}/replay`);
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  meta = data.match;
  events = data.events || [];
  idx = events.length ? 0 : -1;
  const url = shareUrl(matchId);
  window.history.replaceState({}, "", url);
  render();
}

$("loadBtn").addEventListener("click", async () => {
  const matchId = $("matchId").value.trim();
  if (!matchId) return;
  try { await loadReplay(matchId); } catch (e) { alert(String(e)); }
});

$("prevBtn").addEventListener("click", () => {
  if (!events.length) return;
  idx = Math.max(0, idx - 1);
  render();
});

$("nextBtn").addEventListener("click", () => {
  if (!events.length) return;
  idx = Math.min(events.length - 1, idx + 1);
  render();
});

$("copyBtn").addEventListener("click", async () => {
  const matchId = $("matchId").value.trim();
  if (!matchId) return alert("请先填写 match_id");
  const url = shareUrl(matchId);
  const ok = await copyToClipboard(url);
  if (!ok) return alert(url);
});

// Support deep-link: /viewer/?match=<id>
const params = new URLSearchParams(window.location.search);
const matchFromUrl = (params.get("match") || "").trim();
if (matchFromUrl) {
  $("matchId").value = matchFromUrl;
  loadReplay(matchFromUrl).catch((e) => alert(String(e)));
}

render();
