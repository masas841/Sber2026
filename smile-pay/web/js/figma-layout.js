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
  qrCaption: "Подключить оплату улыбкой",
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
  { id: "hold-bg-sber", src: "hold-bg-sber.svg", left: -12.975, top: 149.025, width: 137.633, height: 137.633, rotate: 27.55, stages: ["face"], frame: 515, holdIndex: 0 },
  { id: "hold-bg-star-left", src: "hold-bg-star-left.svg", left: 15.612, top: 224.612, width: 66.306, height: 66.306, rotate: -20.8, stages: ["face"], frame: 515, holdIndex: 1 },
  { id: "hold-bg-smile-left", src: "hold-bg-smile-left.svg", left: 50.218, top: 349.218, width: 91.18, height: 91.18, rotate: -20.8, stages: ["face"], frame: 515, holdIndex: 2 },
  { id: "hold-bg-wave-left", src: "hold-bg-wave-left.svg", left: -1.1, top: 289.106, width: 116.213, height: 116.213, rotate: 57.55, stages: ["face"], frame: 515, holdIndex: 3 },
  { id: "hold-bg-wave-right-top", src: "hold-bg-wave-right-top.svg", left: 405.9, top: 205.028, width: 82.437, height: 82.437, rotate: 57.55, stages: ["face"], frame: 515, holdIndex: 4 },
  { id: "hold-bg-smile-right", src: "hold-bg-smile-right.svg", left: 426.218, top: 231.218, width: 91.18, height: 91.18, rotate: -20.8, stages: ["face"], frame: 515, holdIndex: 5 },
  { id: "hold-bg-star-pink-right", src: "hold-bg-star-pink-right.svg", left: 384.953, top: 281.952, width: 37.37, height: 37.37, rotate: -9.97, stages: ["face"], frame: 515, holdIndex: 6 },
  { id: "hold-bg-wave-right-low", src: "hold-bg-wave-right-low.svg", left: 377.2, top: 317.166, width: 100.754, height: 100.754, rotate: 57.55, stages: ["face"], frame: 515, holdIndex: 7 },
  { id: "hold-bg-star-pink-small", src: "hold-bg-star-pink-small.svg", left: 115.54, top: 318.54, width: 31.194, height: 31.194, rotate: 10.31, stages: ["face"], frame: 515, holdIndex: 8 },
  { id: "hold-bg-star-blue-small", src: "hold-bg-star-blue-small.svg", left: 126.258, top: 368.255, width: 45.182, height: 45.181, rotate: -9.83, stages: ["face"], frame: 515, holdIndex: 9 },
];

/** Frame 1 — line (get_design_context 25:2498) */
const LINE_DECOR = [
  { id: "line-bg-sber", src: "hold-bg-sber.svg", left: -12.975, top: 149.025, width: 137.633, height: 137.633, rotate: 27.55, stages: ["line"], frame: 515 },
  { id: "line-bg-star-left", src: "hold-bg-star-left.svg", left: 15.612, top: 224.612, width: 66.306, height: 66.306, rotate: -20.8, stages: ["line"], frame: 515 },
  { id: "line-bg-smile-left", src: "hold-bg-smile-left.svg", left: 50.218, top: 349.218, width: 91.18, height: 91.18, rotate: -20.8, stages: ["line"], frame: 515 },
  { id: "line-bg-wave-left", src: "hold-bg-wave-left.svg", left: -1.1, top: 289.106, width: 116.213, height: 116.213, rotate: 57.55, stages: ["line"], frame: 515 },
  { id: "line-bg-wave-right-top", src: "hold-bg-wave-right-top.svg", left: 405.9, top: 205.028, width: 82.437, height: 82.437, rotate: 57.55, stages: ["line"], frame: 515 },
  { id: "line-bg-smile-right", src: "hold-bg-smile-right.svg", left: 426.218, top: 231.218, width: 91.18, height: 91.18, rotate: -20.8, stages: ["line"], frame: 515 },
  { id: "line-bg-star-pink-right", src: "hold-bg-star-pink-right.svg", left: 384.953, top: 281.952, width: 37.37, height: 37.37, rotate: -9.97, stages: ["line"], frame: 515 },
  { id: "line-bg-wave-right-low", src: "hold-bg-wave-right-low.svg", left: 377.2, top: 317.166, width: 100.754, height: 100.754, rotate: 57.55, stages: ["line"], frame: 515 },
  { id: "line-bg-star-pink-small", src: "hold-bg-star-pink-small.svg", left: 115.54, top: 318.54, width: 31.194, height: 31.194, rotate: 10.31, stages: ["line"], frame: 515 },
  { id: "line-bg-star-blue-small", src: "hold-bg-star-blue-small.svg", left: 126.258, top: 368.255, width: 45.182, height: 45.181, rotate: -9.83, stages: ["line"], frame: 515 },
  { id: "star-mid-r", src: "star-mid.svg", left: 429.34, top: 164.02, width: 77.471, height: 77.469, rotate: 22.83, stages: ["line"], frame: 515 },
  { id: "star-sm-r", src: "star-small.svg", left: 434, top: 137, width: 43.275, height: 43.274, rotate: -9.97, stages: ["line"], frame: 515 },
  { id: "star-tiny-l", src: "star-tiny.svg", left: 18, top: 152, width: 49.947, height: 49.947, rotate: -25.93, stages: ["line"], frame: 515 },
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
  { id: "cluster-tr", src: "qr-cluster-tr.svg", left: 309, top: 253, width: 164, height: 164, stages: ["qr"], frame: 504 },
  { id: "cluster-tl", src: "qr-cluster-tl.svg", left: 64, top: 152, width: 124, height: 124, stages: ["qr"], frame: 504 },
  { id: "smile-qr", src: "sticker-smile-qr.svg", left: 43.4, top: 84.7, width: 95.1, height: 95.1, rotate: -8, stages: ["qr"], frame: 504 },
  { id: "spring-qr", src: "spring-scribble-qr.svg", left: 285.2, top: 358.3, width: 138.1, height: 107.7, rotate: -63.73, stages: ["qr"], frame: 504 },
  { id: "star-qr-blue", src: "star-qr-blue.svg", left: 383.2, top: 325.1, width: 50.2, height: 50.2, stages: ["qr"], frame: 504 },
  { id: "star-qr-pink", src: "star-qr-pink.svg", left: 97.5, top: 72.3, width: 51.4, height: 51.4, stages: ["qr"], frame: 504 },
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
