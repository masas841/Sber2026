/**
 * Проверка флага «инсталляции выключены» на sberfest2026.ru (poll каждые 10 с).
 * При install_off=true показывается standby-экран (заменится ассетами из Figma).
 */

const DEFAULT_API_BASE = "https://sberfest2026.ru";
const DEFAULT_INTERVAL_MS = 10000;
const DEFAULT_TIMEOUT_MS = 1500;

function applyInstallOffUi(installOff, standbyEl, mainEl) {
  if (standbyEl) {
    standbyEl.classList.toggle("hidden", !installOff);
    standbyEl.hidden = !installOff;
  }
  if (mainEl) {
    mainEl.classList.toggle("hidden", installOff);
    if (installOff) {
      mainEl.setAttribute("aria-hidden", "true");
    } else {
      mainEl.removeAttribute("aria-hidden");
    }
  }
  document.body.classList.toggle("kiosk-install-off", installOff);
}

async function fetchInstallOff(activityId, apiBase, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const base = (apiBase || DEFAULT_API_BASE).replace(/\/$/, "");
  const url = `${base}/api/kiosk-install-mode/${encodeURIComponent(activityId)}`;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      credentials: "omit",
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`kiosk-install-mode ${response.status}`);
    }
    const data = await response.json();
    return Boolean(data.install_off);
  } finally {
    window.clearTimeout(timer);
  }
}

/**
 * @param {{
 *   activityId: string,
 *   apiBase?: string,
 *   intervalMs?: number,
 *   timeoutMs?: number,
 *   standbyEl?: HTMLElement | null,
 *   mainEl?: HTMLElement | null,
 *   onChange?: (installOff: boolean) => void,
 * }} options
 */
export async function initKioskInstallGate(options) {
  const {
    activityId,
    apiBase = DEFAULT_API_BASE,
    intervalMs = DEFAULT_INTERVAL_MS,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    standbyEl = document.getElementById("kiosk-install-standby"),
    mainEl = document.querySelector("[data-kiosk-main]") || document.querySelector("main") || document.body.firstElementChild,
    onChange,
  } = options;

  let installOff = false;
  let timer = null;

  const apply = (value) => {
    installOff = value;
    applyInstallOffUi(installOff, standbyEl, mainEl);
    if (onChange) onChange(installOff);
  };

  const poll = async () => {
    try {
      const value = await fetchInstallOff(activityId, apiBase, timeoutMs);
      apply(value);
    } catch {
      // Без сети киоск работает в обычном режиме.
    }
  };

  await poll();
  timer = window.setInterval(poll, intervalMs);

  return {
    get installOff() {
      return installOff;
    },
    refresh: poll,
    stop() {
      if (timer) window.clearInterval(timer);
      timer = null;
    },
  };
}
