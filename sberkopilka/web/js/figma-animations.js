/**
 * Оркестрация анимаций статических экранов: iframe (CSS) + DOM-оверлей (конфетти).
 */
(function () {
  "use strict";

  const CONFETTI_COLORS = ["#ff64a2", "#01d701", "#122654", "#9effa8", "#ffd54f"];

  const DURATIONS = {
    "transition-out": 560,
    "transition-in": 660,
    "start-exit": 560,
    "onboarding-enter": 1000,
    "onboarding-slide-out": 600,
    "onboarding-slide-in": 800,
    dissolve: 620,
    "result-exit": 620,
    "leaderboard-enter": 660,
    reset: 0,
  };

  function getFrame(root) {
    return (
      root?.querySelector(".figma-overlay__frame--active") ||
      root?.querySelector(".figma-overlay__frame") ||
      null
    );
  }

  function postToFrame(frame, action) {
    if (!frame?.contentWindow) return Promise.resolve();
    const ms = DURATIONS[action] ?? 560;
    return new Promise((resolve) => {
      const t = window.setTimeout(resolve, ms);
      frame.contentWindow.postMessage({ type: "kopilka-anim", action }, "*");
      if (action === "reset") {
        window.clearTimeout(t);
        resolve();
      }
    });
  }

  function runOnFrame(frame, action) {
    return postToFrame(frame, action);
  }

  function runPair(outFrame, inFrame, outAction, inAction) {
    return Promise.all([
      runOnFrame(outFrame, outAction),
      runOnFrame(inFrame, inAction),
    ]);
  }

  function resolveScreenTransition(fromId, toId) {
    if ((!fromId || fromId === "start") && toId === "onboarding_1") {
      return { in: "onboarding-enter", dropOutgoing: fromId === "start" };
    }
    if (fromId?.startsWith("onboarding_") && toId?.startsWith("onboarding_")) {
      return {
        out: "onboarding-slide-out",
        in: "onboarding-slide-in",
        parallel: true,
      };
    }
    if (fromId?.startsWith("result_") && toId === "leaderboard") {
      return { out: "result-exit", in: "leaderboard-enter", parallel: false };
    }
    if (toId?.startsWith("result_")) {
      return { in: "result-enter" };
    }
    return {};
  }

  function spawnConfetti(root, count) {
    const n = count || 48;
    const layer = document.createElement("div");
    layer.className = "figma-confetti-layer";
    root.appendChild(layer);

    for (let i = 0; i < n; i++) {
      const p = document.createElement("span");
      p.className = "figma-confetti-piece";
      p.style.left = `${Math.random() * 100}%`;
      p.style.animationDelay = `${Math.random() * 0.8}s`;
      p.style.animationDuration = `${1.8 + Math.random() * 1.4}s`;
      p.style.background = CONFETTI_COLORS[i % CONFETTI_COLORS.length];
      p.style.transform = `rotate(${Math.random() * 360}deg)`;
      layer.appendChild(p);
    }

    window.setTimeout(() => layer.remove(), 4000);
  }

  async function transitionOut(root) {
    const frame = getFrame(root);
    if (!frame) return;
    await runOnFrame(frame, "transition-out");
  }

  async function transitionIn(root) {
    const frame = getFrame(root);
    if (!frame) return;
    await runOnFrame(frame, "transition-in");
    window.setTimeout(() => runOnFrame(frame, "reset"), DURATIONS["transition-in"]);
  }

  async function dissolve(root) {
    const frame = getFrame(root);
    if (!frame) return;
    await runOnFrame(frame, "dissolve");
  }

  function onRecord(screenId, root) {
    if (screenId === "result_record" && root) {
      spawnConfetti(root, 40);
    }
  }

  window.KopilkaFigmaAnim = {
    DURATIONS,
    resolveScreenTransition,
    runOnFrame,
    runPair,
    transitionOut,
    transitionIn,
    dissolve,
    onRecord,
    spawnConfetti,
  };
})();
