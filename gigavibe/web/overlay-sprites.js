/** Декоративные оверлеи на экранах камеры и результата (киоск 1008×672). */

const FIGMA_FLOWERS = [
  {
    src: "/static/assets/figma/ui/front-flower-left.png",
    x: -57,
    y: 314,
    w: 485.207,
    h: 498.69,
    transform: "scaleY(-1) rotate(160.73deg)",
    innerW: 375.168,
    innerH: 397.129,
    img: {
      width: "225.85%",
      height: "213.36%",
      left: "-62.93%",
      top: "-25.58%",
    },
  },
  {
    src: "/static/assets/figma/ui/front-flower-right.png",
    x: -222,
    y: 174,
    w: 505.779,
    h: 719.184,
    transform: "rotate(18.46deg)",
    innerW: 315.203,
    innerH: 652.97,
    img: {
      width: "207.16%",
      height: "100%",
      left: "-107.16%",
      top: "0",
    },
  },
];

let captureBackLayer = null;
let captureFrontLayer = null;
let resultBackLayer = null;
let resultFrontLayer = null;

function appendFlower(parent, flower) {
  const wrap = document.createElement("div");
  wrap.className = "overlay-flower-wrap";
  wrap.style.left = `${flower.x}px`;
  wrap.style.top = `${flower.y}px`;
  wrap.style.width = `${flower.w}px`;
  wrap.style.height = `${flower.h}px`;

  const transformed = document.createElement("div");
  transformed.className = "overlay-flower-transform";
  transformed.style.width = `${flower.innerW}px`;
  transformed.style.height = `${flower.innerH}px`;
  transformed.style.transform = flower.transform;

  const crop = document.createElement("div");
  crop.className = "overlay-flower-crop";

  const img = document.createElement("img");
  img.className = "overlay-flower";
  img.src = flower.src;
  img.alt = "";
  img.draggable = false;
  img.loading = "eager";
  img.decoding = "async";
  img.style.left = flower.img.left;
  img.style.top = flower.img.top;
  img.style.width = flower.img.width;
  img.style.height = flower.img.height;

  crop.appendChild(img);
  transformed.appendChild(crop);
  wrap.appendChild(transformed);
  parent.appendChild(wrap);
}

function appendFigmaFlowers(parent) {
  for (const flower of FIGMA_FLOWERS) {
    appendFlower(parent, flower);
  }
}

export async function initCaptureOverlays({ back, front, resultBack, resultFront }) {
  captureBackLayer = back;
  captureFrontLayer = front;
  resultBackLayer = resultBack;
  resultFrontLayer = resultFront;
  relayoutCaptureOverlays();
  relayoutResultOverlays();
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
  if (!captureBackLayer || !captureFrontLayer) return;

  captureBackLayer.replaceChildren();
  captureFrontLayer.replaceChildren();
  appendFigmaFlowers(captureFrontLayer);
}

export function relayoutResultOverlays() {
  if (!resultBackLayer || !resultFrontLayer) return;

  resultBackLayer.replaceChildren();
  resultFrontLayer.replaceChildren();
  appendFigmaFlowers(resultFrontLayer);
}
