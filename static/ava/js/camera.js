window.AvaCamera = (() => {
  let stream = null;
  let source = null;
  let facing = "environment";

  function stop() {
    if (stream) stream.getTracks().forEach((track) => track.stop());
    stream = null;
    source = null;
  }

  function waitForVideo(video) {
    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const timeout = window.setTimeout(() => resolve(), 2000);
      video.addEventListener("loadedmetadata", resolve, { once: true });
      video.addEventListener("loadeddata", resolve, { once: true });
      video.addEventListener("error", () => reject(new Error("The camera stream could not be displayed.")), { once: true });
      video.addEventListener("loadedmetadata", () => window.clearTimeout(timeout), { once: true });
      video.addEventListener("loadeddata", () => window.clearTimeout(timeout), { once: true });
    });
  }

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.decoding = "async";
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("The prepared demo image is unavailable."));
      image.src = src;
    });
  }

  async function loadFallbackDemo() {
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="1536" height="1024" viewBox="0 0 1536 1024">
        <defs>
          <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#dfe9f3"/>
            <stop offset="100%" stop-color="#b7c4d6"/>
          </linearGradient>
          <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#8b99ab"/>
            <stop offset="100%" stop-color="#6c7b8f"/>
          </linearGradient>
        </defs>
        <rect width="1536" height="1024" fill="url(#bg)"/>
        <rect y="680" width="1536" height="344" fill="url(#floor)"/>
        <rect x="0" y="0" width="1536" height="120" fill="#eef3f8" opacity="0.9"/>
        <rect x="1120" y="160" width="230" height="520" fill="#f7f9fc" stroke="#9aa8ba" stroke-width="10"/>
        <rect x="1188" y="160" width="94" height="480" fill="#d9e4ef" stroke="#9aa8ba" stroke-width="8"/>
        <rect x="240" y="410" width="240" height="110" rx="16" fill="#473c31"/>
        <rect x="240" y="512" width="30" height="160" fill="#473c31"/>
        <rect x="450" y="512" width="30" height="160" fill="#473c31"/>
        <rect x="260" y="330" width="200" height="90" rx="18" fill="#6a5646"/>
        <rect x="256" y="320" width="208" height="26" rx="12" fill="#816858"/>
        <rect x="920" y="170" width="180" height="120" rx="10" fill="#f7f7f7" stroke="#38556e" stroke-width="8"/>
        <rect x="930" y="182" width="160" height="44" rx="6" fill="#1c9b51"/>
        <text x="1010" y="214" text-anchor="middle" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="#ffffff">EXIT</text>
        <rect x="900" y="312" width="230" height="140" rx="10" fill="#ffffff" stroke="#38556e" stroke-width="8"/>
        <text x="1015" y="372" text-anchor="middle" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#214d74">LIBRARY</text>
        <text x="1015" y="410" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#214d74">SIGN</text>
      </svg>`;
    return loadImage(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`);
  }

  async function start(video, preferredFacing = "environment") {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("Camera access is not supported by this browser.");
    stop();
    video.pause();
    video.srcObject = null;
    try {
      // `ideal` selects the rear camera where available without rejecting
      // older mobile browsers that do not implement facingMode exactly.
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: preferredFacing } }, audio: false });
    } catch (preferredError) {
      try { stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false }); } catch (_) { throw preferredError; }
    }
    try {
      video.srcObject = stream;
      await waitForVideo(video);
      try {
        await video.play();
      } catch (_) {
        // Some mobile browsers require a user gesture to start playback even
        // after the camera stream has been granted. Keep the stream attached so
        // the camera light stays on and a later tap can resume playback.
      }
      const settings = stream.getVideoTracks()[0]?.getSettings?.() || {};
      facing = settings.facingMode || preferredFacing;
      source = video;
      return facing;
    } catch (error) {
      stop();
      video.srcObject = null;
      throw error;
    }
  }

  async function switchCamera(video) {
    return start(video, facing === "environment" ? "user" : "environment");
  }

  async function useDemo(image) {
    const src = image?.currentSrc || image?.src || "";
    if (src) {
      try {
        source = image.complete && image.naturalWidth ? image : await loadImage(src);
        return;
      } catch (_) {
        // Fall through to the built-in synthetic scene below.
      }
    }
    source = await loadFallbackDemo();
  }

  function captureLatest() {
    const width = source?.videoWidth || source?.naturalWidth;
    const height = source?.videoHeight || source?.naturalHeight;
    if (!source || !width || !height) throw new Error("No current camera or demo frame is available.");
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d", { alpha: false }).drawImage(source, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.82));
  }

  return { start, switchCamera, stop, useDemo, captureLatest };
})();
