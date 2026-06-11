/**

 * SVG-маска окна камеры — система 504×504, центр градиента (252, 252).

 */



import { SIZE } from "./figma-layout.js";

import { getCamHoleCanvas504 } from "./cam-geometry.js";



const MASK_ID = "cam-hole-mask-defs";



export function ensureCamMaskDefs() {

  const h = getCamHoleCanvas504();

  const solidStop = Math.max(0, 100 - h.softPct);

  const cx = h.cx;

  const cy = h.cy;

  const r = Math.max(h.rx, h.ry);



  let svg = document.getElementById(MASK_ID);

  if (!svg) {

    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");

    svg.id = MASK_ID;

    svg.setAttribute("width", "0");

    svg.setAttribute("height", "0");

    svg.setAttribute("aria-hidden", "true");

    document.body.appendChild(svg);

  }



  svg.innerHTML = `

    <defs>

      <radialGradient id="cam-hole-feather" gradientUnits="userSpaceOnUse" cx="${cx}" cy="${cy}" r="${r}">

        <stop offset="0%" stop-color="white"/>

        <stop offset="${solidStop.toFixed(2)}%" stop-color="white"/>

        <stop offset="100%" stop-color="transparent"/>

      </radialGradient>

      <mask id="cam-hole-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="${SIZE}" height="${SIZE}">

        <rect width="${SIZE}" height="${SIZE}" fill="black"/>

        <circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#cam-hole-feather)"/>

      </mask>

    </defs>

  `;

}


