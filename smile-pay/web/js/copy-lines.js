/**
 * Загрузка текстов из web/assets/copy/lines.txt
 * Формат: [section] + строки до следующей секции.
 */

import { COPY as DEFAULT_COPY } from "./figma-layout.js";

const COPY_URL = "/static/assets/copy/lines.txt";

/**
 * @typedef {typeof DEFAULT_COPY & { bottomLines: string[] }} CopyBundle
 */

/**
 * @param {string} text
 * @returns {CopyBundle}
 */
export function parseLinesTxt(text) {
  const sections = new Map();
  let current = null;

  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const m = line.match(/^\[([a-z_]+)\]$/i);
    if (m) {
      current = m[1].toLowerCase();
      sections.set(current, []);
      continue;
    }
    if (current) sections.get(current).push(line);
  }

  const pick = (key, fallback) => sections.get(key)?.[0] ?? fallback;
  const bottomLines = sections.get("bottom")?.length
    ? sections.get("bottom")
    : [DEFAULT_COPY.lineBottom];

  return {
    teaser: pick("teaser", DEFAULT_COPY.teaser),
    cta: pick("cta", DEFAULT_COPY.cta),
    lineTop: pick("top", DEFAULT_COPY.lineTop),
    lineBottom: bottomLines[0],
    lineBottomShort: pick("bottom_short", DEFAULT_COPY.lineBottomShort),
    qrCaption: pick("qr_caption", DEFAULT_COPY.qrCaption),
    bottomLines,
  };
}

/** @returns {Promise<CopyBundle>} */
export async function loadCopyLines(url = COPY_URL) {
  try {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return parseLinesTxt(await res.text());
  } catch (err) {
    console.warn("copy-lines: fallback to defaults", err);
    return {
      ...DEFAULT_COPY,
      bottomLines: [DEFAULT_COPY.lineBottom],
    };
  }
}
