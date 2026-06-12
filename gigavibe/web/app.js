import { createSmileWatcher } from "./smile-capture.js";
import { createFacePresenceWatcher } from "./face-presence.js";
import {
  initCaptureOverlays,
  relayoutCaptureOverlays,
  relayoutResultOverlays,
  setCaptureOverlaysVisible,
  setResultOverlaysVisible,
} from "./overlay-sprites.js";
const captureOverlayBack = document.getElementById("capture-overlay-back");
const captureOverlayFront = document.getElementById("capture-overlay-front");
const resultOverlayBack = document.getElementById("result-overlay-back");
const resultOverlayFront = document.getElementById("result-overlay-front");
const cameraRig = document.getElementById("camera-rig");
const cameraProbeSlot = document.getElementById("camera-probe-slot");
const captureFrameSlot = document.getElementById("capture-frame-slot");
const idleBgVideo = document.getElementById("idle-bg-video");
const startHint = document.getElementById("start-hint");

const shell = document.querySelector(".shell");

const screens = {
  start: document.getElementById("screen-start"),
  capture: document.getElementById("screen-capture"),
  processing: document.getElementById("screen-processing"),
  result: document.getElementById("screen-result"),
  error: document.getElementById("screen-error"),
};

const preview = document.getElementById("preview");
const previewCanvas = document.getElementById("preview-canvas");
const snapshot = document.getElementById("snapshot");
const captureHint = document.getElementById("capture-hint");
const smileStatus = document.getElementById("smile-status");
const smileRing = document.getElementById("smile-ring");
const statusPrev = document.getElementById("status-prev");
const statusText = document.getElementById("status-text");
const resultPortrait = document.getElementById("result-portrait");
const resultImage = document.getElementById("result-image");
const resultBadge = document.getElementById("result-badge");
const ctaTitle = document.getElementById("cta-title");
const ctaLead = document.getElementById("cta-lead");
const qrImg = document.getElementById("qr");
const countdownSec = document.getElementById("countdown-sec");
const errorText = document.getElementById("error-text");
const btnErrorRetry = document.getElementById("btn-error-retry");
const btnRetry = document.getElementById("btn-retry");

const RESULT_LOOP_SEC = 20;
const CAMERA_ZOOM = 2;
const DETECTION_FRAME_W = 640;
const DETECTION_FRAME_H = 480;
const DETECTION_READY_TIMEOUT_MS = 900;

const KIOSK_W = 1008;
const KIOSK_H = 672;

function applyKioskScale() {
  const scale = Math.min(
    1,
    window.innerWidth / KIOSK_W,
    window.innerHeight / KIOSK_H,
  );
  document.documentElement.style.setProperty("--kiosk-scale", String(scale));
}

const PROCESSING_LINES = ["Загружаем момент", "Включаем ИИ-магию"];

let kioskCfg = {
  output_kind: "image",
  kiosk_auto_camera: true,
  kiosk_smile_capture: true,
  kiosk_jpeg_quality: 0.96,
  kiosk_smile_threshold: 0.42,
  kiosk_smile_hold_frames: 12,
  kiosk_smile_hold_ms: 650,
  kiosk_smile_detect_stride: 6,
  kiosk_smile_cooldown_ms: 8000,
  kiosk_face_min_size: 0.12,
  kiosk_face_hold_frames: 12,
  kiosk_face_release_frames: 20,
  kiosk_face_hold_ms: 700,
  kiosk_face_release_ms: 1600,
  kiosk_face_detect_stride: 25,
  print_enabled: false,
  output_upload_enabled: false,
};

let stream = null;
let videoWidth = 720;
let videoHeight = 1280;
let funnyTimer = null;
let activeLines = [];
let resultTimer = null;
let countdownTimer = null;
let smileWatcher = null;
let presenceWatcher = null;
let captureLocked = false;
let onCaptureScreen = false;
const screenHideTimers = new Map();
let screenRevealToken = 0;
let previewRaf = null;
let previewVideoFrame = null;
const detectionCanvas = document.createElement("canvas");
detectionCanvas.width = 0;
detectionCanvas.height = 0;

