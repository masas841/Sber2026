/**
 * Скрипт внутри figma-screens/*.html — классы переходов по postMessage от родителя.
 */
(function () {
  "use strict";

  const root = document.getElementById("root");
  if (!root) return;

  const TRANSITION_CLASSES = [
    "kop-transition-in",
    "kop-transition-out",
    "kop-dissolve",
    "kop-result-enter",
    "kop-start-exit",
    "kop-onboarding-enter",
    "kop-onboarding-slide-out",
    "kop-onboarding-slide-in",
    "kop-result-exit",
    "kop-leaderboard-enter",
  ];

  const ACTION_CLASSES = {
    "transition-out": ["kop-transition-out"],
    "transition-in": ["kop-transition-in", "kop-result-enter"],
    dissolve: ["kop-dissolve"],
    "start-exit": ["kop-start-exit"],
    "onboarding-enter": ["kop-onboarding-enter"],
    "onboarding-slide-out": ["kop-onboarding-slide-out"],
    "onboarding-slide-in": ["kop-onboarding-slide-in"],
    "result-exit": ["kop-result-exit"],
    "leaderboard-enter": ["kop-leaderboard-enter"],
  };

  window.addEventListener("message", (ev) => {
    const data = ev.data;
    if (!data || data.type !== "kopilka-anim") return;

    document.body.classList.remove(...TRANSITION_CLASSES);

    const classes = ACTION_CLASSES[data.action];
    if (classes?.length) {
      document.body.classList.add(...classes);
      void document.body.offsetHeight;
    }
  });

  function notifyReady() {
    window.parent.postMessage({ type: "kopilka-screen-ready" }, "*");
  }

  function whenRootPainted(cb) {
    if (root.childElementCount > 0) {
      requestAnimationFrame(() => requestAnimationFrame(cb));
      return;
    }
    const obs = new MutationObserver(() => {
      if (root.childElementCount > 0) {
        obs.disconnect();
        requestAnimationFrame(() => requestAnimationFrame(cb));
      }
    });
    obs.observe(root, { childList: true, subtree: true });
    window.setTimeout(() => {
      obs.disconnect();
      cb();
    }, 5000);
  }

  whenRootPainted(notifyReady);
})();
