/**
 * MediaPipe Face Landmarker для детекта улыбки.
 */

const MP_PKG = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";
const WASM_DIR = `${MP_PKG}/wasm`;
const MODEL_REMOTE =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const MODEL_LOCAL = "/static/models/face_landmarker.task";

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

async function resolveModelUrl() {
  try {
    const head = await fetch(MODEL_LOCAL, { method: "HEAD" });
    if (head.ok) return MODEL_LOCAL;
  } catch {
    /* offline or missing file */
  }
  return MODEL_REMOTE;
}

export async function createFaceLandmarker() {
  modelUrlPromise ||= resolveModelUrl();
  tasksVisionPromise ||= import(MP_PKG);

  const modelUrl = await modelUrlPromise;
  const { FaceLandmarker, FilesetResolver } = await tasksVisionPromise;
  visionPromise ||= FilesetResolver.forVisionTasks(WASM_DIR);
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
