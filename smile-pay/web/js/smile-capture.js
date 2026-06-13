/**
 * Снимок по улыбке (MediaPipe Face Landmarker, blendshapes).
 */

import { createFaceLandmarker, faceBounds, getDetectionFrame } from "./face-landmarker.js?v=20260613-fast-acquire";

export async function createSmileWatcher(videoEl, options = {}) {
  const {
    threshold = 0.42,
    holdFrames = 12,
    holdMs = 650,
    minFaceSize = 0.17,
    releaseMs = 1600,
    detectStride = 6,
    onSmile,
    onLost,
    onStatus,
    onError,
  } = options;

  let landmarker;
  try {
    landmarker = await createFaceLandmarker();
  } catch (err) {
    onError?.(err);
    throw new Error(
      `MediaPipe: ${err.message}. Локальная модель: scripts\\download_smile_model.ps1`,
    );
  }

  let running = false;
  let rafId = 0;
  let hold = 0;
  let smileSince = 0;
  let awaySince = 0;
  let frameTick = 0;
  const stride = Math.max(1, Math.floor(detectStride));
  const readyMs = Number.isFinite(Number(holdMs)) ? Math.max(0, Number(holdMs)) : null;
  const lostMs = Math.max(0, Number(releaseMs) || 0);

  function smileScore(result) {
    const blends = result?.faceBlendshapes?.[0];
    if (!blends?.categories) return 0;
    let left = 0;
    let right = 0;
    for (const c of blends.categories) {
      if (c.categoryName === "mouthSmileLeft") left = c.score;
      if (c.categoryName === "mouthSmileRight") right = c.score;
    }
    return (left + right) / 2;
  }

  function tick() {
    if (!running || videoEl.readyState < 2) {
      rafId = requestAnimationFrame(tick);
      return;
    }
    frameTick += 1;
    if (frameTick % stride !== 0) {
      rafId = requestAnimationFrame(tick);
      return;
    }
    const ts = performance.now();
    const result = landmarker.detectForVideo(getDetectionFrame(videoEl), ts);

    const landmarks = result?.faceLandmarks?.[0];
    const bounds = faceBounds(landmarks);
    const faceSize = bounds?.size ?? 0;
    const faceReady = faceSize >= minFaceSize;
    const score = faceReady ? smileScore(result) : 0;

    if (!faceReady) {
      hold = 0;
      smileSince = 0;
      if (!awaySince) awaySince = ts;
      const awayMs = ts - awaySince;
      onStatus?.({ phase: "wait_face", score, hold, holdFrames, faceSize, minFaceSize });
      if (lostMs > 0 && awayMs >= lostMs) {
        awaySince = 0;
        onLost?.();
      }
    } else if (score >= threshold) {
      awaySince = 0;
      if (!smileSince) smileSince = ts;
      hold += 1;
      const smileMs = ts - smileSince;
      onStatus?.({ phase: "smile", score, hold, holdFrames, smileMs, holdMs: readyMs });
      if (
        (readyMs == null && hold >= holdFrames) ||
        (readyMs != null && smileMs >= readyMs)
      ) {
        running = false;
        cancelAnimationFrame(rafId);
        onSmile?.({ score });
        return;
      }
    } else {
      awaySince = 0;
      smileSince = 0;
      hold = Math.max(0, hold - 1);
      onStatus?.({ phase: "almost", score, hold, holdFrames, smileMs: 0, holdMs: readyMs });
    }
    rafId = requestAnimationFrame(tick);
  }

  return {
    start() {
      if (running) return;
      running = true;
      hold = 0;
      smileSince = 0;
      awaySince = 0;
      frameTick = 0;
      onStatus?.({ phase: "ready", score: 0, hold: 0, holdFrames });
      rafId = requestAnimationFrame(tick);
    },
    stop() {
      running = false;
      cancelAnimationFrame(rafId);
    },
    async close() {
      this.stop();
      landmarker?.close?.();
    },
  };
}
