import {
  createSmileStage,
  STAGES,
  STAGE_ALIASES,
  resolveStage,
} from "./smile-stage.js?v=20260619-boomerang";
import { loadCopyLines } from "./copy-lines.js";
import { createSmileWatcher } from "./smile-capture.js?v=20260619-diag";
import { createFacePresenceWatcher } from "./face-presence.js?v=20260619-diag";
import { createBoomerangRecorder } from "./boomerang-recorder.js?v=20260619-boomerang";
import { initKioskInstallGate } from "./kiosk-install-mode.js?v=20260619-install-timeout";

const params = new URLSearchParams(window.location.search);
const stageParam = params.get("stage");
const demo = params.has("demo");
const debug = params.has("debug");
const diag = params.has("diag");
const live = !params.has("nostage") && !stageParam && !demo;

const HOURLY_REFRESH_MS = 60 * 60 * 1000;

const PRESENCE = {
  minFaceSize: 0.025,
  holdMs: 180,
  releaseMs: 1400,
  detectStride: 6,
};

const SMILE_HOLD = {
  requiredMs: 3000,
};

const SMILE = {
  threshold: 0.21,
  holdMs: SMILE_HOLD.requiredMs,
  minFaceSize: 0.07,
  releaseMs: 1500,
  detectStride: 4,
};

const stageRoot = document.getElementById("stage-root");
const cameraSlot = document.getElementById("camera-slot");
const video = document.getElementById("preview");
const boomerangCanvas = document.getElementById("boomerang");
const snapshot = document.getElementById("snapshot");
const statusEl = document.getElementById("smile-status");

const stage = createSmileStage(stageRoot, { debug });
const boomerang = createBoomerangRecorder(video, boomerangCanvas);

let stream = null;
let presenceWatcher = null;
let smileWatcher = null;
/** @type {"idle"|"face"|"animating"} */
let phase = "idle";
let busy = false;
let lastBottomLineIndex = -1;
const diagState = {};
const diagEl = diag ? document.createElement("pre") : null;

if (diagEl) {
  diagEl.className = "smile-diag";
  diagEl.setAttribute("aria-live", "polite");
  document.body.appendChild(diagEl);
  window.__smileDiag = diagState;
}

function fmt(value) {
  if (value == null) return "-";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  if (typeof value === "boolean") return value ? "yes" : "no";
  return String(value);
}

function diagUpdate(next) {
  if (!diagEl) return;
  Object.assign(diagState, next, { updatedAt: new Date().toLocaleTimeString("ru-RU") });
  window.__smileDiag = diagState;
  diagEl.textContent = [
    "Smile Pay diag",
    `time: ${diagState.updatedAt}`,
    `mode: live=${fmt(live)} demo=${fmt(demo)} stage=${fmt(stageParam)} debug=${fmt(debug)}`,
    `app: phase=${fmt(phase)} busy=${fmt(busy)} stage=${fmt(stage.root?.dataset.stage)}`,
    `install: ${fmt(diagState.install)}`,
    `camera: ${fmt(diagState.camera)} ${fmt(diagState.cameraError)}`,
    `video: ready=${fmt(video.readyState)} ${fmt(video.videoWidth)}x${fmt(video.videoHeight)} paused=${fmt(video.paused)} stream=${fmt(Boolean(video.srcObject))}`,
    `track: ${fmt(diagState.track)}`,
    `presence: ${fmt(diagState.presence)} size=${fmt(diagState.presenceSize)} min=${fmt(diagState.presenceMin)} hold=${fmt(diagState.presenceHold)} ms=${fmt(diagState.presenceMs)}`,
    `smile: ${fmt(diagState.smile)} score=${fmt(diagState.smileScore)} size=${fmt(diagState.smileSize)} min=${fmt(diagState.smileMin)} ms=${fmt(diagState.smileMs)}`,
    `boomerang: ${fmt(diagState.boomerang)} frames=${fmt(diagState.boomerangFrames)} played=${fmt(diagState.boomerangPlayed)}`,
    `error: ${fmt(diagState.error)}`,
  ].join("\n");
}