function isPortraitViewport() {
  const h = window.visualViewport?.height ?? window.innerHeight;
  const w = window.visualViewport?.width ?? window.innerWidth;
  return h > w;
}

/** Рисует кадр камеры на весь экран (cover) + зеркало + поворот landscape-потока на телефоне. */
function drawVideoFit(
  ctx,
  video,
  destW,
  destH,
  { mirror = true, fill = "#111", zoom = 1 } = {},
) {
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  if (!vw || !vh) return;

  const rotated = isPortraitViewport() && vw > vh;

  ctx.fillStyle = fill;
  ctx.fillRect(0, 0, destW, destH);

  ctx.save();
  ctx.translate(destW / 2, destH / 2);
  if (mirror) ctx.scale(-1, 1);
  if (rotated) ctx.rotate(Math.PI / 2);

  const fitW = rotated ? vh : vw;
  const fitH = rotated ? vw : vh;
  const scale = Math.max(destW / fitW, destH / fitH) * Math.max(1, zoom);
  const dw = fitW * scale;
  const dh = fitH * scale;
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(video, -dw / 2, -dh / 2, dw, dh);
  ctx.restore();
}

function drawPreviewFrame() {
  if (!preview.videoWidth || !preview.videoHeight || preview.readyState < 2) return;

  if (
    detectionCanvas.width !== DETECTION_FRAME_W ||
    detectionCanvas.height !== DETECTION_FRAME_H
  ) {
    detectionCanvas.width = DETECTION_FRAME_W;
    detectionCanvas.height = DETECTION_FRAME_H;
  }
  drawVideoFit(
    detectionCanvas.getContext("2d"),
    preview,
    DETECTION_FRAME_W,
    DETECTION_FRAME_H,
    { zoom: CAMERA_ZOOM },
  );

  if (!previewCanvas) return;
  const cw = previewCanvas.clientWidth;
  const ch = previewCanvas.clientHeight;
  if (cw >= 1 && ch >= 1) {
    if (previewCanvas.width !== cw || previewCanvas.height !== ch) {
      previewCanvas.width = cw;
      previewCanvas.height = ch;
    }
    drawVideoFit(previewCanvas.getContext("2d"), preview, cw, ch, { zoom: CAMERA_ZOOM });
  }
}

function startPreviewLoop() {
  stopPreviewLoop();
  if (typeof preview.requestVideoFrameCallback === "function") {
    const tick = () => {
      drawPreviewFrame();
      previewVideoFrame = preview.requestVideoFrameCallback(tick);
    };
    previewVideoFrame = preview.requestVideoFrameCallback(tick);
    return;
  }

  const tick = () => {
    drawPreviewFrame();
    previewRaf = requestAnimationFrame(tick);
  };
  previewRaf = requestAnimationFrame(tick);
}

function stopPreviewLoop() {
  if (
    previewVideoFrame != null &&
    typeof preview.cancelVideoFrameCallback === "function"
  ) {
    preview.cancelVideoFrameCallback(previewVideoFrame);
    previewVideoFrame = null;
  }
  if (previewRaf != null) {
    cancelAnimationFrame(previewRaf);
    previewRaf = null;
  }
  if (previewCanvas) {
    const ctx = previewCanvas.getContext("2d");
    ctx?.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
  }
  detectionCanvas.width = 0;
  detectionCanvas.height = 0;
}

function detectionSourceReady() {
  return detectionCanvas.width > 0 && detectionCanvas.height > 0;
}

async function resolveDetectionSource(timeoutMs = DETECTION_READY_TIMEOUT_MS) {
  const start = performance.now();
  while (performance.now() - start < timeoutMs) {
    drawPreviewFrame();
    if (detectionSourceReady()) return detectionCanvas;
    await new Promise((resolve) => requestAnimationFrame(resolve));
  }
  return preview;
}

