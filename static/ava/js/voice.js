/* Records a short mono PCM WAV clip for the local Vosk backend. */
window.AvaVoice = (() => {
  let context, stream, processor, source, chunks = [];
  const status = document.querySelector("#listening-status");
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let handsFree = false;
  let commandHandler = null;
  let commandInFlight = false;
  let speechLocked = false;
  let restartTimer = null;
  let recognitionRunning = false;
  let restartPending = false;
  let voiceSessionId = 0;
  let restartAttempts = 0;

  function wavBlob(samples, rate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    const text = (offset, value) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt(0)));
    text(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    text(8, "WAVEfmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, rate, true);
    view.setUint32(28, rate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    text(36, "data");
    view.setUint32(40, samples.length * 2, true);
    samples.forEach((sample, index) => view.setInt16(44 + index * 2, Math.max(-1, Math.min(1, sample)) * 0x7fff, true));
    return new Blob([view], { type: "audio/wav" });
  }

  async function start() {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("Microphone recording is not supported by this browser.");
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) throw new Error("Audio recording is not supported by this browser.");
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: { ideal: 1 } }, video: false });
      context = new AudioContextClass();
      await context.resume();
      source = context.createMediaStreamSource(stream);
      processor = context.createScriptProcessor(4096, 1, 1);
      chunks = [];
      processor.onaudioprocess = (event) => chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      source.connect(processor);
      processor.connect(context.destination);
      status.textContent = "Listening. Press ASK AVA again to send.";
    } catch (error) {
      if (stream) stream.getTracks().forEach((track) => track.stop());
      if (context) await context.close();
      context = stream = processor = source = null;
      throw error;
    }
  }

  async function stop() {
    if (!context || !processor || !source || !stream) throw new Error("No active voice recording.");
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const samples = new Float32Array(length);
    let offset = 0;
    chunks.forEach((chunk) => {
      samples.set(chunk, offset);
      offset += chunk.length;
    });
    const blob = wavBlob(samples, context.sampleRate);
    await context.close();
    context = null;
    status.textContent = "Processing command...";
    return blob;
  }

  function clearRestart() {
    if (restartTimer) window.clearTimeout(restartTimer);
    restartTimer = null;
  }

  function restartListeningWhenSafe(delay = 350) {
    clearRestart();
    restartPending = true;
    const session = voiceSessionId;
    if (!recognition || !handsFree || commandInFlight || speechLocked || window.AvaSpeech?.isSpeaking?.()) return;
    if (recognitionRunning) { restartPending = false; return; }
    status.textContent = "Preparing to listen…";
    restartTimer = window.setTimeout(() => {
      restartTimer = null;
      if (session !== voiceSessionId || !recognition || !handsFree || commandInFlight || speechLocked || window.AvaSpeech?.isSpeaking?.() || recognitionRunning) return;
      try {
        recognition.start();
        restartAttempts = 0;
      } catch (error) {
        restartAttempts += 1;
        const retry = Math.min(3000, 300 * (2 ** Math.min(restartAttempts, 3)));
        console.debug("[AVA VOICE] recognition.start() rejected", error.name || error.message);
        if (restartAttempts < 5) restartListeningWhenSafe(retry);
      }
    }, delay);
  }

  function setupRecognition() {
    if (!Recognition || recognition) return Boolean(Recognition);
    recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      recognitionRunning = true;
      restartPending = false;
      console.debug("[AVA STT] onstart", { session: voiceSessionId });
      status.textContent = "Listening. Say a command.";
    };
    recognition.onspeechstart = () => console.debug("[AVA STT] onspeechstart", { session: voiceSessionId });
    recognition.onspeechend = () => console.debug("[AVA STT] onspeechend", { session: voiceSessionId });
    recognition.onresult = async (event) => {
      const session = voiceSessionId;
      const result = event.results[event.resultIndex ?? event.results.length - 1];
      if (!result || !result.isFinal || session !== voiceSessionId) return;
      commandInFlight = true;
      recognitionRunning = false;
      console.debug("[AVA STT] onresult", { session, transcript: result[0].transcript });
      try { recognition.stop(); } catch (_) {}
      const transcript = result[0].transcript.trim();
      status.textContent = transcript ? `Command: ${transcript}` : "No command heard.";
      try {
        if (commandHandler && transcript) await commandHandler(transcript);
      } finally {
        commandInFlight = false;
        if (session === voiceSessionId && handsFree && !speechLocked) restartListeningWhenSafe(500);
      }
    };
    recognition.onerror = (event) => {
      recognitionRunning = false;
      console.debug("[AVA STT] onerror", { session: voiceSessionId, error: event.error });
      status.textContent = event.error === "not-allowed" ? "Microphone permission denied." : `Speech recognition: ${event.error}.`;
      if (handsFree && !commandInFlight && !["not-allowed", "service-not-allowed"].includes(event.error)) restartListeningWhenSafe(event.error === "no-speech" ? 300 : 800);
    };
    recognition.onend = () => {
      recognitionRunning = false;
      console.debug("[AVA STT] onend", { session: voiceSessionId });
      if (handsFree && !speechLocked && !commandInFlight && !window.AvaSpeech?.isSpeaking?.()) restartListeningWhenSafe(700);
    };
    return true;
  }

  function enable(command) {
    commandHandler = command;
    voiceSessionId += 1;
    handsFree = setupRecognition();
    if (!handsFree) throw new Error("Browser speech recognition is unavailable. Use ASK AVA.");
    maybeStart(0);
    return true;
  }

  function disable() {
    handsFree = false;
    voiceSessionId += 1;
    commandInFlight = false;
    recognitionRunning = false;
    clearRestart();
    if (recognition) try { recognition.stop(); } catch (_) {}
  }

  function pause() {
    handsFree = false;
    voiceSessionId += 1;
    recognitionRunning = false;
    clearRestart();
    if (recognition) try { recognition.stop(); } catch (_) {}
  }

  function resume() {
    if (!recognition) return;
    handsFree = true;
    voiceSessionId += 1;
    restartListeningWhenSafe(0);
  }

  document.addEventListener("ava:speech-state", (event) => {
    speechLocked = Boolean(event.detail?.speaking);
    if (speechLocked) {
      clearRestart();
      if (handsFree && recognition) {
        try { recognition.stop(); } catch (_) {}
      }
      status.textContent = "Speaking. Listening paused.";
      return;
    }
    if (handsFree && !commandInFlight) restartListeningWhenSafe(300);
  });

  return {
    start,
    stop,
    active: () => Boolean(context),
    setStatus: (message) => { status.textContent = message; },
    enable,
    disable,
    pause,
    resume,
    supportsHandsFree: () => Boolean(Recognition),
  };
})();
