/**
 * Дуги text-path по геометрии Subtract / Ellipse 28798 (frame 515).
 * Figma nodes: 128:111 (верх), 127:512 / 127:573 (низ).
 * MCP не экспортирует path data text-path → полукруги через cubic bezier (k≈0.5523).
 */

const FIGMA_RING = 515;
const K = 0.5522847498;
/** Центр кольца 515×515 (совпадает с cam-geometry RING_CENTER_515) */
const CX = FIGMA_RING / 2;
const CY = FIGMA_RING / 2;
/** Радиус отверстия камеры в 515 (Ellipse 28798) */
const HOLE_R = 414.60553 / 2;

/** Текст идёт по внутреннему краю кольца, чуть снаружи отверстия камеры */
const TOP_R = HOLE_R + 11.2;
const BOTTOM_R = HOLE_R + 11.7;

function upperSemicircle(cx, cy, r) {
  return [
    `M ${fmt(cx - r)} ${fmt(cy)}`,
    `C ${fmt(cx - r)} ${fmt(cy - r * K)}, ${fmt(cx - r * K)} ${fmt(cy - r)}, ${fmt(cx)} ${fmt(cy - r)}`,
    `C ${fmt(cx + r * K)} ${fmt(cy - r)}, ${fmt(cx + r)} ${fmt(cy - r * K)}, ${fmt(cx + r)} ${fmt(cy)}`,
  ].join(" ");
}

function lowerSemicircle(cx, cy, r) {
  return [
    `M ${fmt(cx - r)} ${fmt(cy)}`,
    `C ${fmt(cx - r)} ${fmt(cy + r * K)}, ${fmt(cx - r * K)} ${fmt(cy + r)}, ${fmt(cx)} ${fmt(cy + r)}`,
    `C ${fmt(cx + r * K)} ${fmt(cy + r)}, ${fmt(cx + r)} ${fmt(cy + r * K)}, ${fmt(cx + r)} ${fmt(cy)}`,
  ].join(" ");
}

function fmt(n) {
  return Number(n.toFixed(3));
}

export const TEXT_PATH_META = {
  frame: FIGMA_RING,
  figmaNodes: {
    top: "128:111",
    bottomFull: "127:512",
    bottomShort: "127:573",
  },
  center: { x: CX, y: CY },
  radii: { hole: HOLE_R, top: TOP_R, bottom: BOTTOM_R },
};

export const TEXT_PATHS = {
  top: upperSemicircle(CX, CY, TOP_R),
  bottom: lowerSemicircle(CX, CY, BOTTOM_R),
};