if (diag) {
  window.addEventListener("error", (event) => {
    diagUpdate({ error: `window: ${event.message}` });
  });
  window.addEventListener("unhandledrejection", (event) => {
    diagUpdate({ error: `promise: ${event.reason?.message ?? event.reason}` });
  });
  for (const eventName of ["loadedmetadata", "playing", "pause", "stalled", "error"]) {
    video.addEventListener(eventName, () => {
      diagUpdate({
        camera: `video:${eventName}`,
        cameraError: video.error ? `${video.error.code}: ${video.error.message}` : "",
      });
    });
  }
}

function setStatus(text) {
  if (!statusEl) return;
  statusEl.textContent = text;
  statusEl.hidden = !text;
}

function scheduleHourlyRefresh() {
  if (!live) return;
  window.setTimeout(() => {
    window.location.reload();
  }, HOURLY_REFRESH_MS);
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
  diagUpdate({ smile: "stopped" });
}

async function stopPresenceWatcher() {
  await presenceWatcher?.close?.();
  presenceWatcher = null;
  diagUpdate({ presence: "stopped" });
}

async function onSmileDetected() {
  if (busy || phase !== "face") return;
  busy = true;
  phase = "animating";
  boomerang.stop();
  diagUpdate({ smile: "detected", boomerang: "stopped", boomerangFrames: boomerang.frameCount() });
  smileWatcher?.stop();
  stage.completeSmileHoldText();
  setStatus("");

  try {
    const blob = await captureBlob();
    uploadCapture(blob).catch((err) => console.warn("Capture API:", err));

    stage.showLine();
    await stage.waitForLineText();
    diagUpdate({ boomerang: "playing", boomerangFrames: boomerang.frameCount() });
    const played = await boomerang.play({ loops: 3 });
    diagUpdate({ boomerang: played ? "played" : "skipped", boomerangPlayed: played });

    stage.playPostSmileSequence({
      onComplete: () => beginLiveSession(),
      skipLine: true,
    });
  } catch (err) {
    console.error(err);
    diagUpdate({ error: `smile detected flow: ${err?.message ?? err}` });
    busy = false;
    phase = "idle";
    boomerang.clear();
    stage.hideCamera();
    await beginLiveSession();
  }
}

function updateSmileUi({ phase: p, smileMs = 0, score = 0, faceSize = 0, minFaceSize = 0 }) {
  if (busy || phase !== "face") return;
  diagUpdate({
    smile: p,
    smileScore: score,
    smileSize: faceSize,
    smileMin: minFaceSize,
    smileMs,
  });
  if (p === "smile") {
    boomerang.start();
    boomerang.capture();
    diagUpdate({ boomerang: "recording", boomerangFrames: boomerang.frameCount() });
    const progress = Math.min(1, smileMs / SMILE_HOLD.requiredMs);
    stage.setSmileHoldProgress(progress);
    setStatus("");
    return;
  }

  boomerang.discard();
  diagUpdate({ boomerang: "discarded", boomerangFrames: 0 });
  stage.fadeSmileHoldText();
  if (p === "almost") setStatus("Удерживайте улыбку");
  else if (p === "wait_face") setStatus("");
  else if (p === "ready") setStatus("Улыбнитесь!");
}

async function startSmileWatcher() {
  await stopSmileWatcher();
  diagUpdate({ smile: "creating" });
  smileWatcher = await createSmileWatcher(video, {
    ...SMILE,
    onStatus: updateSmileUi,
    onSmile: () => onSmileDetected(),
    onLost: () => {
      if (phase === "face" && !busy) {
        phase = "idle";
        boomerang.discard();
        stage.hideCamera();
        setStatus("");
        stopSmileWatcher().then(() => startPresenceWatcher());
      }
    },
    onError: (e) => {
      console.warn("smile", e);
      diagUpdate({ error: `smile: ${e?.message ?? e}` });
    },
  });
  smileWatcher.start();
  diagUpdate({ smile: "started" });
}

