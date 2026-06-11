/**
 * Сцена «Улыбка» — координаты через mapBox из figma-layout.
 */

import {
  SIZE,
  S,
  FIGMA_RING,
  COPY as DEFAULT_COPY,
  MASTER_GRADIENT,
  SUBTRACT,
  QR_BOX,
  QR_IMAGE,
  QR_CAPTION,
  QR_CODE_ASSET,
  PILL,
  ALL_DECOR,
  TEXT_PATHS,
  TEXT_PATH_META,
  TEXT,
  mapBox,
} from "./figma-layout.js";
import { applyCamVars, getCamHoleCanvas504 } from "./cam-geometry.js";

const ASSET_BASE = "/static/assets/figma";

export const STAGES = ["idle", "face", "line", "stickers", "qr"];

export const STAGE_ALIASES = {
  intro: "idle",
  line_hold: "face",
  line_expand: "line",
};

export const STAGE_TIMING = {
  line: 10000,
  stickers: 2400,
  qr: 20000,
};

const LINE_TYPEWRITER = {
  delay: 220,
  duration: 1150,
};

const STICKERS_IN_MS = 1000;
const STICKERS_OUT_MS = 1000;
const STICKER_DECOR = ALL_DECOR.filter((item) => item.stages.includes("stickers"));

export { DEFAULT_COPY as COPY };

function px(value) {
  return `${value}px`;
}

function placeBox(el, box, rotate = 0) {
  el.style.left = px(box.left);
  el.style.top = px(box.top);
  el.style.width = px(box.width);
  el.style.height = px(box.height);
  if (rotate) el.style.setProperty("--rot", `${rotate}deg`);
}

function scalePathD(d) {
  const k = TEXT_PATH_META.frame === FIGMA_RING ? S : 1;
  return d.replace(/-?\d+\.?\d*/g, (n) => String(Number(n) * k));
}

function decorNode(item, index) {
  const box = mapBox(item);
  const wrap = document.createElement("div");
  wrap.className = `smile-stage__decor smile-stage__decor--${item.id}`;
  wrap.dataset.decorStages = item.stages.join(" ");
  wrap.dataset.debugLabel = `decor:${item.id}`;
  wrap.style.setProperty("--decor-i", String(index));
  if (Number.isFinite(item.holdIndex)) {
    wrap.dataset.holdDecor = "true";
    wrap.style.setProperty("--hold-i", String(item.holdIndex));
  }
  const stickerIndex = STICKER_DECOR.indexOf(item);
  if (stickerIndex >= 0) {
    wrap.style.setProperty("--decor-out-i", String(STICKER_DECOR.length - stickerIndex - 1));
  }
  placeBox(wrap, box, item.rotate ?? 0);

  const img = document.createElement("img");
  img.src = `${ASSET_BASE}/${item.src}`;
  img.alt = "";
  img.draggable = false;
  wrap.appendChild(img);
  return wrap;
}

function buildTextPaths(copy) {
  const topD = scalePathD(TEXT_PATHS.top);
  const bottomD = scalePathD(TEXT_PATHS.bottom);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "smile-stage__text-svg");
  svg.setAttribute("viewBox", `0 0 ${SIZE} ${SIZE}`);
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = `
    <defs>
      <path id="smile-path-top" d="${topD}" fill="none" />
      <path id="smile-path-bottom" d="${bottomD}" fill="none" />
    </defs>
    <text class="smile-stage__path-text smile-stage__path-text--top" font-size="${TEXT.pathTopSize}">
      <textPath href="#smile-path-top" startOffset="50%" text-anchor="middle" data-role="top-line">${copy.lineTop}</textPath>
    </text>
    <text class="smile-stage__path-text smile-stage__path-text--bottom" font-size="${TEXT.pathBottomShortSize}">
      <textPath href="#smile-path-bottom" startOffset="50%" text-anchor="middle" data-role="bottom-line">${copy.lineBottomShort}</textPath>
    </text>
  `;
  return svg;
}

