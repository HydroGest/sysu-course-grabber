const SERVER = "http://127.0.0.1:8124";

function setState(id, ok, text) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.innerHTML = `<span class="dot ${ok ? "ok" : "bad"}"></span>` + text;
}

async function refresh() {
  try {
    const resp = await fetch(SERVER + "/api/health");
    const data = await resp.json();
    setState("serverState", true, "服务已连接");
    setState("cookieState", Boolean(data.cookie), data.cookie ? "Cookie 已同步" : "等待同步");
  } catch (_) {
    setState("serverState", false, "服务未运行");
    setState("cookieState", false, "Cookie 未知");
  }
}

document.getElementById("syncBtn").addEventListener("click", async () => {
  const btn = document.getElementById("syncBtn");
  btn.disabled = true;
  const result = await chrome.runtime.sendMessage({ type: "sync" });
  btn.disabled = false;
  setState("cookieState", Boolean(result && result.ok), result && result.ok ? "Cookie 已同步" : "同步失败");
  await refresh();
});

document.getElementById("openBtn").addEventListener("click", () => {
  chrome.tabs.create({ url: SERVER });
});

refresh();

