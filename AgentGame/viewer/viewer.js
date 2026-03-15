let events = [];
let meta = null;
let idx = -1;

function $(id) { return document.getElementById(id); }

function render() {
  $("meta").textContent = meta ? JSON.stringify(meta, null, 2) : "";
  $("cursor").textContent = events.length ? `事件 ${Math.max(0, idx + 1)}/${events.length}` : "无事件";
  $("event").textContent = (idx >= 0 && idx < events.length) ? JSON.stringify(events[idx], null, 2) : "";
}

async function loadReplay(matchId) {
  const res = await fetch(`/v1/matches/${matchId}/replay`);
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  meta = data.match;
  events = data.events || [];
  idx = events.length ? 0 : -1;
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

render();