function layoutCapturePreview() {
  if (!onCaptureScreen || !captureFrameSlot) return;
  const w = captureFrameSlot.clientWidth;
  const h = captureFrameSlot.clientHeight;
  if (w < 1 || h < 1) return;
  document.documentElement.style.setProperty("--capture-frame-w", `${w}px`);
  document.documentElement.style.setProperty("--capture-frame-h", `${h}px`);
}

function mountCameraLive() {
  if (!cameraRig || !captureFrameSlot) return;
  captureFrameSlot.appendChild(cameraRig);
  cameraRig.classList.remove("camera-rig--probe");
}

function mountCameraProbe() {
  if (!cameraRig || !cameraProbeSlot) return;
  cameraProbeSlot.appendChild(cameraRig);
  cameraRig.classList.add("camera-rig--probe");
}

function playIdleVideo() {
  idleBgVideo?.play().catch(() => {});
}

idleBgVideo?.addEventListener("playing", () => {
  idleBgVideo.dataset.ready = "true";
});

function bindViewportLayout() {
  applyKioskScale();
  layoutCapturePreview();
}

function bindCaptureLayout() {
  bindViewportLayout();
  window.addEventListener("resize", bindViewportLayout);
  window.visualViewport?.addEventListener("resize", bindViewportLayout);
  window.addEventListener("orientationchange", () => {
    setTimeout(bindViewportLayout, 120);
  });
  preview.addEventListener("loadedmetadata", () => {
    layoutCapturePreview();
    drawPreviewFrame();
  });
}

async function loadKioskConfig() {
  try {
    const res = await fetch("/api/config");
    if (!res.ok) return;
    const cfg = await res.json();
    kioskCfg = { ...kioskCfg, ...cfg };
    if (cfg.video_width > 0 && cfg.video_height > 0) {
      videoWidth = cfg.video_width;
      videoHeight = cfg.video_height;
      document.documentElement.style.setProperty(
        "--video-aspect",
        `${videoWidth} / ${videoHeight}`,
      );
    }
    if (cfg.video_duration_sec > 0) {
      document.documentElement.style.setProperty(
        "--dolly-duration",
        `${cfg.video_duration_sec}s`,
      );
    }
    layoutCapturePreview();
    applyOutputKindUi();
  } catch {
    /* defaults */
  }
}

function applyOutputKindUi() {
  if (resultBadge) resultBadge.textContent = "Ваш портрет";
  if (ctaTitle) {
    if (kioskCfg.print_enabled) {
      ctaTitle.innerHTML =
        "Забирай фото с принтера<br />и скачивай вайб по QR!";
    } else {
      ctaTitle.innerHTML =
        "Скачивай готовый вайб<br />и забирай настоящее фото!";
    }
  }
  if (ctaLead) {
    if (kioskCfg.print_enabled) {
      ctaLead.textContent = kioskCfg.output_upload_enabled
        ? "Фото на сервере и в печати. QR — для скачивания на телефон"
        : "Печать запущена. QR — для скачивания на телефон";
    } else {
      ctaLead.textContent =
        "Наведите камеру на QR — картинка откроется в браузере";
    }
  }
}

function show(name) {
  const target = screens[name];
  screenRevealToken += 1;
  const revealToken = screenRevealToken;
  shell?.setAttribute("data-screen", name);

  Object.values(screens).forEach((el) => {
    if (!el) return;
    const timer = screenHideTimers.get(el);
    if (timer) {
      clearTimeout(timer);
      screenHideTimers.delete(el);
    }

    if (el === target) {
      el.classList.remove("hidden", "is-hiding");
      requestAnimationFrame(() => {
        if (revealToken !== screenRevealToken) return;
        el.classList.add("is-visible");
      });
      return;
    }

    el.classList.remove("is-visible");
    if (el.classList.contains("hidden")) {
      el.classList.remove("is-hiding");
      return;
    }
    el.classList.add("is-hiding");
    const hideTimer = window.setTimeout(() => {
      el.classList.add("hidden");
      el.classList.remove("is-hiding", "is-visible");
      screenHideTimers.delete(el);
    }, 460);
    screenHideTimers.set(el, hideTimer);
  });
  onCaptureScreen = name === "capture";
  setCaptureOverlaysVisible(name === "start" || name === "capture");
  setResultOverlaysVisible(name === "result");
  if (name === "result") relayoutResultOverlays();
  playIdleVideo();
}

