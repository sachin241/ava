/* The only browser module allowed to call SpeechSynthesis. */
window.AvaSpeech = (() => {
  const speakingStatus = document.querySelector("#speaking-status");
  const spokenMessage = document.querySelector("#spoken-message");
  const audioStatus = document.querySelector("#audio-status");
  let language = "en-US";
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
  function update(message, status) { spokenMessage.textContent = message || "None."; speakingStatus.textContent = status; }
  function speak(request, interrupt = false) {
    if (!request || !supported()) { if (!supported()) audioStatus.textContent = "Speech output is not supported by this browser."; return; }
    if (interrupt) window.speechSynthesis.cancel();
    const cached = request.priority >= 90 ? criticalPhrases[language]?.[request.event_type] : null;
    const text = cached || request.text;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language;
    utterance.onstart = () => update(text, "Speaking.");
    utterance.onend = async () => { update(text, "Idle."); try { handle(await window.AvaApi.completeResponse(request.timestamp)); } catch (_) { /* local speech already finished */ } };
    utterance.onerror = () => update(request.text, "Speech output unavailable.");
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
    utterance.lang = language;
    utterance.rate = 1.02;
    utterance.onstart = () => update(text, "Speaking.");
    utterance.onend = () => update(text, "Idle.");
    utterance.onerror = () => update(text, "Speech output unavailable.");
    window.speechSynthesis.speak(utterance);
  }
  function stop() { if (supported()) window.speechSynthesis.cancel(); update("None.", "Stopped."); }
  return { handle, handleAll: (decisions) => decisions.forEach(handle), announce, stop, supported, setLanguage: (value) => { language = value; } };
})();
