/* The only browser module allowed to call SpeechSynthesis. */
window.AvaSpeech = (() => {
  const speakingStatus = document.querySelector("#speaking-status");
  const spokenMessage = document.querySelector("#spoken-message");
  const audioStatus = document.querySelector("#audio-status");
  let language = "en-US";
  let speechGeneration = 0;
  let preferredVoice = null;
  const criticalPhrases = {
    "hi-IN": {
      EMERGENCY_DETECTED: "आपात स्थिति का पता चला है। कृपया ध्यान दें।",
      OBSTACLE_APPROACHING: "रुकिए। सामने बाधा है।",
      PATH_BLOCKED: "रुकिए। सामने बाधा है।",
      OBSTACLE_ENTERED_PATH: "सामने बाधा है।",
      PATH_CLEARED: "रास्ता साफ़ है।",
    },
  };

  function supported() { return "speechSynthesis" in window && "SpeechSynthesisUtterance" in window; }
  function pickVoice() {
    if (!supported()) return null;
    const voices = window.speechSynthesis.getVoices();
    const wanted = language.toLowerCase();
    const match = voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith(wanted));
    if (match) return match;
    const indianLocal = voices.find((voice) => /hindi|india|indian/i.test(`${voice.name} ${voice.lang}`));
    if (language === "hi-IN" && indianLocal) return indianLocal;
    return voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith("en-")) || voices[0] || null;
  }
  function applyPreferredVoice(utterance) {
    if (!utterance) return;
    preferredVoice = pickVoice();
    if (preferredVoice) utterance.voice = preferredVoice;
    utterance.lang = language;
  }
  function update(message, status) { spokenMessage.textContent = message || "None."; speakingStatus.textContent = status; document.dispatchEvent(new CustomEvent("ava:speech-state", { detail: { speaking: status === "Speaking." } })); }
  function speak(request, interrupt = false) {
    if (!request || !supported()) { if (!supported()) audioStatus.textContent = "Speech output is not supported by this browser."; return; }
    if (interrupt) window.speechSynthesis.cancel();
    const generation = ++speechGeneration;
    console.debug("[AVA TTS] start requested", { generation, event: request.event_type });
    // Cached wording is reserved for the emergency phrase. Object-aware
    // hazard text from the Response Manager must remain intact.
    const cached = request.event_type === "EMERGENCY_DETECTED" ? criticalPhrases[language]?.[request.event_type] : null;
    const text = cached || request.text;
    const utterance = new SpeechSynthesisUtterance(text);
    applyPreferredVoice(utterance);
    utterance.onstart = () => { if (generation === speechGeneration) { console.debug("[AVA TTS] start", { generation }); update(text, "Speaking."); } };
    utterance.onend = async () => { if (generation !== speechGeneration) return; console.debug("[AVA TTS] end", { generation }); update(text, "Idle."); try { handle(await window.AvaApi.completeResponse(request.timestamp)); } catch (_) { /* local speech already finished */ } };
    utterance.onerror = () => { if (generation === speechGeneration) { console.debug("[AVA TTS] error", { generation }); update(request.text, "Speech output unavailable."); } };
    window.speechSynthesis.speak(utterance);
  }
  function handle(decision) {
    if (!decision || decision.action === "DROP") return;
    if (decision.action === "INTERRUPT") speak(decision.request, true);
    if (decision.action === "SPEAK") speak(decision.request, false);
  }
  function announce(text) {
    if (!text || !supported()) return;
    const utterance = new SpeechSynthesisUtterance(text);
    const generation = ++speechGeneration;
    applyPreferredVoice(utterance);
    utterance.rate = 1.02;
    utterance.onstart = () => { if (generation === speechGeneration) update(text, "Speaking."); };
    utterance.onend = () => { if (generation === speechGeneration) update(text, "Idle."); };
    utterance.onerror = () => { if (generation === speechGeneration) update(text, "Speech output unavailable."); };
    window.speechSynthesis.speak(utterance);
  }
  function stop() { speechGeneration += 1; if (supported()) window.speechSynthesis.cancel(); console.debug("[AVA TTS] cancelled"); update("None.", "Stopped."); }
  if (supported()) {
    window.speechSynthesis.onvoiceschanged = () => {
      preferredVoice = pickVoice();
    };
  }
  return { handle, handleAll: (decisions) => decisions.forEach(handle), announce, stop, supported, isSpeaking: () => Boolean(window.speechSynthesis?.speaking || window.speechSynthesis?.pending), setLanguage: (value) => { language = value; preferredVoice = pickVoice(); } };
})();