function updateStartHint({ phase, size, minFaceSize }) {
  if (!startHint) return;
  if (phase === "too_far" && size > 0) {
    startHint.textContent = "Подойдите ближе к экрану";
  } else if (phase === "approaching") {
    startHint.textContent = "Отлично, ещё чуть-чуть…";
  } else {
    startHint.textContent = "";
  }
}

function buildActiveLines() {
  activeLines = [...PROCESSING_LINES];
}

function restartAnimation(el, className) {
  if (!el) return;
  el.classList.remove(className);
  // Force reflow so repeated status changes replay the CSS animation.
  void el.offsetWidth;
  el.classList.add(className);
}

function fitStatusText(el) {
  if (!el) return;
  const parent = el.parentElement;
  const maxWidth = parent ? parent.clientWidth - 88 : 560;
  let size = 44;
  el.style.transform = "scaleX(1)";
  el.style.fontSize = `${size}px`;
  while (el.scrollWidth > maxWidth && size > 22) {
    size -= 1;
    el.style.fontSize = `${size}px`;
  }
  if (el.scrollWidth > maxWidth) {
    const scale = Math.max(0.82, maxWidth / el.scrollWidth);
    el.style.transform = `scaleX(${scale.toFixed(3)})`;
  }
}

function showProcessingStatus(text, previousText = statusText?.textContent || "") {
  if (!text) return;
  if (text === statusText?.textContent) {
    fitStatusText(statusText);
    return;
  }

  const prevBox = statusPrev?.parentElement;
  const currentBox = statusText?.parentElement;

  if (statusPrev) {
    statusPrev.textContent = previousText || "";
    fitStatusText(statusPrev);
  }
  statusText.textContent = text;
  fitStatusText(statusText);

  if (previousText) {
    restartAnimation(prevBox, "is-leaving");
    window.setTimeout(() => {
      if (statusPrev?.textContent === previousText) statusPrev.textContent = "";
      prevBox?.classList.remove("is-leaving");
    }, 820);
  } else {
    prevBox?.classList.remove("is-leaving");
  }
  restartAnimation(currentBox, "is-entering");
}

function setActiveLine(slot, prevSlot = null) {
  const text = activeLines[slot];
  if (!text) return;
  const previousText =
    prevSlot == null ? statusText?.textContent || "" : activeLines[prevSlot] || "";
  showProcessingStatus(text, previousText);
}

function startFunnyRotation() {
  stopFunnyRotation();
  buildActiveLines();
  let slot = 0;
  setActiveLine(slot);
  funnyTimer = setInterval(() => {
    const prevSlot = slot;
    slot = (slot + 1) % activeLines.length;
    setActiveLine(slot, prevSlot);
  }, 2800);
}

function stopFunnyRotation() {
  if (funnyTimer) {
    clearInterval(funnyTimer);
    funnyTimer = null;
  }
}


function updateSmileUi({ phase, score, hold, holdFrames, smileMs, holdMs }) {
  smileRing.classList.remove("hidden");
  const pct =
    holdMs && smileMs != null
      ? Math.min(100, Math.round((smileMs / holdMs) * 100))
      : holdFrames
        ? Math.min(100, Math.round((hold / holdFrames) * 100))
        : 0;
  smileRing.style.setProperty("--smile-pct", `${pct}%`);

  if (phase === "wait_face") {
    smileStatus.textContent = "Посмотрите в камеру";
    if (captureHint) captureHint.textContent = "Подойдите ближе";
  } else if (phase === "smile" || phase === "almost") {
    smileStatus.textContent = "Отлично! Держите улыбку…";
    if (captureHint) captureHint.textContent = "Улыбайтесь!";
  } else {
    smileStatus.textContent = "Улыбнитесь для снимка";
    if (captureHint) captureHint.textContent = "Улыбайтесь!";
  }
}

