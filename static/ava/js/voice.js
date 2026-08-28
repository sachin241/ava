/* Records a short mono PCM WAV clip for the local Vosk backend. */
window.AvaVoice = (() => {
  let context, stream, processor, source, chunks = [];
  const status = document.querySelector("#listening-status");

  function wavBlob(samples, rate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2); const view = new DataView(buffer);
    const text = (offset, value) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt(0)));
    text(0, "RIFF"); view.setUint32(4, 36 + samples.length * 2, true); text(8, "WAVEfmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true); view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, "data"); view.setUint32(40, samples.length * 2, true);
    samples.forEach((sample, index) => view.setInt16(44 + index * 2, Math.max(-1, Math.min(1, sample)) * 0x7fff, true));
    return new Blob([view], { type: "audio/wav" });
  }
  async function start() {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("Microphone recording is not supported by this browser.");
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) throw new Error("Audio recording is not supported by this browser.");
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: { ideal: 1 } }, video: false });
      context = new AudioContextClass(); await context.resume(); source = context.createMediaStreamSource(stream); processor = context.createScriptProcessor(4096, 1, 1); chunks = [];
      processor.onaudioprocess = (event) => chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      source.connect(processor); processor.connect(context.destination); status.textContent = "Listening. Press ASK AVA again to send.";
    } catch (error) {
      if (stream) stream.getTracks().forEach((track) => track.stop());
      if (context) await context.close();
      context = stream = processor = source = null;
      throw error;
    }
  }
  async function stop() {
    if (!context || !processor || !source || !stream) throw new Error("No active voice recording.");
    processor.disconnect(); source.disconnect(); stream.getTracks().forEach((track) => track.stop());
    const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0); const samples = new Float32Array(length); let offset = 0;
    chunks.forEach((chunk) => { samples.set(chunk, offset); offset += chunk.length; });
    const blob = wavBlob(samples, context.sampleRate); await context.close(); context = null; status.textContent = "Processing command…"; return blob;
  }
  return { start, stop, active: () => Boolean(context), setStatus: (message) => { status.textContent = message; } };
})();
