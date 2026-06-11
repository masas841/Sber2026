/**
 * Координаты из Figma section 128:109 (обновление 2026-06-09).
 * idle/qr = 504; face/line/stickers = 515 → масштаб S.
 */

export const SIZE = 504;
export const FIGMA_RING = 515;
export const S = SIZE / FIGMA_RING;

export const COPY = {
  teaser: "Такой улыбкой можно оплатить…",
  cta: "",
  lineTop: "Такой улыбкой можно оплатить…",
  lineBottom: "самый сочный бургер на фудкорте",
  lineBottomShort: "самый…",
  qrCaption: "Узнай больше про биометрию",
};

export const MASTER_GRADIENT = {
  frame: 504,
  left: -201,
  top: -72,
  width: 1205.656,
  height: 678.609,
};

export const SUBTRACT = {
  frame: 515,
  left: -152,
  top: -92.69,
  width: 807,
  height: 688.542,
};

export const CAM_HOLE = {
  frame: 515,
  left: 43.948883,
  top: 43.96048,
  width: 414.60553,
  height: 414.60553,
};

/** Frame 3 — pill + текст (metadata 127:557, 127:545, 127:556) */
export const PILL = {
  frame: 504,
  left: 13.343225,
  top: 200.916016,
  width: 477.313679,
  height: 199.541739,
  innerWidth: 464.17,
  innerHeight: 153.299,
  rotate: -5.82,
  radius: 73.5,
};

export const TEXT = {
  pillMain: {
    left: 53,
    top: 216.926041,
    width: 403.29786,
    fontSize: 39.316,
    lineHeight: 0.98,
  },
  pillCta: {
    left: 126,
    top: 295.727539,
    width: 266.553125,
    fontSize: 25.985,
    lineHeight: 0.98,
  },
  pathTopSize: 22,
  pathBottomSize: 25.5,
  pathBottomShortSize: 25.5,
};

/** Frame 6 — карточка QR (137:1456) */
export const QR_CARD = {
  frame: 504,
  left: 123,
  top: 92,
  width: 258,
  height: 321,
  radius: 25,
};

/** QR-код из макета Figma (node 137:115) — PNG-экспорт, не генерируется */
export const QR_CODE_ASSET = "qr-code.png";

export const QR_IMAGE = {
  frame: 504,
  left: 129,
  top: 97,
  width: 245,
  height: 245,
};

export const QR_CAPTION = {
  frame: 504,
  left: 149.714233,
  top: 342,
  width: 204.285751,
  fontSize: 20.923,
  lineHeight: 0.98,
  color: "rgba(12, 15, 46, 0.99)",
};

/** @deprecated use QR_CARD */
export const QR_BOX = QR_CARD;

/** Frame 3 — idle decor */
const IDLE_DECOR = [
  { id: "sber", src: "sticker-sber.svg", left: 37.127487, top: -41.716385, width: 300.001467, height: 300.001467, rotate: 27.55, stages: ["idle"], frame: 504 },
  { id: "smile", src: "sticker-smile.svg", left: 320, top: 287.783936, width: 202.637874, height: 202.637874, rotate: -20.8, stages: ["idle"], frame: 504 },
  { id: "spring", src: "spring-scribble.svg", left: -10, top: 305.354523, width: 188.594611, height: 158.532198, rotate: -10.05, stages: ["idle"], frame: 504 },
  { id: "star-lg", src: "star-large.svg", left: 326.539001, top: 113, width: 87.86753, height: 87.864846, rotate: 13.05, stages: ["idle"], frame: 504 },
  { id: "star-sm", src: "star-small.svg", left: 268.342773, top: 103.350594, width: 53.564031, height: 53.563611, rotate: -9.97, stages: ["idle"], frame: 504 },
];

/** Frame 4 — face (get_design_context 127:567) */
const FACE_DECOR = [
  { id: "star-mid-r", src: "star-mid.svg", left: 429.34, top: 164.02, width: 77.471, height: 77.469, rotate: 22.83, stages: ["face"], frame: 515 },
  { id: "star-sm-r", src: "star-small.svg", left: 434, top: 137, width: 43.275, height: 43.274, rotate: -9.97, stages: ["face"], frame: 515 },
  { id: "star-tiny-l", src: "star-tiny.svg", left: 12, top: 151, width: 49.947, height: 49.947, rotate: -25.93, stages: ["face"], frame: 515 },
];

