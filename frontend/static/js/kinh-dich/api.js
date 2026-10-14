// SSE streaming client cho /api/kinh-dich-stream

function parseSSEBlock(raw) {
  const lines = raw.split("\n");
  let event = "message";
  let data = "";
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return null;
  try { return { event, data: JSON.parse(data) }; }
  catch { return { event, data: {} }; }
}

export async function streamDivination(question, handlers = {}) {
  const {
    onCast, onCore, onTamHop, onAction, onError, onDone,
  } = handlers;

  const token = localStorage.getItem("token");
  const res = await fetch("/api/kinh-dich-stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ cau_hoi: question }),
  });

  if (res.status === 401 && token) {
    localStorage.clear();
    location.replace("/");
    return;
  }
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(txt || `Lỗi máy chủ (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buf = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const raw = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const evt = parseSSEBlock(raw);
      if (!evt) continue;

      switch (evt.event) {
        case "cast":    onCast?.(evt.data); break;
        case "core":    onCore?.(evt.data); break;
        case "tam_hop": onTamHop?.(evt.data); break;
        case "action":  onAction?.(evt.data); break;
        case "error":   onError?.(evt.data); break;
        case "done":    onDone?.(); break;
      }
    }
  }
}