function buildPillCopy(copy) {
  const wrap = document.createElement("div");
  wrap.className = "smile-stage__pill-wrap";

  // Figma get_design_context 127:513: плашка и тексты - отдельные flex-обёртки.
  const block = document.createElement("div");
  block.className = "smile-stage__pill-block";
  placeBox(block, {
    frame: 504,
    left: PILL.left,
    top: 153.88,
    width: PILL.width,
    height: PILL.height,
  }, PILL.rotate);

  const main = document.createElement("p");
  main.className = "smile-stage__pill-main";
  main.textContent = copy.teaser;
  main.style.left = px(252 - 383.872 / 2);
  main.style.top = px(253.65 - 82);
  main.style.width = px(383.872);
  main.style.height = px(164);
  main.style.fontSize = px(TEXT.pillMain.fontSize);
  main.style.lineHeight = String(TEXT.pillMain.lineHeight);
  main.style.setProperty("--rot", `${PILL.rotate}deg`);

  const cta = document.createElement("p");
  cta.className = "smile-stage__pill-cta";
  cta.textContent = copy.cta;
  cta.style.left = px(252 + 7.28 - 253.714 / 2);
  cta.style.top = px(270 + (164.517 - 139.509) / 2);
  cta.style.width = px(253.714);
  cta.style.height = px(139.509);
  cta.style.fontSize = px(TEXT.pillCta.fontSize);
  cta.style.lineHeight = String(TEXT.pillCta.lineHeight);
  cta.style.setProperty("--rot", `${PILL.rotate}deg`);

  wrap.appendChild(block);
  wrap.appendChild(main);
  wrap.appendChild(cta);
  return wrap;
}

export function resolveStage(id) {
  return STAGE_ALIASES[id] ?? id;
}

function debugBox(label, source, className = "") {
  const box = mapBox(source);
  const node = document.createElement("div");
  node.className = `smile-stage__debug-box ${className}`.trim();
  node.dataset.debugLabel = label;
  placeBox(node, box, source.rotate ?? 0);
  return node;
}

function buildDebugOverlay() {
  const layer = document.createElement("div");
  layer.className = "smile-stage__debug-layer";
  layer.setAttribute("aria-hidden", "true");

  layer.appendChild(debugBox("master", MASTER_GRADIENT, "smile-stage__debug-box--master"));
  layer.appendChild(debugBox("subtract", SUBTRACT, "smile-stage__debug-box--subtract"));
  const camHole = getCamHoleCanvas504();
  layer.appendChild(
    debugBox("cam-hole", { frame: SIZE, ...camHole, width: camHole.width, height: camHole.height, left: camHole.left, top: camHole.top }, "smile-stage__debug-box--camera"),
  );
  layer.appendChild(debugBox("pill", PILL, "smile-stage__debug-box--pill"));
  layer.appendChild(debugBox("qr", QR_BOX, "smile-stage__debug-box--qr"));

  ALL_DECOR.forEach((item) => {
    const node = debugBox(`decor:${item.id}`, item, "smile-stage__debug-box--decor");
    node.dataset.debugStages = item.stages.join(" ");
    layer.appendChild(node);
  });

  return layer;
}