function cameraErrorMessage(err) {
  if (!window.isSecureContext) {
    const host = location.hostname || "сервер";
    return (
      "Камера доступна только по HTTPS (или на localhost). " +
      `Откройте https://${host}${location.port ? ":" + location.port : ""}, ` +
      "примите предупреждение о сертификате (Дополнительно → Перейти) и разрешите камеру."
    );
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    return "Браузер не поддерживает камеру. Используйте Chrome или Edge.";
  }
  const name = err?.name || "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError") {
    return "Разрешите камеру в настройках браузера (значок замка в адресной строке) и обновите страницу.";
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return "Камера не найдена. Подключите веб-камеру к устройству киоска.";
  }
  return "Нет доступа к камере. Проверьте HTTPS и разрешения браузера.";
}

async function startCamera() {
  if (!window.isSecureContext) {
    throw new DOMException("insecure context", "SecurityError");
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new DOMException("no getUserMedia", "NotSupportedError");
  }
  stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user" },
    audio: false,
  });
  preview.srcObject = stream;
  await preview.play().catch(() => {});
  layoutCapturePreview();
  startPreviewLoop();
}

async function startPresenceWatch() {
  await presenceWatcher?.close?.();
  presenceWatcher = null;
  try {
    const detectionSource = await resolveDetectionSource();
    presenceWatcher = await createFacePresenceWatcher(detectionSource, {
      minFaceSize: kioskCfg.kiosk_face_min_size,
      holdFrames: kioskCfg.kiosk_face_hold_frames,
      releaseFrames: kioskCfg.kiosk_face_release_frames,
      holdMs: kioskCfg.kiosk_face_hold_ms,
      releaseMs: kioskCfg.kiosk_face_release_ms,
      detectStride: kioskCfg.kiosk_face_detect_stride,
      onStatus: updateStartHint,
      onReady: () => enterCapture(),
      onError: (e) => console.warn("presence", e),
    });
    presenceWatcher.start();
  } catch (err) {
    if (startHint) {
      startHint.textContent =
        "Распознавание лица недоступно. Запустите scripts\\download_smile_model.ps1";
    }
    console.warn(err);
  }
}

async function enterCapture() {
  if (onCaptureScreen || captureLocked) return;
  await presenceWatcher?.close?.();
  presenceWatcher = null;

  show("capture");
  mountCameraLive();
  relayoutCaptureOverlays();
  layoutCapturePreview();
  startPreviewLoop();

  smileStatus.textContent = "Улыбнитесь для снимка";
  if (captureHint) captureHint.textContent = "Улыбайтесь!";

  await startSmileCapture();
}

async function returnToIdle() {
  captureLocked = false;
  stopFunnyRotation();
  stopResultPlayback();
  await smileWatcher?.close?.();
  smileWatcher = null;
  smileRing?.classList.add("hidden");
  qrImg.removeAttribute("src");
  errorText.textContent = "";

  stopPreviewLoop();
  mountCameraProbe();
  show("start");
  startPreviewLoop();

  if (stream) {
    await startPresenceWatch();
  } else if (kioskCfg.kiosk_auto_camera) {
    await bootIdle();
  }
}

async function startSmileCapture() {
  if (!kioskCfg.kiosk_smile_capture) return;
  try {
    await smileWatcher?.close?.();
    const detectionSource = await resolveDetectionSource();
    smileWatcher = await createSmileWatcher(detectionSource, {
      threshold: kioskCfg.kiosk_smile_threshold,
      holdFrames: kioskCfg.kiosk_smile_hold_frames,
      holdMs: kioskCfg.kiosk_smile_hold_ms,
      minFaceSize: kioskCfg.kiosk_face_min_size * 0.85,
      releaseMs: kioskCfg.kiosk_face_release_ms,
      detectStride: kioskCfg.kiosk_smile_detect_stride,
      onStatus: updateSmileUi,
      onSmile: () => triggerCapture(),
      onLost: () => {
        if (!captureLocked) returnToIdle();
      },
      onError: (e) => console.warn("smile", e),
    });
    smileWatcher.start();
  } catch (err) {
    smileStatus.textContent =
      "Улыбка недоступна. Запустите scripts\\download_smile_model.ps1. " +
      err.message;
  }
}

