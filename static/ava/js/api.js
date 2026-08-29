window.AvaApi = (() => {
  async function jsonOrError(response) {
    const body = await response.text();
    let payload;
    try { payload = body ? JSON.parse(body) : {}; } catch (_) { payload = {}; }
    if (!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
    return payload;
  }
  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || "";
  }

  async function detect(frame) {
    const data = new FormData();
    data.append("image", frame, "camera-frame.jpg");
    const response = await fetch("/api/vision/detect/", {
      method: "POST", headers: { "X-CSRFToken": csrfToken() }, body: data,
    });
    return jsonOrError(response);
  }
  async function post(path, payload = null) {
    const headers = { "X-CSRFToken": csrfToken() };
    if (payload) headers["Content-Type"] = "application/json";
    const response = await fetch(path, { method: "POST", headers, body: payload ? JSON.stringify(payload) : null });
    return jsonOrError(response);
  }
  async function upload(path, field, blob, filename) {
    const data = new FormData();
    data.append(field, blob, filename);
    const response = await fetch(path, { method: "POST", headers: { "X-CSRFToken": csrfToken() }, body: data });
    return jsonOrError(response);
  }
  return { detect, read: (frame) => upload("/api/interaction/read/", "image", frame, "read-frame.jpg"), currency: (frame) => upload("/api/interaction/currency/", "image", frame, "currency-frame.jpg"), transcribe: (audio) => upload("/api/interaction/transcribe/", "audio", audio, "command.wav"), command: (text) => post("/api/interaction/command/", { text }), completeResponse: (timestamp) => post("/api/response/complete/", { timestamp }), stopResponse: () => post("/api/response/stop/"), repeatResponse: () => post("/api/response/repeat/"), emergency: () => post("/api/emergency/"), health: () => fetch("/api/health/").then((r) => r.json()) };
})();