async function onFaceReady() {
  if (busy || phase !== "idle") return;
  phase = "face";
  diagUpdate({ presence: "ready" });
  await stopPresenceWatcher();
  pickBottomLineForAttempt();
  stage.revealCamera();
  setStatus("Улыбнитесь!");
  try {
    await startSmileWatcher();
  } catch (err) {
    console.warn(err);
    diagUpdate({ error: `startSmileWatcher: ${err?.message ?? err}` });
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
    boomerang.discard();
    stage.hideCamera();
    setStatus("");
    await startPresenceWatcher();
  }
}

async function startPresenceWatcher() {
  if (phase !== "idle" || busy) return;
  await stopPresenceWatcher();
  try {
    diagUpdate({ presence: "creating" });
    presenceWatcher = await createFacePresenceWatcher(video, {
      ...PRESENCE,
      keepOnly: false,
      onReady: () => onFaceReady(),
      onLost: () => onFaceLost(),
      onStatus: ({ phase: p, size = 0, minFaceSize = 0, closeHold = 0, closeMs = 0, awayMs = 0 }) => {
        diagUpdate({
          presence: p,
          presenceSize: size,
          presenceMin: minFaceSize,
          presenceHold: closeHold,
          presenceMs: closeMs || awayMs,
        });
        if (phase === "idle" && p === "too_far") setStatus("");
      },
      onError: (e) => {
        console.warn("presence", e);
        diagUpdate({ error: `presence: ${e?.message ?? e}` });
      },
    });
    presenceWatcher.start();
    diagUpdate({ presence: "started" });
  } catch (err) {
    setStatus("Детект лица недоступен. scripts\\download_smile_model.ps1");
    diagUpdate({ error: `startPresenceWatcher: ${err?.message ?? err}` });
    console.warn(err);
  }
}

async function startCamera() {
  diagUpdate({ camera: "checking mediaDevices" });
  if (!navigator.mediaDevices?.getUserMedia) {
    diagUpdate({ camera: "unsupported", cameraError: "navigator.mediaDevices.getUserMedia missing" });
    return false;
  }
  if (stream) {
    diagUpdate({ camera: "reusing stream" });
    return true;
  }
  try {
    diagUpdate({ camera: "requesting 1920x1080" });
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    const track = stream.getVideoTracks()[0];
    const settings = track?.getSettings?.() ?? {};
    diagUpdate({
      camera: "playing",
      cameraError: "",
      track: `${settings.width ?? "?"}x${settings.height ?? "?"} ${settings.frameRate ?? "?"}fps ${track?.readyState ?? "?"} ${track?.label ?? ""}`,
    });
    cameraSlot.removeAttribute("aria-hidden");
    return true;
  } catch (err) {
    console.warn("Камера недоступна:", err);
    diagUpdate({ camera: "failed", cameraError: `${err?.name ?? "Error"}: ${err?.message ?? err}` });
    return false;
  }
}

async function beginLiveSession() {
  busy = false;
  phase = "idle";
  diagUpdate({ camera: "begin live", error: "" });
  boomerang.clear();
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
  diagUpdate({ install: "checking" });
  const installGate = await initKioskInstallGate({
    activityId: "smile-pay",
    standbyEl: document.getElementById("kiosk-install-standby"),
    mainEl: document.getElementById("shell"),
  });
  diagUpdate({ install: installGate.installOff ? "off" : "on" });
  if (installGate.installOff) return;

  const copy = await loadCopyLines();
  diagUpdate({ install: "on; copy loaded" });
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
    scheduleHourlyRefresh();
    await beginLiveSession();
    return;
  }

  stage.setStage("idle");
}

init();

window.addEventListener("beforeunload", () => {
  stopSmileWatcher();
  stopPresenceWatcher();
  boomerang.clear();
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
  }
});
