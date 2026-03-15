async function main() {
  const updatesEl = document.getElementById("updates");
  try {
    const res = await fetch("/site/updates.json");
    const updates = await res.json();
    updatesEl.innerHTML = "";
    for (const u of updates) {
      const div = document.createElement("div");
      div.className = "update";
      div.innerHTML = `
        <div class="when">${u.date} · ${u.line}</div>
        <div class="what"><strong>${u.title}</strong><div style="opacity:.82;margin-top:4px">${u.detail || ""}</div></div>
      `;
      updatesEl.appendChild(div);
    }
  } catch (e) {
    updatesEl.textContent = "暂无更新（updates.json 读取失败）";
  }
}
main();