async function triggerCapture() {
  if (captureLocked) return;
  captureLocked = true;
  smileWatcher?.stop();
  smileStatus.textContent = "Снимаем!";

  try {
    const blob = await captureBlob();
    stopCamera();
    await submitPhoto(blob);
  } catch (err) {
    errorText.textContent = err.message;
    show("error");
  }
}

function stopCamera() {
  stopPreviewLoop();
  smileWatcher?.stop();
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
}

function captureBlob() {
  const w = videoWidth;
  const h = videoHeight;
  snapshot.width = w;
  snapshot.height = h;
  drawVideoFit(snapshot.getContext("2d"), preview, w, h, { zoom: 1 });
  const q = kioskCfg.kiosk_jpeg_quality ?? 0.96;
  return new Promise((resolve) => {
    snapshot.toBlob((blob) => resolve(blob), "image/jpeg", q);
  });
}

function stopResultPlayback() {
  if (resultTimer) {
    clearTimeout(resultTimer);
    resultTimer = null;
  }
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
  if (resultImage) {
    resultImage.removeAttribute("src");
  }
}

function fitResultPortrait() {
  if (!resultImage?.naturalWidth) return;
  const ar = resultImage.naturalWidth / resultImage.naturalHeight;
  // 9:16 и близкие вертикальные кадры — лицо чуть выше геометрического центра
  if (ar < 0.8) {
    resultImage.style.objectPosition = "center 44%";
  } else if (ar < 1.05) {
    resultImage.style.objectPosition = "center 40%";
  } else {
    resultImage.style.objectPosition = "center center";
  }
}

function showResultMedia(data) {
  const mediaUrl = data.image_path || data.download_url;
  if (!mediaUrl || !resultImage) return Promise.resolve();
  return new Promise((resolve) => {
    resultImage.onload = () => {
      fitResultPortrait();
      resolve();
    };
    resultImage.onerror = () => {
      console.error("Не удалось загрузить портрет:", mediaUrl);
      resolve();
    };
    resultImage.src = `${mediaUrl}?t=${Date.now()}`;
  });
}

async function startResultPlayback(data) {
  stopResultPlayback();
  setCaptureOverlaysVisible(false);

  if (data.qr_data_url) {
    qrImg.src = data.qr_data_url;
  } else if (data.qr_path) {
    qrImg.src = `${data.qr_path}?t=${Date.now()}`;
  }
  qrImg.alt = "QR для скачивания портрета";

  await showResultMedia(data);

  let left = RESULT_LOOP_SEC;
  countdownSec.textContent = String(left);
  show("result");
  countdownTimer = setInterval(() => {
    left -= 1;
    countdownSec.textContent = String(Math.max(left, 0));
  }, 1000);
  resultTimer = setTimeout(() => reset(), RESULT_LOOP_SEC * 1000);
}

async function submitPhoto(blob) {
  show("processing");
  startFunnyRotation();

  const form = new FormData();
  form.append("photo", blob, "selfie.jpg");

  const createRes = await fetch("/api/jobs", { method: "POST", body: form });
  if (!createRes.ok) {
    const errBody = await createRes.text().catch(() => "");
    throw new Error(errBody || "Не удалось отправить фото");
  }
  const { job_id: jobId } = await createRes.json();

  for (let i = 0; i < 300; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    const statusRes = await fetch(`/api/jobs/${jobId}`);
    if (!statusRes.ok) {
      const errBody = await statusRes.text().catch(() => "");
      throw new Error(
        errBody.startsWith("{")
          ? (JSON.parse(errBody).detail ?? errBody)
          : errBody || `Ошибка сервера (${statusRes.status})`,
      );
    }
    const data = await statusRes.json();

    if (data.status === "done") {
      stopFunnyRotation();
      startResultPlayback(data);
      return;
    }
    if (data.status === "error") {
      throw new Error(data.message || "Ошибка генерации");
    }
  }
  throw new Error("Превышено время ожидания");
}

