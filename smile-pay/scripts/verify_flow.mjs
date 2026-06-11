// Verify stage-machine transitions in ?demo=1 (no camera needed).
// Logs data-stage + shell classes over time.
import { chromium } from "playwright";

const BASE = "http://127.0.0.1:8888";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 560, height: 560 } });

const log = [];
await page.goto(`${BASE}/?demo=1`, { waitUntil: "networkidle" });

const start = Date.now();
// Poll stage + shell classes long enough to see qr→idle loop
for (let i = 0; i < 96; i++) {
  const snap = await page.evaluate(() => {
    const stageEl = document.querySelector(".smile-stage");
    const shell = document.getElementById("shell");
    return {
      stage: stageEl?.dataset.stage ?? "?",
      camOpen: shell?.classList.contains("shell--cam-open") ?? false,
      masterVisible: shell?.classList.contains("shell--master-visible") ?? false,
    };
  });
  const t = ((Date.now() - start) / 1000).toFixed(1);
  const line = `${t}s stage=${snap.stage} cam=${snap.camOpen ? 1 : 0} master=${snap.masterVisible ? 1 : 0}`;
  if (log.length === 0 || log[log.length - 1].slice(5) !== line.slice(5)) {
    log.push(line);
    console.log(line);
  }
  await page.waitForTimeout(250);
}

await browser.close();
