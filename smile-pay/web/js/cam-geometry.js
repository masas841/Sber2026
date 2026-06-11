/**
 * Окно камеры — размер из Figma Ellipse 28798, центр в canvas 504×504.
 */

import { SIZE, S, CAM_HOLE, mapBox } from "./figma-layout.js";

const CAM_WINDOW_OFFSET_Y = -10;

/** Центр кольца в координатах Figma frame 515 (для text-path) */
export const RING_CENTER_515 = {
  x: 257.5,
  y: 257.5,
};

/** Геометрия отверстия в canvas 504 */
export function getCamHoleCanvas504() {
  const figmaHole = mapBox(CAM_HOLE);
  const cx = SIZE / 2;
  const cy = SIZE / 2 + CAM_WINDOW_OFFSET_Y;
  const rx = figmaHole.width / 2;
  const ry = figmaHole.height / 2;
  /** feGaussianBlur stdDeviation из mask-subtract.svg */
  const feather = 39.7 * S;
  const softPct = Math.min(36, (feather / rx) * 135);

  return {
    cx,
    cy,
    rx,
    ry,
    left: cx - rx,
    top: cy - ry,
    width: figmaHole.width,
    height: figmaHole.height,
    feather,
    softPct,
    rxPct: (rx / SIZE) * 100,
    ryPct: (ry / SIZE) * 100,
  };
}

export function applyCamVars(el) {
  if (!el) return;
  const h = getCamHoleCanvas504();
  el.style.setProperty("--cam-cx", `${h.cx}px`);
  el.style.setProperty("--cam-cy", `${h.cy}px`);
  el.style.setProperty("--cam-rx", `${h.rx}px`);
  el.style.setProperty("--cam-ry", `${h.ry}px`);
  el.style.setProperty("--cam-hole-x", `${h.left}px`);
  el.style.setProperty("--cam-hole-y", `${h.top}px`);
  el.style.setProperty("--cam-hole-w", `${h.width}px`);
  el.style.setProperty("--cam-hole-h", `${h.height}px`);
  el.style.setProperty("--cam-feather", `${h.feather}px`);
  el.style.setProperty("--cam-soft", `${h.softPct}%`);

  const view = el.classList?.contains("camera-slot")
    ? el.querySelector(".camera-slot__view")
    : el.closest?.(".camera-slot")?.querySelector(".camera-slot__view");
  if (view) {
    view.style.left = `${h.left}px`;
    view.style.top = `${h.top}px`;
    view.style.width = `${h.width}px`;
    view.style.height = `${h.height}px`;
  }
}