async function reset() {
  await returnToIdle();
}

async function bootIdle() {
  try {
    if (!stream) {
      await startCamera();
    }
    mountCameraProbe();
    await startPresenceWatch();
  } catch (err) {
    errorText.textContent = cameraErrorMessage(err);
    show("error");
  }
}

btnErrorRetry.addEventListener("click", reset);
btnRetry.addEventListener("click", reset);

function devPreviewResult() {
  const params = new URLSearchParams(location.search);
  const preview = params.get("preview");
  if (preview === "processing") {
    show("processing");
    activeLines = [
      params.get("previous") || PROCESSING_LINES[0],
      params.get("current") || PROCESSING_LINES[1],
    ];
    setActiveLine(1, 0);
    document.body.dataset.verifyReady = "1";
    return true;
  }
  if (preview === "capture") {
    show("capture");
    relayoutCaptureOverlays();
    document.body.dataset.verifyReady = "1";
    return true;
  }
  if (preview !== "result") return false;

  show("result");
  relayoutResultOverlays();

  const canvas = document.createElement("canvas");
  canvas.width = 720;
  canvas.height = 1280;
  const ctx = canvas.getContext("2d");
  const bg = ctx.createLinearGradient(0, 0, 0, 1280);
  bg.addColorStop(0, "#5ecfff");
  bg.addColorStop(0.55, "#c8f5d8");
  bg.addColorStop(1, "#a6ff00");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, 720, 1280);
  ctx.fillStyle = "#f0c8a8";
  ctx.beginPath();
  ctx.ellipse(360, 520, 118, 148, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#1a1a1a";
  ctx.beginPath();
  ctx.arc(328, 498, 14, 0, Math.PI * 2);
  ctx.arc(392, 498, 14, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#21a038";
  ctx.fillRect(275, 668, 170, 420);

  resultImage.onload = () => {
    fitResultPortrait();
    const wrap = document.querySelector(".result-portrait-wrap");
    const img = resultImage;
    const imgStyle = getComputedStyle(img);
    document.body.dataset.verifyPortraitW = String(Math.round(wrap?.offsetWidth ?? 0));
    document.body.dataset.verifyPortraitH = String(Math.round(wrap?.offsetHeight ?? 0));
    document.body.dataset.verifyObjectPosition = imgStyle.objectPosition;
    document.body.dataset.verifyObjectFit = imgStyle.objectFit;
    document.body.dataset.verifyReady = "1";
  };
  resultImage.src = canvas.toDataURL("image/jpeg", 0.92);

  const qrCanvas = document.createElement("canvas");
  qrCanvas.width = 240;
  qrCanvas.height = 240;
  const qctx = qrCanvas.getContext("2d");
  qctx.fillStyle = "#fff";
  qctx.fillRect(0, 0, 240, 240);
  qctx.fillStyle = "#000";
  for (let y = 0; y < 12; y += 1) {
    for (let x = 0; x < 12; x += 1) {
      if ((x + y) % 2 === 0) qctx.fillRect(x * 20, y * 20, 20, 20);
    }
  }
  qrImg.src = qrCanvas.toDataURL("image/png");
  applyOutputKindUi();
  return true;
}

(async () => {
  bindCaptureLayout();
  await initCaptureOverlays({
    back: captureOverlayBack,
    front: captureOverlayFront,
    resultBack: resultOverlayBack,
    resultFront: resultOverlayFront,
  });
  await loadKioskConfig();
  if (devPreviewResult()) return;
  mountCameraProbe();
  show("start");
  playIdleVideo();
  if (kioskCfg.kiosk_auto_camera) {
    await bootIdle();
  }
})();
