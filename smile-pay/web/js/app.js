import {
  createSmileStage,
  STAGES,
  STAGE_ALIASES,
  resolveStage,
} from "./smile-stage.js?v=20260611-detection-zoom";
import { loadCopyLines } from "./copy-lines.js";
import { createSmileWatcher } from "./smile-capture.js?v=20260611-detection-zoom";
import { createFacePresenceWatcher } from "./face-presence.js?v=20260611-detection-zoom";

const params = new URLSearchParams(window.location.search);
const stageParam = params.get("stage");
const demo = params.has("demo");
const debug = params.has("debug");
const live = !params.has("nostage") && !stageParam && !demo;

const PRESENCE = {
  minFaceSize: 0.10,
  holdMs: 450,
  releaseMs: 1400,
  detectStride: 6,
};

const SMILE_HOLD = {
  requiredMs: 3000,
  successPauseMs: 2000,
};

const SMILE = {
  threshold: 0.42,
  holdMs: SMILE_HOLD.requiredMs,
  minFaceSize: 0.14,
  releaseMs: 1500,
  detectStride: 4,
};

const stageRoot = document.getElementById("stage-root");
const cameraSlot = document.getElementById("camera-slot");
const video = document.getElementById("preview");
const snapshot = document.getElementById("snapshot");
const statusEl = document.getElementById("smile-status");

const stage = createSmileStage(stageRoot, { debug });

let stream = null;
let presenceWatcher = null;
let smileWatcher = null;
/** @type {"idle"|"face"|"animating"} */
let phase = "idle";
let busy = false;
let lastBottomLineIndex = -1;

