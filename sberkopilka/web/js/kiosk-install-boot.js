import { initKioskInstallGate } from "./kiosk-install-mode.js";

window.__kopilkaInstallGate = initKioskInstallGate({
  activityId: "sberkopilka",
  standbyEl: document.getElementById("kiosk-install-standby"),
  mainEl: document.getElementById("game-root"),
});
