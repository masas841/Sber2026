/**
 * Общая инициализация MediaPipe Face Landmarker для киоска.
 */

const MP_VERSION = "0.10.14";
const MP_CDN = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VERSION}`;
const MP_LOCAL_BASE = "/static/vendor/mediapipe/tasks-vision";
const MODEL_REMOTE =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const MODEL_LOCAL = "/static/models/face_landmarker.task";

let assetsPromise = null;
let modelUrlPromise = null;
let tasksVisionPromise = null;
let visionPromise = null;

async function probeOk(url) {
  try {
    const head = await fetch(url, { method: "HEAD" });
    return head.ok;
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
  if (await probeOk(localBundle)) {
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
