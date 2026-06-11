/**
 * Subtract (Figma 127:569) — зелёное кольцо 504×504 + feGaussianBlur как mask-subtract.svg.
 * Фон статичен; растёт только отверстие (--cam-reveal-r).
 */

import { SIZE } from "./figma-layout.js";
import { getCamHoleCanvas504 } from "./cam-geometry.js";

function fmt(n) {
  return Number(n.toFixed(4));
}

/** @param {ReturnType<typeof getCamHoleCanvas504>} [hole] */
export function buildSubtractSvg504(hole = getCamHoleCanvas504()) {
  const { cx, cy, feather } = hole;

  return `<svg class="smile-stage__subtract" viewBox="0 0 ${SIZE} ${SIZE}" width="${SIZE}" height="${SIZE}" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<defs>
<filter id="subtract-blur" x="0" y="0" width="${SIZE}" height="${SIZE}" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
<feGaussianBlur in="SourceGraphic" stdDeviation="${fmt(feather)}"/>
</filter>
<mask id="subtract-ring-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="${SIZE}" height="${SIZE}">
<rect width="${SIZE}" height="${SIZE}" fill="white"/>
<circle class="smile-stage__subtract-hole" cx="${fmt(cx)}" cy="${fmt(cy)}" fill="black"/>
</mask>
</defs>
<rect width="${SIZE}" height="${SIZE}" fill="#A0DD29" mask="url(#subtract-ring-mask)" filter="url(#subtract-blur)"/>
</svg>`;
}

/** @deprecated Используйте buildSubtractSvg504 */
export const SUBTRACT_SVG = buildSubtractSvg504();
