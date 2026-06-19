const DEFAULT_OPTIONS = {
  size: 504,
  recordMs: 3000,
  captureFps: 12,
  playFps: 30,
  playbackMs: 3000,
  loops: 3,
  fadeMs: 260,
};

function readCameraZoom(videoEl) {
  const style = getComputedStyle(videoEl);
  const zoom = Number.parseFloat(style.getPropertyValue("--camera-zoom"));
  return Number.isFinite(zoom) && zoom > 0 ? zoom : 1;
}

function drawCameraFrame(ctx, videoEl, size) {
  const videoWidth = videoEl.videoWidth;
  const videoHeight = videoEl.videoHeight;
  if (!videoWidth || !videoHeight) return false;

  const zoom = readCameraZoom(videoEl);
  const sourceSize = Math.min(videoWidth, videoHeight) / zoom;
  const sourceX = (videoWidth - sourceSize) / 2;
  const sourceY = (videoHeight - sourceSize) / 2;

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, size, size);
  ctx.setTransform(-1, 0, 0, 1, size, 0);
  ctx.drawImage(videoEl, sourceX, sourceY, sourceSize, sourceSize, 0, 0, size, size);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  return true;
}

function cloneCanvas(source) {
  const frame = document.createElement("canvas");
  frame.width = source.width;
  frame.height = source.height;
  frame.getContext("2d")?.drawImage(source, 0, 0);
  return frame;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function nextFrame() {
  return new Promise((resolve) => requestAnimationFrame(resolve));
}

export function createBoomerangRecorder(videoEl, outputCanvas, options = {}) {
  const config = { ...DEFAULT_OPTIONS, ...options };
  const captureCanvas = document.createElement("canvas");
  captureCanvas.width = config.size;
  captureCanvas.height = config.size;
  const captureCtx = captureCanvas.getContext("2d", { alpha: false });
  const outputCtx = outputCanvas?.getContext("2d", { alpha: false });

  let frames = [];
  let recording = false;
  let playing = false;
  let lastCaptureAt = 0;
  let playToken = 0;

  if (outputCanvas) {
    outputCanvas.width = config.size;
    outputCanvas.height = config.size;
  }

  function trimFrames(now) {
    const cutoff = now - config.recordMs;
    frames = frames.filter((frame) => frame.ts >= cutoff);
  }

  function hideOutput() {
    if (!outputCanvas) return;
    outputCanvas.hidden = true;
    outputCanvas.classList.remove("camera-slot__boomerang--active");
    outputCtx?.clearRect(0, 0, outputCanvas.width, outputCanvas.height);
  }

  return {
    start() {
      if (recording || !captureCtx) return;
      recording = true;
      lastCaptureAt = 0;
    },
    capture(now = performance.now()) {
      if (!recording || !captureCtx) return;
      const frameInterval = 1000 / config.captureFps;
      if (now - lastCaptureAt < frameInterval) return;
      if (!drawCameraFrame(captureCtx, videoEl, config.size)) return;
      lastCaptureAt = now;
      frames.push({ ts: now, canvas: cloneCanvas(captureCanvas) });
      trimFrames(now);
    },
    stop() {
      recording = false;
    },
    discard() {
      this.stop();
      frames = [];
      hideOutput();
    },
    clear() {
      this.stop();
      playing = false;
      playToken += 1;
      frames = [];
      hideOutput();
    },
    frameCount() {
      return frames.length;
    },
    hasFrames() {
      return frames.length > 2;
    },
    async play({ durationMs = config.playbackMs, loops = config.loops } = {}) {
      this.stop();
      if (!outputCanvas || !outputCtx || frames.length <= 2) return false;

      const token = playToken + 1;
      playToken = token;
      playing = true;
      outputCanvas.hidden = false;
      outputCanvas.classList.add("camera-slot__boomerang--active");

      const forward = frames.map((frame) => frame.canvas);
      const backward = forward.slice(1, -1).reverse();
      const sequence = [...forward, ...backward];
      outputCtx.drawImage(sequence[0], 0, 0, outputCanvas.width, outputCanvas.height);
      await nextFrame();
      outputCanvas.classList.add("camera-slot__boomerang--active");
      await delay(config.fadeMs);

      const frameInterval = 1000 / config.playFps;
      for (let loop = 0; loop < loops && playing && token === playToken; loop += 1) {
        const startAt = performance.now();
        while (playing && token === playToken) {
          const elapsed = performance.now() - startAt;
          const progress = Math.min(1, elapsed / durationMs);
          const index = Math.min(sequence.length - 1, Math.floor(progress * sequence.length));
          outputCtx.drawImage(sequence[index], 0, 0, outputCanvas.width, outputCanvas.height);
          if (progress >= 1) break;
          await delay(frameInterval);
        }
      }

      if (token === playToken) {
        playing = false;
        outputCanvas.classList.remove("camera-slot__boomerang--active");
        await delay(config.fadeMs);
        hideOutput();
      }
      return true;
    },
  };
}