/** Стикеры, которые появляются во время удержания улыбки и печати нижнего лайна */
const SMILE_HOLD_DECOR = [
  { id: "hold-flower-green", src: "hold-flower-green.svg", left: 1, top: 150, width: 82, height: 82, rotate: 16, stages: ["face"], frame: 504, holdIndex: 0 },
  { id: "hold-smile-blue", src: "hold-smile-blue.svg", left: 24, top: 189, width: 68, height: 68, rotate: -10, stages: ["face"], frame: 504, holdIndex: 1 },
  { id: "hold-smile-pink", src: "hold-smile-pink.svg", left: 0, top: 282, width: 82, height: 82, rotate: -12, stages: ["face"], frame: 504, holdIndex: 2 },
  { id: "hold-smile-green", src: "hold-smile-green.svg", left: 57, top: 333, width: 78, height: 78, rotate: 13, stages: ["face"], frame: 504, holdIndex: 3 },
  { id: "hold-flower-lime", src: "hold-flower-lime.svg", left: 340, top: 302, width: 82, height: 82, rotate: -14, stages: ["face"], frame: 504, holdIndex: 4 },
  { id: "hold-smile-blue-2", src: "hold-smile-blue.svg", left: 374, top: 150, width: 68, height: 68, rotate: 11, stages: ["face"], frame: 504, holdIndex: 5 },
  { id: "hold-flower-green-2", src: "hold-flower-green.svg", left: 398, top: 252, width: 82, height: 82, rotate: -9, stages: ["face"], frame: 504, holdIndex: 6 },
  { id: "hold-smile-pink-2", src: "hold-smile-pink.svg", left: 404, top: 192, width: 82, height: 82, rotate: 8, stages: ["face"], frame: 504, holdIndex: 7 },
  { id: "hold-flower-lime-2", src: "hold-flower-lime.svg", left: 112, top: 357, width: 82, height: 82, rotate: 18, stages: ["face"], frame: 504, holdIndex: 8 },
  { id: "hold-smile-green-2", src: "hold-smile-green.svg", left: 31, top: 238, width: 78, height: 78, rotate: -16, stages: ["face"], frame: 504, holdIndex: 9 },
];

/** Frame 1 — line (get_design_context 25:2498) */
const LINE_DECOR = [
  { id: "star-mid-r", src: "star-mid.svg", left: 400.5, top: 212, width: 77.471, height: 77.469, rotate: 22.83, stages: ["line"], frame: 515 },
  { id: "star-tiny-l", src: "star-tiny.svg", left: 12, top: 151, width: 49.947, height: 49.947, rotate: -25.93, stages: ["line"], frame: 515 },
  { id: "smile-sm", src: "sticker-smile.svg", left: 418.5, top: 258, width: 117.616, height: 117.616, rotate: -20.8, stages: ["line"], frame: 515 },
  { id: "sber-sm", src: "sticker-sber.svg", left: -66.03, top: 195.47, width: 185.683, height: 185.683, rotate: 27.55, stages: ["line"], frame: 515 },
];

