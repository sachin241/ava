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
  const voiceControlButton = document.querySelector("#voice-control-button");
  const voiceControlStatus = document.querySelector("#voice-control-status");
  const sttStatus = document.querySelector("#stt-status");
  let requestInFlight = false;
  let isScanning = false;
  let scanTimer = null;
  let droppedFrames = 0;
  let completedFrames = 0;
  let scanStartedAt = 0;
  let currencyRequestInFlight = false;
  let lastCurrencyScanAt = 0;
  let lastCurrencyAnnouncement = { denomination: null, at: 0 };
  const hasConnectCameraButton = Boolean(connectCameraButton);
  const hasCameraSwitchButton = Boolean(cameraSwitchButton);
  const hasDemoButton = Boolean(demoButton);
  const hasSpeechLanguage = Boolean(speechLanguage);
  const SCAN_INTERVAL_MS = 320;
  const CURRENCY_SCAN_INTERVAL_MS = 0;
  const isSecureMediaContext = () => Boolean(window.isSecureContext || ["localhost", "127.0.0.1"].includes(location.hostname));
  const isLikelyMobile = () => Boolean(window.matchMedia?.("(pointer: coarse)")?.matches || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent));
  const secureOriginMessage = "Camera and microphone require HTTPS on a phone. Use https:// for the computer's LAN address, or open AVA on the phone's own localhost.";

  async function handleHandsFreeCommand(transcript) {
    if (voiceControlStatus) voiceControlStatus.textContent = "Processing.";
    console.debug("[AVA VOICE] command received", transcript);
    try {
      const result = await window.AvaApi.command(transcript);
      console.debug("[AVA STATE] intent/controller", result.intent, result.assistant);
      await applyVoiceCommand(result);
      if (result.response) window.AvaSpeech.handle(result.response);
    } catch (error) {
      detectionStatus.textContent = error.message;
    } finally {
      if (voiceControlStatus) voiceControlStatus.textContent = "Active.";
    }
  }

  async function enableVoiceControl() {
    try {
      if (!window.AvaVoice) throw new Error("Voice capture is unavailable in this page.");
      if (!isSecureMediaContext()) throw new Error(secureOriginMessage);
      if (!window.AvaSpeech.supported()) throw new Error("Browser audio/TTS is unavailable.");
      if (!window.AvaVoice.supportsHandsFree()) throw new Error("Speech recognition is unavailable. Use ASK AVA.");
      window.AvaVoice.enable(handleHandsFreeCommand);
      if (voiceControlStatus) voiceControlStatus.textContent = "Active.";
      if (microphoneStatus) microphoneStatus.textContent = "Ready for browser voice control.";
      if (sttStatus) sttStatus.textContent = "Ready (browser recognition).";
      if (voiceControlButton) { voiceControlButton.textContent = "VOICE CONTROL: ON"; voiceControlButton.setAttribute("aria-pressed", "true"); }
    } catch (error) {
      if (voiceControlStatus) voiceControlStatus.textContent = `Unavailable: ${error.message}`;
      if (sttStatus) sttStatus.textContent = "Unavailable; use ASK AVA.";
    }
  }

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

  function applyAssistantState(state) {
    if (!state) return;
    if (systemState) systemState.textContent = `${state.state}${state.muted ? " (muted)" : ""}.`;
  }

  async function applyVoiceCommand(result) {
    applyAssistantState(result.assistant);
    const intent = result.intent;
    if (intent === "START_MONITORING" || intent === "RESUME_MONITORING") {
      if (!isScanning) toggleScan();
    } else if (intent === "STOP_MONITORING" || intent === "PAUSE_MONITORING") {
      if (isScanning) toggleScan();
    } else if (intent === "SCAN") {
      await processLatestFrame();
    } else if (intent === "READ" && result.requires_frame) {
      await readCurrentFrame();
    } else if (intent === "CURRENCY" && result.requires_frame) {
      await checkCurrencyInFrame(await window.AvaCamera.captureLatest(), true);
    } else if (intent === "STOP_SPEAKING" || intent === "STOP") {
      window.AvaSpeech.stop();
    } else if (intent === "CHANGE_LANGUAGE" && result.language) {
      window.AvaSpeech.setLanguage(result.language);
      if (speechLanguage) speechLanguage.value = result.language;
    }
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
      checkCurrencyInFrame(frame);
      completedFrames += 1;
      renderDetections(result.detections, result.world_state);
      systemState.textContent = `${isScanning ? "MONITORING" : "IDLE"}; path ${result.safety.path_status}.`;
      // A clear-path transition is useful in the UI but is not narrated on
      // every passive frame; users can ask "is the path clear?" explicitly.
      const filteredResponses = result.responses.filter((decision) => decision.action !== "DROP" && decision.request?.event_type !== "PATH_CLEARED");
      const audibleResponse = filteredResponses.find(Boolean);
      if (audibleResponse) window.AvaSpeech.handle(audibleResponse);
      inferenceTime.textContent = `Inference: ${result.inference_ms} ms`;
      const summary = result.detections.length
        ? `Scene updated. Path ${result.safety.path_status}.`
        : "Scene updated. No objects detected.";
      detectionStatus.textContent = summary;
      if (!audibleResponse && filteredResponses.length) window.AvaSpeech.handleAll(filteredResponses);
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
      if (!frame) throw new Error("No camera frame is available. Connect the camera or choose USE DEMO.");
      const result = await window.AvaApi.read(frame);
      detectionStatus.textContent = `Read confidence: ${result.ocr.confidence}%; attempts: ${result.ocr.attempts}; OCR: ${result.ocr.elapsed_ms} ms.`;
      window.AvaSpeech.handle(result.response);
    } catch (error) { detectionStatus.textContent = error.message; }
  }

  async function checkCurrencyInFrame(frame, force = false) {
    if (!frame || currencyRequestInFlight) return;
    const now = performance.now();
    if (!force && (!isScanning || now - lastCurrencyScanAt < CURRENCY_SCAN_INTERVAL_MS)) return;
    currencyRequestInFlight = true;
    lastCurrencyScanAt = now;
    try {
      const result = await window.AvaApi.currency(frame);
      if (!result.currency?.denomination || result.currency.confidence === "low" || !result.response || result.response.action === "DROP") return;
      if (!force && lastCurrencyAnnouncement.denomination === result.currency.denomination && now - lastCurrencyAnnouncement.at < 15000) return;
      lastCurrencyAnnouncement = { denomination: result.currency.denomination, at: now };
      detectionStatus.textContent = `Indian currency detected: INR ${result.currency.denomination}.`;
      window.AvaSpeech.handle(result.response);
    } catch (error) {
      console.debug("[AVA CURRENCY] recognition unavailable", error.message);
    } finally {
      currencyRequestInFlight = false;
    }
  }

  function toggleScan() {
    isScanning = !isScanning;
    scanButton.setAttribute("aria-pressed", String(isScanning));
    if (isScanning) {
      droppedFrames = 0; completedFrames = 0; scanStartedAt = performance.now();
      scanButton.textContent = "STOP SCAN";
      processLatestFrame();
      scanTimer = window.setInterval(() => processLatestFrame(), SCAN_INTERVAL_MS);
    } else {
      window.clearInterval(scanTimer); scanTimer = null;
      scanButton.textContent = "START SCAN";
      detectionStatus.textContent = "Scanning paused.";
    }
  }

  async function checkMicrophone() {
    if (!microphoneStatus) return;
    if (!isSecureMediaContext()) { microphoneStatus.textContent = "Needs HTTPS on mobile."; return; }
    if (!navigator.mediaDevices?.getUserMedia) { microphoneStatus.textContent = "Not supported by this browser."; return; }
    if (!navigator.permissions?.query) { microphoneStatus.textContent = "Tap ASK AVA or ENABLE AVA VOICE to allow."; return; }
    try {
      const permission = await navigator.permissions.query({ name: "microphone" });
      microphoneStatus.textContent = permission.state === "granted" ? "Ready (permission granted)." : "Tap ASK AVA or ENABLE AVA VOICE to allow.";
      permission.onchange = () => { microphoneStatus.textContent = permission.state === "granted" ? "Ready (permission granted)." : "Tap ASK AVA or ENABLE AVA VOICE to allow."; };
    } catch (_) {
      microphoneStatus.textContent = "Tap ASK AVA or ENABLE AVA VOICE to allow.";
    }
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
    if (!isSecureMediaContext()) {
      await useDemo(`${secureOriginMessage} Prepared demo ready.`);
      checkMicrophone();
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      await useDemo("Camera access is not supported by this browser. Prepared demo ready.");
      checkMicrophone();
      return;
    }
    if (isLikelyMobile()) {
      cameraStatus.textContent = "Tap CONNECT CAMERA to allow the mobile camera.";
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
      askButton.disabled = false;
    } catch (error) { cameraStatus.textContent = error.message; }
  }

  document.addEventListener("click", () => {
    if (window.AudioContext || window.webkitAudioContext) audioStatus.textContent = "Browser audio is ready.";
  }, { once: true });
  scanButton.addEventListener("click", toggleScan);
  readButton.addEventListener("click", readCurrentFrame);
  askButton.addEventListener("click", async () => {
    try {
      if (!window.AvaVoice) throw new Error("Voice capture is unavailable in this page.");
      if (!isSecureMediaContext()) throw new Error(secureOriginMessage);
      if (!window.AvaVoice.active()) {
        await window.AvaVoice.start(); askButton.textContent = "SEND COMMAND"; askButton.setAttribute("aria-pressed", "true"); return;
      }
      const audio = await window.AvaVoice.stop(); askButton.textContent = "ASK AVA"; askButton.setAttribute("aria-pressed", "false");
      const result = await window.AvaApi.transcribe(audio);
      if (window.AvaVoice.setStatus) window.AvaVoice.setStatus(result.transcript ? `Heard: ${result.transcript}` : "No command heard.");
      else if (voiceControlStatus) voiceControlStatus.textContent = result.transcript ? `Heard: ${result.transcript}` : "No command heard.";
      window.AvaSpeech.handle(result.response);
      await applyVoiceCommand(result);
    } catch (error) {
      if (window.AvaVoice?.setStatus) window.AvaVoice.setStatus("Listening unavailable.");
      else if (voiceControlStatus) voiceControlStatus.textContent = "Listening unavailable.";
      detectionStatus.textContent = error.message;
      askButton.textContent = "ASK AVA";
      askButton.setAttribute("aria-pressed", "false");
    }
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
      systemState.textContent = "EMERGENCY.";
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
      window.AvaVoice?.setLanguage?.(speechLanguage.value);
      audioStatus.textContent = `Speech language selected: ${speechLanguage.options[speechLanguage.selectedIndex].text}.`;
    });
  }
  if (voiceControlButton) voiceControlButton.addEventListener("click", () => {
    if (voiceControlButton.getAttribute("aria-pressed") === "true") { window.AvaVoice?.disable(); voiceControlButton.textContent = "ENABLE AVA VOICE"; voiceControlButton.setAttribute("aria-pressed", "false"); if (voiceControlStatus) voiceControlStatus.textContent = "Off."; }
    else enableVoiceControl();
  });
  if (sttStatus) window.AvaApi.health().then((health) => { sttStatus.textContent = health.stt?.available ? "Ready (local STT model)." : "Local STT unavailable; browser fallback available if supported."; }).catch(() => { sttStatus.textContent = "Unable to check local STT; browser fallback available if supported."; });
  initialise();
})();
