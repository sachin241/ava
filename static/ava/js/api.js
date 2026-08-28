window.AvaApi = (() => {
  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || "";
  }

  async function detect(frame) {
    const data = new FormData();
    data.append("image", frame, "camera-frame.jpg");
    const response = await fetch("/api/vision/detect/", {
      method: "POST", headers: { "X-CSRFToken": csrfToken() }, body: data,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Detection request failed.");
    return payload;
  }
  async function post(path, payload = null) {
    const headers = { "X-CSRFToken": csrfToken() };
    if (payload) headers["Content-Type"] = "application/json";
    const response = await fetch(path, { method: "POST", headers, body: payload ? JSON.stringify(payload) : null });
    const responseBody = await response.json();
    if (!response.ok) throw new Error(responseBody.error || "Response request failed.");
    return responseBody;
  }
  async function upload(path, field, blob, filename) {
    const data = new FormData();
    data.append(field, blob, filename);
    const response = await fetch(path, { method: "POST", headers: { "X-CSRFToken": csrfToken() }, body: data });
    const responseBody = await response.json();
    if (!response.ok) throw new Error(responseBody.error || "Upload request failed.");
    return responseBody;
  }
  return { detect, read: (frame) => upload("/api/interaction/read/", "image", frame, "read-frame.jpg"), transcribe: (audio) => upload("/api/interaction/transcribe/", "audio", audio, "command.wav"), completeResponse: (timestamp) => post("/api/response/complete/", { timestamp }), stopResponse: () => post("/api/response/stop/"), repeatResponse: () => post("/api/response/repeat/"), emergency: () => post("/api/emergency/") };
})();