/** Frame 5 — stickers */
const STICKERS_DECOR = [
  { id: "wave-a", src: "wave-curve.svg", left: 239.721252, top: 72.886124, width: 364.534296, height: 364.534296, rotate: 57.55, stages: ["stickers"], frame: 515 },
  { id: "wave-b", src: "wave-curve.svg", left: 287, top: 57, width: 364.534296, height: 364.534296, rotate: 57.55, stages: ["stickers"], frame: 515 },
  { id: "cl-a", src: "sticker-cluster-a.svg", left: 179, top: 219.978897, width: 328.338767, height: 328.338767, rotate: -17.57, stages: ["stickers"], frame: 515 },
  { id: "cl-b", src: "sticker-cluster-b.svg", left: 64, top: 11.436444, width: 525.633887, height: 525.633887, rotate: -17.57, stages: ["stickers"], frame: 515 },
  { id: "cl-c", src: "sticker-cluster-c.svg", left: -70, top: 290.978912, width: 328.338767, height: 328.338767, rotate: -17.57, stages: ["stickers"], frame: 515 },
  { id: "cl-d", src: "sticker-cluster-d.svg", left: 39, top: -20.021101, width: 328.338767, height: 328.338767, rotate: -17.57, stages: ["stickers"], frame: 515 },
  { id: "smile", src: "sticker-smile.svg", left: 334, top: 306.783936, width: 202.637874, height: 202.637874, rotate: -20.8, stages: ["stickers"], frame: 515 },
  { id: "cl-e", src: "sticker-cluster-e.svg", left: 11.543343, top: 151, width: 198.618439, height: 198.618439, rotate: 18.38, stages: ["stickers"], frame: 515 },
  { id: "cl-f", src: "sticker-cluster-f.svg", left: 135, top: 97.441544, width: 207.707781, height: 207.707781, rotate: -24.22, stages: ["stickers"], frame: 515 },
  { id: "cl-g", src: "sticker-cluster-g.svg", left: 175.7173, top: 278, width: 216.267945, height: 216.267945, rotate: 31.77, stages: ["stickers"], frame: 515 },
  { id: "sber-lg", src: "sticker-sber-lg.svg", left: 61.973286, top: -46, width: 352.885926, height: 352.885926, rotate: 27.55, stages: ["stickers"], frame: 515 },
  { id: "cl-h", src: "sticker-cluster-h.svg", left: 251.439651, top: 239.000031, width: 400.919386, height: 400.919386, rotate: 27.55, stages: ["stickers"], frame: 515 },
  { id: "star-mid", src: "star-mid.svg", left: 106.948334, top: 73, width: 77.471208, height: 77.469329, rotate: 22.83, stages: ["stickers"], frame: 515 },
  { id: "star-big", src: "star-big.svg", left: 258, top: 419.798737, width: 102.617689, height: 102.618186, rotate: -30.25, stages: ["stickers"], frame: 515 },
  { id: "star-tiny", src: "star-tiny.svg", left: 12, top: 151, width: 49.947, height: 49.947, rotate: -25.93, stages: ["stickers"], frame: 515 },
];

/** Frame 6 — qr decor (selected Figma frame 127:713) */
const QR_DECOR = [
  { id: "cluster-tr", src: "qr-cluster.svg", left: 406.365112, top: 220, width: 224.714509, height: 224.714509, stages: ["qr"], frame: 504 },
  { id: "cluster-tl", src: "qr-cluster.svg", left: 144.365097, top: 84, width: 224.714509, height: 224.714509, stages: ["qr"], frame: 504 },
  { id: "smile-qr", src: "sticker-smile-qr.svg", left: 23, top: 109.922012, width: 126.855921, height: 126.855921, stages: ["qr"], frame: 504 },
  { id: "spring-qr", src: "spring-scribble-qr.svg", left: 278.180064, top: 383.054575, width: 164.448, height: 128.192, rotate: -63.73, stages: ["qr"], frame: 504 },
  { id: "star-qr-blue", src: "star-qr-blue.svg", left: 391.90976, top: 316, width: 62.749671, height: 62.747933, stages: ["qr"], frame: 504 },
  { id: "star-qr-pink", src: "star-qr-pink.svg", left: 89, top: 78.429565, width: 68.528644, height: 68.52852, stages: ["qr"], frame: 504 },
];

export const ALL_DECOR = [
  ...IDLE_DECOR,
  ...FACE_DECOR,
  ...SMILE_HOLD_DECOR,
  ...LINE_DECOR,
  ...STICKERS_DECOR,
  ...QR_DECOR,
];

export { TEXT_PATHS, TEXT_PATH_META } from "./text-paths.js";

export function mapBox({ left, top, width, height, frame = 504 }) {
  const k = frame === FIGMA_RING ? S : 1;
  return {
    left: left * k,
    top: top * k,
    width: width * k,
    height: height * k,
  };
}

export function mapValue(value, frame = 504) {
  return frame === FIGMA_RING ? value * S : value;
}