function setStatus(text) {
  if (!statusEl) return;
  statusEl.textContent = text;
  statusEl.hidden = !text;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function captureBlob() {
  const w = video.videoWidth || 720;
  const h = video.videoHeight || 720;
  snapshot.width = w;
  snapshot.height = h;
  const ctx = snapshot.getContext("2d");
  ctx.translate(w, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(video, 0, 0, w, h);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  return new Promise((resolve) => {
    snapshot.toBlob((blob) => resolve(blob), "image/jpeg", 0.92);
  });
}

async function uploadCapture(blob) {
  const form = new FormData();
  form.append("photo", blob, "smile.jpg");
  const res = await fetch("/api/capture", { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

async function stopSmileWatcher() {
  await smileWatcher?.close?.();
  smileWatcher = null;
}

async function stopPresenceWatcher() {
  await presenceWatcher?.close?.();
  presenceWatcher = null;
}

async function onSmileDetected() {
  if (busy || phase !== "face") return;
  busy = true;
  phase = "animating";
  smileWatcher?.stop();
  stage.completeSmileHoldText();
  setStatus("");

  try {
    await delay(SMILE_HOLD.successPauseMs);

    const blob = await captureBlob();
    try {
      await uploadCapture(blob);
    } catch (err) {
      console.warn("Capture API:", err);
    }

    stage.playPostSmileSequence({
      onComplete: () => beginLiveSession(),
      skipLine: true,
    });
  } catch (err) {
    console.error(err);
    busy = false;
    phase = "idle";
    stage.hideCamera();
    await beginLiveSession();
  }
}

function updateSmileUi({ phase: p, smileMs = 0 }) {
  if (busy || phase !== "face") return;
  if (p === "smile") {
    const progress = Math.min(1, smileMs / SMILE_HOLD.requiredMs);
    stage.setSmileHoldProgress(progress);
    setStatus("");
    return;
  }

  stage.fadeSmileHoldText();
  if (p === "almost") setStatus("Удерживайте улыбку");
  else if (p === "wait_face") setStatus("");
  else if (p === "ready") setStatus("Улыбнитесь!");
}

async function startSmileWatcher() {
  await stopSmileWatcher();
  smileWatcher = await createSmileWatcher(video, {
    ...SMILE,
    onStatus: updateSmileUi,
    onSmile: () => onSmileDetected(),
    onLost: () => {
      if (phase === "face" && !busy) {
        phase = "idle";
        stage.hideCamera();
        setStatus("");
        stopSmileWatcher().then(() => startPresenceWatcher());
      }
    },
    onError: (e) => console.warn("smile", e),
  });
  smileWatcher.start();
}

async function onFaceReady() {
  if (busy || phase !== "idle") return;
  phase = "face";
  await stopPresenceWatcher();
  pickBottomLineForAttempt();
  stage.revealCamera();
  setStatus("Улыбнитесь!");
  try {
    await startSmileWatcher();
  } catch (err) {
    console.warn(err);
    setStatus("Детект улыбки недоступен");
  }
}

function pickBottomLineForAttempt() {
  const lines = stage.getCopy().bottomLines ?? [];
  if (lines.length <= 1) {
    stage.setBottomLineIndex(0);
    lastBottomLineIndex = 0;
    return;
  }

  let nextIndex = Math.floor(Math.random() * lines.length);
  if (nextIndex === lastBottomLineIndex) {
    nextIndex = (nextIndex + 1) % lines.length;
  }
  lastBottomLineIndex = nextIndex;
  stage.setBottomLineIndex(nextIndex);
}

async function onFaceLost() {
  if (busy || phase === "animating") return;
  if (phase === "face") {
    phase = "idle";
    await stopSmileWatcher();
    stage.hideCamera();
    setStatus("");
    await startPresenceWatcher();
  }
}

async function startPresenceWatcher() {
  if (phase !== "idle" || busy) return;
  await stopPresenceWatcher();
  try {
    presenceWatcher = await createFacePresenceWatcher(video, {
      ...PRESENCE,
      keepOnly: false,
      onReady: () => onFaceReady(),
      onLost: () => onFaceLost(),
      onStatus: ({ phase: p }) => {
        if (phase === "idle" && p === "too_far") setStatus("");
      },
      onError: (e) => console.warn("presence", e),
    });
    presenceWatcher.start();
  } catch (err) {
    setStatus("Детект лица недоступен. scripts\\download_smile_model.ps1");
    console.warn(err);
  }
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) return false;
  if (stream) return true;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 720 }, height: { ideal: 720 } },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    cameraSlot.removeAttribute("aria-hidden");
    return true;
  } catch (err) {
    console.warn("Камера недоступна:", err);
    return false;
  }
}

async function beginLiveSession() {
  busy = false;
  phase = "idle";
  stage.reset();
  await stopSmileWatcher();
  await stopPresenceWatcher();

  const ok = await startCamera();
  if (!ok) {
    setStatus("Камера недоступна — ?demo=1");
    return;
  }
  await startPresenceWatcher();
}

function runDemoSequence() {
  busy = true;
  phase = "animating";
  stage.revealCamera();
  setTimeout(() => {
    stage.playPostSmileSequence({
      onComplete: () => {
        // Автовозврат в idle (как в live), затем повтор цикла для наглядности
        busy = false;
        phase = "idle";
        stage.reset();
        setTimeout(runDemoSequence, 2000);
      },
    });
  }, 900);
}

function applyStagePreview(id) {
  const resolved = resolveStage(id);
  busy = false;
  phase = resolved === "idle" ? "idle" : "animating";
  stage.setStage(resolved);
  if (resolved === "face" || resolved === "line") {
    stage.root.classList.add("smile-stage--cam-open");
  }
  if (resolved === "line") {
    stage.root.classList.add("smile-stage--line-expanded");
  }
  if (resolved === "stickers") {
    stage.root.classList.add("smile-stage--stickers-in");
  }
  if (resolved === "qr") {
    stage.root.classList.add("smile-stage--dissolve");
  }
}

async function init() {
  const copy = await loadCopyLines();
  stage.applyCopy(copy);

  const previewId = stageParam ? resolveStage(stageParam) : null;
  if (previewId && (STAGES.includes(previewId) || STAGE_ALIASES[stageParam])) {
    applyStagePreview(stageParam);
    return;
  }

  if (demo) {
    stage.setStage("idle");
    setTimeout(runDemoSequence, 600);
    return;
  }

  if (live) {
    await beginLiveSession();
    return;
  }

  stage.setStage("idle");
}

init();

window.addEventListener("beforeunload", () => {
  stopSmileWatcher();
  stopPresenceWatcher();
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
  }
});
