(() => {
  const video = document.querySelector("#camera");
  const scanButton = document.querySelector("#scan-button");
  const readButton = document.querySelector("#read-button");
  const askButton = document.querySelector("#ask-button");
  const repeatButton = document.querySelector("#repeat-button");
  const stopButton = document.querySelector("#stop-button");
  const sosButton = document.querySelector("#sos-button");
  const connectCameraButton = document.querySelector("#connect-camera-button");
  const demoButton = document.querySelector("#demo-button");
  const cameraSwitchButton = document.querySelector("#camera-switch-button");
  const demoFrame = document.querySelector("#demo-frame");
  const cameraStatus = document.querySelector("#camera-status");
  const microphoneStatus = document.querySelector("#microphone-status");
  const audioStatus = document.querySelector("#audio-status");
  const detectionStatus = document.querySelector("#detection-status");
  const list = document.querySelector("#detection-list");
  const inferenceTime = document.querySelector("#inference-time");
  const trackingMetrics = document.querySelector("#tracking-metrics");
  const systemState = document.querySelector("#system-state");
  const speechLanguage = document.querySelector("#speech-language");
  let requestInFlight = false;
  let isScanning = false;
  let scanTimer = null;
  let droppedFrames = 0;
  let completedFrames = 0;
  let scanStartedAt = 0;
  let lastSceneSpeech = "";
  let lastSceneSpeechAt = 0;
  const hasConnectCameraButton = Boolean(connectCameraButton);
  const hasCameraSwitchButton = Boolean(cameraSwitchButton);
  const hasDemoButton = Boolean(demoButton);
  const hasSpeechLanguage = Boolean(speechLanguage);

  function renderDetections(detections, worldState) {
    list.replaceChildren();
    if (!detections.length) {
      const item = document.createElement("li"); item.textContent = "No objects detected in the latest frame."; list.append(item); return;
    }
    const tracked = new Map(worldState.objects.map((object) => [object.id, object]));
    detections.forEach((detection) => {
      const item = document.createElement("li");
      const context = tracked.get(detection.track_id);
      const temporal = context ? ` Track ${context.id}: ${context.direction}, ${context.proximity}, ${context.motion}.` : "";
      item.textContent = `${detection.label}, ${Math.round(detection.confidence * 100)}% confidence.${temporal}`;
      list.append(item);
    });
  }

  function updateMetrics(result) {
    const elapsedSeconds = Math.max((performance.now() - scanStartedAt) / 1000, 0.001);
    const browserFps = (completedFrames / elapsedSeconds).toFixed(2);
    trackingMetrics.textContent = `Browser FPS: ${browserFps}; server FPS: ${result.tracking.fps}; dropped frames: ${droppedFrames}; active tracks: ${result.tracking.active_tracks}.`;
  }

  function objectSummary(worldState) {
    const objects = worldState.objects.slice(0, 3).map((object) => {
      const label = object.name.charAt(0).toUpperCase() + object.name.slice(1);
      const place = object.direction === "center" ? "ahead" : `on your ${object.direction}`;
      return `${label} ${place}, ${object.proximity}`;
    });
    if (!objects.length) return "No tracked objects.";
    if (objects.length === 1) return `${objects[0]}.`;
    if (objects.length === 2) return `${objects[0]} and ${objects[1]}.`;
    return `${objects.slice(0, -1).join("; ")}, and ${objects[objects.length - 1]}.`;
  }

  function shouldAnnounceScene(summary) {
    if (!isScanning) return false;
    if (!summary) return false;
    const now = performance.now();
    if (summary === lastSceneSpeech && now - lastSceneSpeechAt < 8000) return false;
    if (window.speechSynthesis?.speaking || window.speechSynthesis?.pending) return false;
    lastSceneSpeech = summary;
    lastSceneSpeechAt = now;
    return true;
  }

  async function processLatestFrame() {
    // While inference runs, newly available frames are deliberately discarded; none are queued.
    if (requestInFlight) { droppedFrames += 1; return; }
    requestInFlight = true;
    detectionStatus.textContent = "Analysing the latest camera frame…";
    try {
      const frame = await window.AvaCamera.captureLatest();
      if (!frame) throw new Error("Unable to capture a camera frame.");
      const result = await window.AvaApi.detect(frame);
      completedFrames += 1;
      renderDetections(result.detections, result.world_state);
      systemState.textContent = `${result.safety.system_state}; path ${result.safety.path_status}.`;
      const audibleResponse = result.responses.find((decision) => decision.action !== "DROP");
      if (audibleResponse) window.AvaSpeech.handle(audibleResponse);
      inferenceTime.textContent = `Inference: ${result.inference_ms} ms`;
      const summary = result.detections.length
        ? `Detected ${result.detections.length} object(s). ${objectSummary(result.world_state)}`
        : "No objects detected in the latest frame.";
      detectionStatus.textContent = summary;
      if (!audibleResponse && shouldAnnounceScene(summary)) window.AvaSpeech.announce(summary);
      updateMetrics(result);
    } catch (error) {
      detectionStatus.textContent = error.message;
    } finally {
      requestInFlight = false;
      if (!isScanning) scanButton.disabled = false;
    }
  }

  async function readCurrentFrame() {
    detectionStatus.textContent = "Reading the current frame…";
    try {
      const frame = await window.AvaCamera.captureLatest();
      const result = await window.AvaApi.read(frame);
      detectionStatus.textContent = `Read confidence: ${result.ocr.confidence}%; attempts: ${result.ocr.attempts}; OCR: ${result.ocr.elapsed_ms} ms.`;
      window.AvaSpeech.handle(result.response);
    } catch (error) { detectionStatus.textContent = error.message; }
  }

  function toggleScan() {
    isScanning = !isScanning;
    scanButton.setAttribute("aria-pressed", String(isScanning));
    if (isScanning) {
      droppedFrames = 0; completedFrames = 0; scanStartedAt = performance.now();
      scanButton.textContent = "STOP SCAN";
      processLatestFrame();
      scanTimer = window.setInterval(processLatestFrame, 400);
    } else {
      window.clearInterval(scanTimer); scanTimer = null;
      scanButton.textContent = "START SCAN";
      detectionStatus.textContent = "Scanning paused.";
    }
  }

  async function checkMicrophone() {
    if (!navigator.mediaDevices?.getUserMedia) { microphoneStatus.textContent = "Not supported by this browser."; return; }
    try {
      const mic = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      mic.getTracks().forEach((track) => track.stop());
      microphoneStatus.textContent = "Ready (permission granted).";
    } catch (_) { microphoneStatus.textContent = "Unavailable or permission not granted."; }
  }

  function setCameraSwitchLabel(facing) {
    if (!hasCameraSwitchButton) return;
    cameraSwitchButton.textContent = facing === "environment" ? "SWITCH TO FRONT" : "SWITCH TO BACK";
  }

  async function startLiveCamera(switching = false) {
    try {
      if (isScanning) toggleScan();
      cameraStatus.textContent = switching ? "Switching camera…" : "Connecting camera…";
      const facing = switching ? await window.AvaCamera.switchCamera(video) : await window.AvaCamera.start(video);
      if (video) video.hidden = false;
      if (demoFrame) demoFrame.hidden = true;
      if (hasDemoButton) {
        demoButton.setAttribute("aria-pressed", "false");
        demoButton.textContent = "USE DEMO";
      }
      cameraStatus.textContent = `Camera ready (${facing === "environment" ? "back" : "front"} camera when available). AVA keeps only the latest frame.`;
      scanButton.disabled = false;
      readButton.disabled = false;
      askButton.disabled = false;
      if (hasCameraSwitchButton) cameraSwitchButton.disabled = false;
      setCameraSwitchLabel(facing);
      return true;
    } catch (error) {
      cameraStatus.textContent = `Camera unavailable: ${error.message}${hasConnectCameraButton ? " Tap CONNECT CAMERA to try again." : ""}`;
      return false;
    }
  }

  async function initialise() {
    if (!window.isSecureContext && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
      await useDemo("Camera and microphone access require a secure origin. Open AVA through localhost or HTTPS, then reconnect the camera.");
      checkMicrophone();
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      await useDemo("Camera access is not supported by this browser. Prepared demo ready.");
      checkMicrophone();
      return;
    }
    if (!await startLiveCamera()) await useDemo(`${cameraStatus.textContent}. Prepared demo ready.`);
    checkMicrophone();
  }

  async function useDemo(message = "Prepared demo ready. It uses the same image API as camera frames.") {
    try {
      if (isScanning) toggleScan();
      await window.AvaCamera.useDemo(demoFrame);
      if (video) video.hidden = true;
      if (demoFrame) demoFrame.hidden = false;
      if (hasDemoButton) {
        demoButton.setAttribute("aria-pressed", "true");
        demoButton.textContent = "DEMO ACTIVE";
      }
      if (hasCameraSwitchButton) cameraSwitchButton.disabled = false;
      cameraStatus.textContent = message;
      scanButton.disabled = false;
      readButton.disabled = false;
    } catch (error) { cameraStatus.textContent = error.message; }
  }

  document.addEventListener("click", () => {
    if (window.AudioContext || window.webkitAudioContext) audioStatus.textContent = "Browser audio is ready.";
  }, { once: true });
  scanButton.addEventListener("click", toggleScan);
  readButton.addEventListener("click", readCurrentFrame);
  askButton.addEventListener("click", async () => {
    try {
      if (!window.AvaVoice.active()) {
        await window.AvaVoice.start(); askButton.textContent = "SEND COMMAND"; askButton.setAttribute("aria-pressed", "true"); return;
      }
      const audio = await window.AvaVoice.stop(); askButton.textContent = "ASK AVA"; askButton.setAttribute("aria-pressed", "false");
      const result = await window.AvaApi.transcribe(audio);
      window.AvaVoice.setStatus(result.transcript ? `Heard: ${result.transcript}` : "No command heard.");
      window.AvaSpeech.handle(result.response);
      if (result.requires_frame) await readCurrentFrame();
    } catch (error) { window.AvaVoice.setStatus("Listening unavailable."); detectionStatus.textContent = error.message; askButton.textContent = "ASK AVA"; askButton.setAttribute("aria-pressed", "false"); }
  });
  stopButton.addEventListener("click", async () => {
    window.AvaSpeech.stop();
    try { await window.AvaApi.stopResponse(); } catch (error) { detectionStatus.textContent = error.message; }
  });
  repeatButton.addEventListener("click", async () => {
    try { window.AvaSpeech.handle(await window.AvaApi.repeatResponse()); } catch (error) { detectionStatus.textContent = error.message; }
  });
  sosButton.addEventListener("click", async () => {
    try {
      const result = await window.AvaApi.emergency();
      systemState.textContent = "Critical emergency response requested.";
      window.AvaSpeech.handle(result.response);
    } catch (error) { detectionStatus.textContent = error.message; }
  });
  if (hasConnectCameraButton) {
    connectCameraButton.addEventListener("click", async () => {
      connectCameraButton.disabled = true;
      try {
        if (!await startLiveCamera()) await useDemo(`${cameraStatus.textContent}. Prepared demo ready.`);
      } finally {
        connectCameraButton.disabled = false;
      }
    });
  }
  if (hasDemoButton) demoButton.addEventListener("click", () => useDemo());
  if (hasCameraSwitchButton) {
    cameraSwitchButton.addEventListener("click", async () => {
      cameraSwitchButton.disabled = true;
      if (!await startLiveCamera(true)) await useDemo(`${cameraStatus.textContent}. Prepared demo ready.`);
    });
  }
  if (hasSpeechLanguage) {
    speechLanguage.addEventListener("change", () => {
      window.AvaSpeech.setLanguage(speechLanguage.value);
      audioStatus.textContent = `Speech language selected: ${speechLanguage.options[speechLanguage.selectedIndex].text}.`;
    });
  }
  initialise();
})();
