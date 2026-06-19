/**
 * MediaPipe Face Landmarker для детекта улыбки.
 * Локальные assets в /static/vendor и /static/models; CDN только как fallback.
 */

const MP_VERSION = "0.10.14";
const MP_CDN = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VERSION}`;
const MP_LOCAL_BASE = "/static/vendor/mediapipe/tasks-vision";
const MIN_INTERNAL_WASM_BYTES = 9_000_000;
const MODEL_REMOTE =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const MODEL_LOCAL = "/static/models/face_landmarker.task";

let assetsPromise = null;
let modelUrlPromise = null;
let tasksVisionPromise = null;
let visionPromise = null;
let detectionCanvas = null;
let detectionCtx = null;

function cameraZoomFor(videoEl) {
  const style = getComputedStyle(videoEl);
  const detectionZoom = Number.parseFloat(style.getPropertyValue("--detection-zoom"));
  const cameraZoom = Number.parseFloat(style.getPropertyValue("--camera-zoom"));
  const zoom = Number.isFinite(detectionZoom) && detectionZoom > 0 ? detectionZoom : cameraZoom;
  return Number.isFinite(zoom) && zoom > 0 ? zoom : 1;
}

async function probeOk(url) {
  try {
    const head = await fetch(url, { method: "HEAD" });
    return head.ok;
  } catch {
    return false;
  }
}

async function probeMinSize(url, minBytes) {
  try {
    const head = await fetch(url, { method: "HEAD" });
    if (!head.ok) return false;
    const size = Number(head.headers.get("content-length"));
    return Number.isFinite(size) && size >= minBytes;
  } catch {
    return false;
  }
}

async function resolveModelUrl() {
  if (await probeOk(MODEL_LOCAL)) return MODEL_LOCAL;
  return MODEL_REMOTE;
}

async function resolveMediaPipeAssets() {
  const localBundle = `${MP_LOCAL_BASE}/vision_bundle.mjs`;
  const localWasm = `${MP_LOCAL_BASE}/wasm/vision_wasm_internal.wasm`;
  if (await probeOk(localBundle) && await probeMinSize(localWasm, MIN_INTERNAL_WASM_BYTES)) {
    return {
      importUrl: localBundle,
      wasmDir: `${MP_LOCAL_BASE}/wasm`,
    };
  }
  return {
    importUrl: MP_CDN,
    wasmDir: `${MP_CDN}/wasm`,
  };
}

export async function createFaceLandmarker() {
  assetsPromise ||= resolveMediaPipeAssets();
  modelUrlPromise ||= resolveModelUrl();
  tasksVisionPromise ||= assetsPromise.then(({ importUrl }) => import(importUrl));

  const [{ wasmDir }, modelUrl, { FaceLandmarker, FilesetResolver }] = await Promise.all([
    assetsPromise,
    modelUrlPromise,
    tasksVisionPromise,
  ]);

  visionPromise ||= FilesetResolver.forVisionTasks(wasmDir);
  const vision = await visionPromise;
  const baseOpts = {
    baseOptions: { modelAssetPath: modelUrl },
    runningMode: "VIDEO",
    numFaces: 1,
    minFaceDetectionConfidence: 0.05,
    minFacePresenceConfidence: 0.05,
    minTrackingConfidence: 0.05,
    outputFaceBlendshapes: true,
  };

  try {
    return await FaceLandmarker.createFromOptions(vision, {
      ...baseOpts,
      baseOptions: { ...baseOpts.baseOptions, delegate: "GPU" },
    });
  } catch {
    return FaceLandmarker.createFromOptions(vision, {
      ...baseOpts,
      baseOptions: { ...baseOpts.baseOptions, delegate: "CPU" },
    });
  }
}

export function getDetectionFrame(videoEl) {
  const width = videoEl.videoWidth || videoEl.clientWidth;
  const height = videoEl.videoHeight || videoEl.clientHeight;
  if (!width || !height) return videoEl;

  detectionCanvas ||= document.createElement("canvas");
  detectionCtx ||= detectionCanvas.getContext("2d", { alpha: false });
  if (!detectionCtx) return videoEl;

  if (detectionCanvas.width !== width) detectionCanvas.width = width;
  if (detectionCanvas.height !== height) detectionCanvas.height = height;

  const zoom = cameraZoomFor(videoEl);
  const sourceWidth = width / zoom;
  const sourceHeight = height / zoom;
  const sourceX = (width - sourceWidth) / 2;
  const sourceY = (height - sourceHeight) / 2;

  detectionCtx.setTransform(-1, 0, 0, -1, width, height);
  detectionCtx.drawImage(
    videoEl,
    sourceX,
    sourceY,
    sourceWidth,
    sourceHeight,
    0,
    0,
    width,
    height,
  );
  detectionCtx.setTransform(1, 0, 0, 1, 0, 0);
  return detectionCanvas;
}

export function faceBounds(landmarks) {
  if (!landmarks?.length) return null;
  let minX = 1;
  let minY = 1;
  let maxX = 0;
  let maxY = 0;
  for (const p of landmarks) {
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x);
    maxY = Math.max(maxY, p.y);
  }
  const width = maxX - minX;
  const height = maxY - minY;
  return {
    width,
    height,
    size: Math.max(width, height),
    cx: (minX + maxX) / 2,
    cy: (minY + maxY) / 2,
  };
}
