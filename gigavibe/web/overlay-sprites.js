/** Декоративные оверлеи на экранах камеры и результата (киоск 1008×672). */

const KIOSK_W = 1008;
const KIOSK_H = 672;

const CAMERA = { x: 215, y: 143, w: 579, h: 387 };
const CAPTURE_SPRITE_COUNT = 6;
const RESULT_SPRITE_COUNT = 5;

const CAPTURE_TEXT_BLOCKERS = [
  { x: 40, y: 40, w: 185, h: 103 },
  { x: 255, y: 520, w: 500, h: 110 },
];

const RESULT_PORTRAIT = { x: 180, y: 57, w: 352, h: 529 };
const RESULT_HARD_BLOCKERS = [
  { x: 551, y: 178, w: 286, h: 286 },
  { x: 551, y: 68, w: 143, h: 81 },
  { x: 551, y: 472, w: 310, h: 110 },
];

let pool = [];
let captureBackLayer = null;
let captureFrontLayer = null;
let resultBackLayer = null;
let resultFrontLayer = null;

const ASSET_FILES = Array.from({ length: 20 }, (_, i) => `Asset (${i + 1}).png`);

function shuffle(items) {
  const arr = [...items];
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function rand(min, max) {
  return min + Math.random() * (max - min);
}

function rectsOverlap(a, b, margin = 0) {
  return !(
    a.x + a.w + margin < b.x ||
    b.x + b.w + margin < a.x ||
    a.y + a.h + margin < b.y ||
    b.y + b.h + margin < a.y
  );
}

function overlapsBlockers(rect, blockers, margin = 0) {
  return blockers.some((zone) => rectsOverlap(rect, zone, margin));
}

function assetUrl(fileName) {
  return `/assets/img/${encodeURIComponent(fileName)}`;
}

function loadSprite(fileName) {
  const src = assetUrl(fileName);
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      resolve({
        src,
        w: img.naturalWidth || 512,
        h: img.naturalHeight || 512,
      });
    };
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

function appendSprite(parent, sprite, rect) {
  const img = document.createElement("img");
  img.className = "overlay-sprite";
  img.src = sprite.src;
  img.alt = "";
  img.draggable = false;
  img.loading = "eager";
  img.decoding = "async";
  img.style.left = `${rect.x}px`;
  img.style.top = `${rect.y}px`;
  img.style.width = `${Math.round(rect.w)}px`;
  img.style.height = `${Math.round(rect.h)}px`;
  img.style.setProperty("--dur", `${rand(3.2, 7.5).toFixed(2)}s`);
  img.style.setProperty("--delay", `${rand(0, 2.4).toFixed(2)}s`);
  img.style.setProperty("--sway", `${rand(-10, 10).toFixed(1)}px`);
  img.style.setProperty("--bob", `${rand(5, 16).toFixed(1)}px`);
  img.style.setProperty("--rot", `${rand(-9, 9).toFixed(1)}deg`);
  parent.appendChild(img);
}

export async function initCaptureOverlays({ back, front, resultBack, resultFront }) {
  captureBackLayer = back;
  captureFrontLayer = front;
  resultBackLayer = resultBack;
  resultFrontLayer = resultFront;
  try {
    const loaded = await Promise.all(ASSET_FILES.map(loadSprite));
    pool = loaded.filter(Boolean);
    if (pool.length === 0) throw new Error("empty assets/img sprite pool");
  } catch (err) {
    console.warn("[overlays] assets/img load failed:", err);
    pool = [];
  }
}

export function setCaptureOverlaysVisible(visible) {
  for (const layer of [captureBackLayer, captureFrontLayer]) {
    layer?.classList.toggle("hidden", !visible);
  }
}

export function setResultOverlaysVisible(visible) {
  for (const layer of [resultBackLayer, resultFrontLayer]) {
    layer?.classList.toggle("hidden", !visible);
  }
}

export function relayoutCaptureOverlays() {
  if (!captureBackLayer || !captureFrontLayer || pool.length === 0) return;

  captureBackLayer.replaceChildren();
  captureFrontLayer.replaceChildren();

  const picked = shuffle(pool).slice(0, Math.min(CAPTURE_SPRITE_COUNT, pool.length));
  const placed = [];

  for (const sprite of picked) {
    const targetW = rand(100, 270);
    const scale = targetW / sprite.w;
    const dispW = sprite.w * scale;
    const dispH = sprite.h * scale;

    for (let attempt = 0; attempt < 40; attempt += 1) {
      const x = rand(-dispW * 0.4, KIOSK_W - dispW * 0.6);
      const y = rand(24, KIOSK_H - dispH * 0.5);
      const rect = { x, y, w: dispW, h: dispH };

      if (placed.some((p) => rectsOverlap(rect, p, 24))) continue;
      if (overlapsBlockers(rect, CAPTURE_TEXT_BLOCKERS, 72)) continue;

      const overCamera = rectsOverlap(rect, CAMERA, 0);
      const coversCameraCenter = rectsOverlap(rect, {
        x: CAMERA.x + CAMERA.w * 0.28,
        y: CAMERA.y + CAMERA.h * 0.28,
        w: CAMERA.w * 0.44,
        h: CAMERA.h * 0.44,
      });
      if (coversCameraCenter) continue;

      placed.push(rect);
      appendSprite(overCamera ? captureFrontLayer : captureBackLayer, sprite, rect);
      break;
    }
  }
}

export function relayoutResultOverlays() {
  if (!resultBackLayer || !resultFrontLayer || pool.length === 0) return;

  resultBackLayer.replaceChildren();
  resultFrontLayer.replaceChildren();

  const portraitCenter = {
    x: RESULT_PORTRAIT.x + RESULT_PORTRAIT.w * 0.22,
    y: RESULT_PORTRAIT.y + RESULT_PORTRAIT.h * 0.18,
    w: RESULT_PORTRAIT.w * 0.56,
    h: RESULT_PORTRAIT.h * 0.58,
  };

  const picked = shuffle(pool).slice(0, Math.min(RESULT_SPRITE_COUNT, pool.length));
  const placed = [];

  for (const sprite of picked) {
    const targetW = rand(72, 190);
    const scale = targetW / sprite.w;
    const dispW = sprite.w * scale;
    const dispH = sprite.h * scale;

    for (let attempt = 0; attempt < 50; attempt += 1) {
      const x = rand(-dispW * 0.35, KIOSK_W - dispW * 0.65);
      const y = rand(8, KIOSK_H - dispH * 0.45);
      const rect = { x, y, w: dispW, h: dispH };

      if (placed.some((p) => rectsOverlap(rect, p, 20))) continue;
      if (overlapsBlockers(rect, RESULT_HARD_BLOCKERS, 40)) continue;
      if (rectsOverlap(rect, portraitCenter, 8)) continue;

      const overPortrait = rectsOverlap(rect, RESULT_PORTRAIT, 0);
      const coversPortraitCenter = rectsOverlap(rect, portraitCenter, 12);
      if (coversPortraitCenter) continue;

      placed.push(rect);
      appendSprite(overPortrait ? resultFrontLayer : resultBackLayer, sprite, rect);
      break;
    }
  }
}