export function createSmileStage(container, { debug = false, copy: initialCopy } = {}) {
  let copy = {
    ...DEFAULT_COPY,
    bottomLines: [DEFAULT_COPY.lineBottom],
    ...initialCopy,
  };
  let bottomLineIndex = 0;

  const root = document.createElement("div");
  root.className = "smile-stage";
  root.dataset.stage = "idle";
  root.classList.toggle("smile-stage--debug", debug);

  // Зелёное «поле» отдельным слоем — в нём прорезается окно камеры на cam-open.
  const field = document.createElement("div");
  field.className = "smile-stage__field";
  root.appendChild(field);

  const master = document.createElement("div");
  master.className = "smile-stage__master";
  placeBox(master, mapBox(MASTER_GRADIENT));
  root.appendChild(master);

  // Subtract (Figma 127:569): mask-subtract.svg + inset −11.53% / −9.84%
  const subtractWrap = document.createElement("div");
  subtractWrap.className = "smile-stage__subtract-wrap";
  const subtractBox = mapBox(SUBTRACT);
  const camHole = getCamHoleCanvas504();
  placeBox(subtractWrap, subtractBox);
  subtractWrap.style.setProperty("--subtract-mask-cx", px(camHole.cx - subtractBox.left));
  subtractWrap.style.setProperty("--subtract-mask-cy", px(camHole.cy - subtractBox.top));
  const subtractImg = document.createElement("img");
  subtractImg.className = "smile-stage__subtract";
  subtractImg.src = `${ASSET_BASE}/mask-subtract.svg`;
  subtractImg.alt = "";
  subtractImg.draggable = false;
  subtractWrap.appendChild(subtractImg);
  root.appendChild(subtractWrap);

  const decorLayer = document.createElement("div");
  decorLayer.className = "smile-stage__decor-layer";
  ALL_DECOR.forEach((item, i) => decorLayer.appendChild(decorNode(item, i)));
  root.appendChild(decorLayer);

  const copyLayer = document.createElement("div");
  copyLayer.className = "smile-stage__copy";
  const pillWrap = buildPillCopy(copy);
  const textSvg = buildTextPaths(copy);
  copyLayer.appendChild(pillWrap);
  copyLayer.appendChild(textSvg);
  root.appendChild(copyLayer);

  const qrSlot = document.createElement("div");
  qrSlot.className = "smile-stage__qr-slot";
  const qrFrame = document.createElement("div");
  qrFrame.className = "smile-stage__qr-frame";
  placeBox(qrFrame, mapBox(QR_BOX));

  const qrImageSlot = document.createElement("div");
  qrImageSlot.className = "smile-stage__qr-image";
  const imgBox = mapBox(QR_IMAGE);
  const cardBox = mapBox(QR_BOX);
  qrImageSlot.style.left = px(imgBox.left - cardBox.left);
  qrImageSlot.style.top = px(imgBox.top - cardBox.top);
  qrImageSlot.style.width = px(imgBox.width);
  qrImageSlot.style.height = px(imgBox.height);
  const qrImg = document.createElement("img");
  qrImg.src = `${ASSET_BASE}/${QR_CODE_ASSET}`;
  qrImg.alt = copy.qrCaption;
  qrImg.draggable = false;
  qrImageSlot.appendChild(qrImg);
  qrFrame.appendChild(qrImageSlot);

  const qrCaption = document.createElement("p");
  qrCaption.className = "smile-stage__qr-caption";
  qrCaption.textContent = copy.qrCaption;
  const capBox = mapBox(QR_CAPTION);
  qrCaption.style.left = px(capBox.left - cardBox.left);
  qrCaption.style.top = px(capBox.top - cardBox.top);
  qrCaption.style.width = px(capBox.width);
  qrCaption.style.fontSize = px(QR_CAPTION.fontSize);
  qrCaption.style.lineHeight = String(QR_CAPTION.lineHeight);
  qrCaption.style.color = QR_CAPTION.color;
  qrFrame.appendChild(qrCaption);

  qrSlot.appendChild(qrFrame);
  qrSlot.hidden = true;
  root.appendChild(qrSlot);

  if (debug) {
    root.appendChild(buildDebugOverlay());
  }

  container.replaceChildren(root);

  const shell = document.getElementById("shell");
  const cameraSlot = document.getElementById("camera-slot");
  applyCamVars(shell);
  applyCamVars(cameraSlot);
  applyCamVars(root);

  const topLine = () => root.querySelector('[data-role="top-line"]');
  const bottomLine = () => root.querySelector('[data-role="bottom-line"]');
  const qrCaptionEl = () => root.querySelector(".smile-stage__qr-caption");
  let timer = null;
  let typeTimer = null;
  let holdTextTimer = null;

  function clearTimer() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function clearTypewriter() {
    if (typeTimer) {
      clearTimeout(typeTimer);
      typeTimer = null;
    }
  }

  function clearHoldTextTimer() {
    if (holdTextTimer) {
      clearTimeout(holdTextTimer);
      holdTextTimer = null;
    }
  }

  function syncShell(stage) {
    const camOpen = stage === "face" || stage === "line";
    shell?.classList.toggle("shell--cam-open", camOpen);
    shell?.classList.toggle("shell--master-visible", stage === "idle" || stage === "qr");
  }

  function currentBottomText(stage) {
    if (stage === "face") return copy.lineBottomShort;
    const lines = copy.bottomLines?.length ? copy.bottomLines : [copy.lineBottom];
    return lines[bottomLineIndex % lines.length] ?? copy.lineBottom;
  }

  function updateBottomLine(stage) {
    const node = bottomLine();
    if (!node) return;
    const short = stage === "face";
    node.textContent = currentBottomText(stage);
    const textEl = node.closest(".smile-stage__path-text--bottom");
    if (textEl) {
      textEl.setAttribute(
        "font-size",
        String(short ? TEXT.pathBottomShortSize : TEXT.pathBottomSize),
      );
    }
  }

  function typeBottomLine(text) {
    const node = bottomLine();
    if (!node) return;

    clearTypewriter();
    node.textContent = "";

    const chars = Array.from(text);
    if (!chars.length) return;

    const stepMs = LINE_TYPEWRITER.duration / chars.length;
    let index = 0;

    function tick() {
      if (root.dataset.stage !== "line") {
        clearTypewriter();
        return;
      }

      index += 1;
      node.textContent = chars.slice(0, index).join("");

      if (index < chars.length) {
        typeTimer = setTimeout(tick, stepMs);
      } else {
        typeTimer = null;
      }
    }

    typeTimer = setTimeout(tick, LINE_TYPEWRITER.delay);
  }

  function setSmileHoldProgress(progress) {
    if (root.dataset.stage !== "face") return;

    const node = bottomLine();
    if (!node) return;

    clearHoldTextTimer();

    const text = currentBottomText("line");
    const chars = Array.from(text);
    const clamped = Math.max(0, Math.min(1, Number(progress) || 0));
    const count = Math.min(chars.length, Math.ceil(chars.length * clamped));
    const textEl = node.closest(".smile-stage__path-text--bottom");
    if (textEl) {
      textEl.setAttribute("font-size", String(TEXT.pathBottomSize));
    }

    node.textContent = chars.slice(0, count).join("");
    root.classList.toggle("smile-stage--smile-hold-active", count > 0);
    updateSmileHoldDecor(clamped);
  }

  function updateSmileHoldDecor(progress) {
    const clamped = Math.max(0, Math.min(1, Number(progress) || 0));
    const nodes = [...root.querySelectorAll("[data-hold-decor='true']")];
    const total = Math.max(1, nodes.length);
    for (const node of nodes) {
      const index = Number(node.style.getPropertyValue("--hold-i")) || 0;
      const threshold = (index + 1) / (total + 1);
      node.classList.toggle("smile-stage__decor--hold-visible", clamped >= threshold);
    }
  }

  function completeSmileHoldText() {
    setSmileHoldProgress(1);
  }

  function fadeSmileHoldText() {
    if (root.dataset.stage !== "face") return;

    const node = bottomLine();
    if (!node || holdTextTimer) return;
    if (!root.classList.contains("smile-stage--smile-hold-active")) {
      node.textContent = "";
      return;
    }

    const stepMs = 28;

    function tick() {
      if (root.dataset.stage !== "face") {
        clearHoldTextTimer();
        return;
      }

      const chars = Array.from(node.textContent);
      if (!chars.length) {
        root.classList.remove("smile-stage--smile-hold-active");
        updateSmileHoldDecor(0);
        holdTextTimer = null;
        return;
      }

      root.classList.add("smile-stage--smile-hold-active");
      node.textContent = chars.slice(0, -1).join("");
      updateSmileHoldDecor(Math.max(0, (chars.length - 1) / Array.from(currentBottomText("line")).length));
      holdTextTimer = setTimeout(tick, stepMs);
    }

    holdTextTimer = setTimeout(tick, stepMs);
  }

  function applyCopy(next) {
    copy = {
      ...copy,
      ...next,
      bottomLines: next.bottomLines?.length ? next.bottomLines : copy.bottomLines,
    };

    const main = root.querySelector(".smile-stage__pill-main");
    const cta = root.querySelector(".smile-stage__pill-cta");
    if (main) main.textContent = copy.teaser;
    if (cta) cta.textContent = copy.cta;
    if (topLine()) topLine().textContent = copy.lineTop;
    if (qrCaptionEl()) qrCaptionEl().textContent = copy.qrCaption;
    if (qrImg) qrImg.alt = copy.qrCaption;
    updateBottomLine(root.dataset.stage);
  }

  function setBottomLineIndex(index) {
    bottomLineIndex = Math.max(0, index);
    if (root.dataset.stage !== "face") updateBottomLine(root.dataset.stage);
  }

  function setStage(stage) {
    if (!STAGES.includes(stage)) return;
    clearTimer();
    clearTypewriter();
    clearHoldTextTimer();
    root.classList.remove(
      "smile-stage--cam-open",
      "smile-stage--line-expanded",
      "smile-stage--stickers-in",
      "smile-stage--stickers-out",
      "smile-stage--stickers-curtain",
      "smile-stage--dissolve",
      "smile-stage--smile-hold-active",
    );
    updateSmileHoldDecor(0);
    root.dataset.stage = stage;
    syncShell(stage);
    updateBottomLine(stage);

    if (stage === "face") {
      root.classList.add("smile-stage--cam-open");
    }
    if (stage === "line") {
      root.classList.add("smile-stage--cam-open", "smile-stage--line-expanded");
      typeBottomLine(currentBottomText("line"));
    }
    if (stage === "stickers") {
      requestAnimationFrame(() => root.classList.add("smile-stage--stickers-in"));
    }
    if (stage === "qr") {
      root.classList.add("smile-stage--dissolve");
    }

    qrSlot.hidden = stage !== "qr";
  }

  function revealCamera() {
    setStage("face");
  }

  function hideCamera() {
    setStage("idle");
  }

  function showLine() {
    setStage("line");
  }

  function playPostSmileSequence({ onComplete, skipLine = false } = {}) {
    if (!skipLine) showLine();

    timer = setTimeout(() => {
      setStage("stickers");
      timer = setTimeout(() => {
        setStage("qr");
        root.classList.add("smile-stage--stickers-curtain");
        requestAnimationFrame(() => root.classList.add("smile-stage--stickers-out"));
        timer = setTimeout(() => {
          root.classList.remove("smile-stage--stickers-curtain", "smile-stage--stickers-out");
          timer = setTimeout(() => {
            root.classList.add("smile-stage--stickers-curtain");
            requestAnimationFrame(() => root.classList.add("smile-stage--stickers-in"));
            timer = setTimeout(() => {
              setStage("idle");
              root.classList.add("smile-stage--stickers-curtain", "smile-stage--stickers-in");
              requestAnimationFrame(() => root.classList.add("smile-stage--stickers-out"));
              timer = setTimeout(() => {
                root.classList.remove("smile-stage--stickers-curtain", "smile-stage--stickers-in", "smile-stage--stickers-out");
                onComplete?.();
              }, STICKERS_OUT_MS);
            }, STICKERS_IN_MS);
          }, STAGE_TIMING.qr);
        }, STICKERS_OUT_MS);
      }, STAGE_TIMING.stickers);
    }, skipLine ? 0 : STAGE_TIMING.line);
  }

  function reset() {
    clearTimer();
    clearTypewriter();
    clearHoldTextTimer();
    root.classList.remove(
      "smile-stage--cam-open",
      "smile-stage--line-expanded",
      "smile-stage--stickers-in",
      "smile-stage--stickers-out",
      "smile-stage--stickers-curtain",
      "smile-stage--dissolve",
      "smile-stage--smile-hold-active",
    );
    updateSmileHoldDecor(0);
    root.dataset.stage = "idle";
    syncShell("idle");
    updateBottomLine("idle");
    qrSlot.hidden = true;
  }

  return {
    root,
    setStage,
    revealCamera,
    hideCamera,
    showLine,
    playPostSmileSequence,
    reset,
    applyCopy,
    setBottomLineIndex,
    setSmileHoldProgress,
    completeSmileHoldText,
    fadeSmileHoldText,
    getCopy: () => ({ ...copy }),
    getQrSlot: () => qrSlot,
  };
}
