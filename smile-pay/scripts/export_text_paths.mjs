// Генерирует SVG-ассеты text-path из геометрии кольца Figma.
// Usage: node scripts/export_text_paths.mjs

import { writeFileSync, mkdirSync } from "node:fs";
import { TEXT_PATHS, TEXT_PATH_META } from "../web/js/text-paths.js";

const OUT = "web/assets/figma";
const VB = TEXT_PATH_META.frame;

mkdirSync(OUT, { recursive: true });

function svgFor(id, d) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VB} ${VB}" fill="none">
  <path id="${id}" d="${d}" stroke="#fff" stroke-width="1" opacity="0.35"/>
</svg>
`;
}

writeFileSync(`${OUT}/text-path-top.svg`, svgFor("text-path-top", TEXT_PATHS.top));
writeFileSync(`${OUT}/text-path-bottom.svg`, svgFor("text-path-bottom", TEXT_PATHS.bottom));
writeFileSync(
  `${OUT}/text-paths.json`,
  JSON.stringify({ meta: TEXT_PATH_META, paths: TEXT_PATHS }, null, 2),
);

console.log("[saved] text-path-top.svg, text-path-bottom.svg, text-paths.json");
console.log(JSON.stringify(TEXT_PATHS, null, 2));
