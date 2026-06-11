/**
 * Общая инициализация MediaPipe Face Landmarker для киоска.
 */

const MP_PKG = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";
const WASM_DIR = `${MP_PKG}/wasm`;
const MODEL_REMOTE =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const MODEL_LOCAL = "/static/models/face_landmarker.task";

let modelUrlPromise = null;
let tasksVisionPromise = null;
let visionPromise = null;

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

/** Нормализованный bbox лица (0..1) по landmarks. */
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
