/**
 * Ожидание гостя: лицо достаточно крупное → открываем «окно» камеры.
 */

import { createFaceLandmarker, faceBounds } from "./face-landmarker.js";

export async function createFacePresenceWatcher(videoEl, options = {}) {
  const {
    minFaceSize = 0.2,
    holdFrames = 10,
    releaseFrames = 16,
    holdMs = 400,
    releaseMs = 1200,
    detectStride = 8,
    keepOnly = false,
    onReady,
    onLost,
    onStatus,
    onError,
  } = options;

  let landmarker;
  try {
    landmarker = await createFaceLandmarker();
  } catch (err) {
    onError?.(err);
    throw err;
  }

  let running = false;
  let rafId = 0;
  let closeHold = 0;
  let awayHold = 0;
  let closeSince = 0;
  let awaySince = 0;
  let frameTick = 0;
  const stride = Math.max(1, Math.floor(detectStride));
  const readyMs = Number.isFinite(Number(holdMs)) ? Math.max(0, Number(holdMs)) : null;
  const lostMs = Number.isFinite(Number(releaseMs)) ? Math.max(0, Number(releaseMs)) : null;

  function tick() {
    if (!running) return;
    if (videoEl.readyState < 2) {
      rafId = requestAnimationFrame(tick);
      return;
    }

    frameTick += 1;
    if (frameTick % stride !== 0) {
      rafId = requestAnimationFrame(tick);
      return;
    }

    const ts = performance.now();
    const result = landmarker.detectForVideo(videoEl, ts);
    const landmarks = result?.faceLandmarks?.[0];
    const bounds = faceBounds(landmarks);
    const size = bounds?.size ?? 0;
    const closeEnough = size >= minFaceSize;

    if (closeEnough) {
      awayHold = 0;
      awaySince = 0;
      if (!closeSince) closeSince = ts;
      if (keepOnly) {
        onStatus?.({ phase: "present", size, minFaceSize });
      } else {
        closeHold += 1;
        const closeMs = ts - closeSince;
        onStatus?.({
          phase: "approaching",
          size,
          minFaceSize,
          closeHold,
          holdFrames,
          closeMs,
          holdMs: readyMs,
        });
        if (
          (readyMs == null && closeHold >= holdFrames) ||
          (readyMs != null && closeMs >= readyMs)
        ) {
          running = false;
          onReady?.({ size });
          return;
        }
      }
    } else if (landmarks) {
      closeSince = 0;
      if (keepOnly) {
        awayHold += 1;
        if (!awaySince) awaySince = ts;
        const awayMs = ts - awaySince;
        onStatus?.({ phase: "too_far", size, minFaceSize, awayHold, releaseFrames, awayMs, releaseMs: lostMs });
        if (
          (lostMs == null && awayHold >= releaseFrames) ||
          (lostMs != null && awayMs >= lostMs)
        ) {
          onLost?.();
          awayHold = 0;
          awaySince = 0;
        }
      } else {
        closeHold = Math.max(0, closeHold - 1);
        closeSince = 0;
        onStatus?.({ phase: "too_far", size, minFaceSize, closeHold, holdFrames });
      }
    } else {
      closeHold = 0;
      closeSince = 0;
      awayHold += 1;
      if (!awaySince) awaySince = ts;
      const awayMs = ts - awaySince;
      onStatus?.({ phase: "no_face", size: 0, minFaceSize, awayHold, releaseFrames, awayMs, releaseMs: lostMs });
      if (
        (lostMs == null && awayHold >= releaseFrames) ||
        (lostMs != null && awayMs >= lostMs)
      ) {
        onLost?.();
        awayHold = 0;
        awaySince = 0;
      }
    }

    rafId = requestAnimationFrame(tick);
  }

  return {
    start() {
      if (running) return;
      running = true;
      closeHold = 0;
      awayHold = 0;
      closeSince = 0;
      awaySince = 0;
      frameTick = 0;
      onStatus?.({ phase: "watching", size: 0, minFaceSize, closeHold: 0, holdFrames });
      rafId = requestAnimationFrame(tick);
    },
    stop() {
      running = false;
      cancelAnimationFrame(rafId);
    },
    resetHold() {
      closeHold = 0;
      awayHold = 0;
      closeSince = 0;
      awaySince = 0;
    },
    async close() {
      this.stop();
      landmarker?.close?.();
    },
  };
}
