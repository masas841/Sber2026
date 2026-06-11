// Capture rendered Smile Pay stages for visual diff vs Figma.
// Usage: node scripts/shot_browser.mjs
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const OUT = "scripts/figma_out";
const BASE = "http://127.0.0.1:8888";
const stages = ["idle", "face", "line", "stickers", "qr"];

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 560, height: 560 } });

for (const stage of stages) {
  await page.goto(`${BASE}/?stage=${stage}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  const shell = await page.$("#shell");
  const file = `${OUT}/browser_${stage}.png`;
  if (shell) await shell.screenshot({ path: file });
  else await page.screenshot({ path: file });
  console.log(`[saved] ${file}`);
}

await browser.close();
