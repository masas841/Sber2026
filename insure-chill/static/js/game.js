const STAGE = 672;
const DEFAULT_DURATION = 59;
const ASSET = "/static/assets/figma/";

const THREAT_LAYOUTS = [
  {
    id: "nail-phone",
    figma: "Group 2136141720",
    className: "threat--nail",
    src: "threat-nail-phone.png",
    labels: [
      ["забивают", "pill--pink"],
      ["телефон", "pill--pink"],
      ["гвоздь", "pill--pink"],
    ],
    w: 255,
    h: 282,
    startX: 28,
    startY: -350,
    speed: 92,
    sway: 26,
    freq: 1.15,
    rotate: 25,
    hit: { x: 45, y: 38, w: 168, h: 210 },
  },
  {
    id: "water-drop",
    figma: "Group 2136141721",
    className: "threat--drop",
    src: "threat-water-drop.png",
    labels: [
      ["капли", "pill--pink"],
      ["воды", "pill--pink"],
    ],
    w: 260,
    h: 255,
    startX: 350,
    startY: -540,
    speed: 78,
    sway: 34,
    freq: 0.95,
    rotate: 22,
    hit: { x: 48, y: 40, w: 160, h: 174 },
  },
  {
    id: "cat-paw",
    figma: "Group 2136141724",
    className: "threat--paw",
    src: "threat-cat-paw.png",
    labels: [
      ["кошачья лапа", "pill--blue"],
      ["толкает", "pill--blue"],
      ["телефон", "pill--blue"],
    ],
    w: 215,
    h: 215,
    startX: 405,
    startY: -770,
    speed: 84,
    sway: 42,
    freq: 1.25,
    rotate: -20,
    hit: { x: 38, y: 50, w: 138, h: 132 },
  },
  {
    id: "fist",
    figma: "Group 2136141737",
    className: "threat--fist",
    src: "threat-fist.png",
    labels: [
      ["прилетает", "pill--green pill--vertical"],
      ["кулак", "pill--green"],
    ],
    w: 235,
    h: 235,
    startX: 428,
    startY: -980,
    speed: 104,
    sway: 28,
    freq: 1.05,
    rotate: -35,
    hit: { x: 55, y: 48, w: 135, h: 142 },
  },
  {
    id: "soap-phone",
    figma: "Group 2136141745",
    className: "threat--soap",
    src: "threat-soap-phone.png",
    labels: [
      ["телефон как мыло", "pill--pink"],
      ["выскользнул", "pill--pink"],
    ],
    w: 245,
    h: 205,
    startX: 80,
    startY: -1210,
    speed: 88,
    sway: 38,
    freq: 1.35,
    rotate: -26,
    hit: { x: 28, y: 34, w: 178, h: 120 },
  },
];

const RESULT_INTRO_HOLD_MS = 3000;
const RESULT_FINAL_HOLD_MS = 20000;
const RESULT_TRANSITION_MS = 480;
const STAR_LIGHT_DELAY_MS = 420;
const STAR_LIGHT_START_MS = 720;

const RESULT_VARIANTS = [
  {
    id: "low",
    minScore: 0,
    maxScore: 4,
    starCount: 0,
    title: "похоже, что-то застало тебя врасплох!",
    text: "Но хорошо, что есть СберСтрахование.",
  },
  {
    id: "medium",
    minScore: 5,
    maxScore: 7,
    starCount: 1,
    title: "неплохой результат!",
    text: "Ты смог защититься от многих неприятностей, для всего остального есть СберСтрахование.",
  },
  {
    id: "good",
    minScore: 8,
    maxScore: 13,
    starCount: 2,
    title: "отличная реакция!",
    text: "Большинство рисков тебе уже не страшны, с остальными справится СберСтрахование.",
  },
  {
    id: "max",
    minScore: 14,
    maxScore: Infinity,
    starCount: 3,
    title: "максимальная защита!",
    text: "Ты поймал все угрозы и стал настоящим супергероем фестиваля — Сбер одобряет! А на случай неожиданностей есть СберСтрахование.",
  },
];

const stage = document.querySelector("#stage");
const idleLayer = document.querySelector("#idleLayer");
const gameLayer = document.querySelector("#gameLayer");
const resultLayer = document.querySelector("#resultLayer");
const threatLayer = document.querySelector("#threatLayer");
const debugLayer = document.querySelector("#debugLayer");
const protectorEl = document.querySelector("#protector");
const scoreValue = document.querySelector("#scoreValue");
const timerValue = document.querySelector("#timerValue");
const hitFlash = document.querySelector("#hitFlash");
const resultIntro = document.querySelector("#resultIntro");
const resultFinal = document.querySelector("#resultFinal");
const resultIntroScore = document.querySelector("#resultIntroScore");
const resultFinalScore = document.querySelector("#resultFinalScore");
const resultTitle = document.querySelector("#resultTitle");
const resultText = document.querySelector("#resultText");
const resultRating = document.querySelector("#resultRating");

const query = new URLSearchParams(window.location.search);
const isDebug = query.get("debug") === "1";
if (isDebug) {
  stage.classList.add("is-debug");
}

const game = {
  phase: "idle",
  duration: DEFAULT_DURATION,
  hitPadding: 10,
  score: 0,
  remaining: DEFAULT_DURATION,
  startedAt: 0,
  lastFrameAt: 0,
  lastStateSentAt: 0,
  ws: null,
  resultTimers: [],
  resultVariant: null,
  threats: [],
  protector: {
    x: 303,
    y: 302,
    w: 65,
    h: 65,
    targetX: 303,
    targetY: 302,
    nextTargetAt: 0,
  },
};

function formatScore(score) {
  return String(score).padStart(3, "0");
}

function createThreat(layout) {
  const element = document.createElement("div");
  element.className = `threat ${layout.className}`;
  element.style.setProperty("--w", `${layout.w}px`);
  element.style.setProperty("--h", `${layout.h}px`);
  element.dataset.threat = layout.id;
  element.dataset.figma = layout.figma;

  const image = document.createElement("img");
  image.src = `${ASSET}${layout.src}`;
  image.alt = "";
  element.append(image);

  for (const [text, classes] of layout.labels) {
    const pill = document.createElement("span");
    pill.className = `pill ${classes}`;
    pill.textContent = text;
    element.append(pill);
  }

  threatLayer.append(element);
  return {
    ...layout,
    el: element,
    x: layout.startX,
    y: layout.startY,
    active: true,
    killed: false,
    respawnAt: 0,
    seed: Math.random() * Math.PI * 2,
  };
}

function setupThreats() {
  threatLayer.innerHTML = "";
  game.threats = THREAT_LAYOUTS.map(createThreat);
}

function connectScreen() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws/screen`);
  game.ws = ws;

  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "hello") {
      game.duration = message.config?.gameDurationSec ?? DEFAULT_DURATION;
      game.hitPadding = message.config?.hitPaddingPx ?? 10;
      setIdle();
      return;
    }
    if (message.type !== "command") {
      return;
    }

    const command = message.payload?.command;
    if (command === "start") {
      startGame();
    } else if (command === "insure") {
      attemptInsure();
    } else if (command === "reset") {
      setIdle();
    }
  });

  ws.addEventListener("close", () => {
    setTimeout(connectScreen, 1000);
  });
}

function send(type, payload) {
  if (game.ws?.readyState === WebSocket.OPEN) {
    game.ws.send(JSON.stringify({ type, payload }));
  }
}

function setLayer(activeLayer) {
  for (const layer of [idleLayer, gameLayer, resultLayer]) {
    layer.classList.toggle("scene-layer--active", layer === activeLayer);
  }
}

function getResultVariant(score) {
  return (
    RESULT_VARIANTS.find((variant) => score >= variant.minScore && score <= variant.maxScore) ??
    RESULT_VARIANTS[RESULT_VARIANTS.length - 1]
  );
}

function clearResultFlow() {
  for (const timerId of game.resultTimers) {
    window.clearTimeout(timerId);
  }
  game.resultTimers = [];
  game.resultVariant = null;

  resultIntro.classList.remove("is-leaving", "is-animating", "is-hidden");
  resultFinal.classList.remove("is-active", "is-animating");
  resultFinal.hidden = true;
  resultText.hidden = false;
  resultLayer.dataset.variant = "";

  for (const star of resultRating.querySelectorAll(".result-rating__star")) {
    star.classList.remove("is-lit");
  }
}

function scheduleResultStep(callback, delayMs) {
  const timerId = window.setTimeout(callback, delayMs);
  game.resultTimers.push(timerId);
  return timerId;
}

function playResultAnimation(container) {
  container.classList.remove("is-animating");
  void container.offsetWidth;
  container.classList.add("is-animating");
}

function animateRatingStars(starCount) {
  const stars = resultRating.querySelectorAll(".result-rating__star");
  for (const star of stars) {
    star.classList.remove("is-lit");
  }

  for (let index = 0; index < starCount; index += 1) {
    scheduleResultStep(() => {
      stars[index]?.classList.add("is-lit");
    }, STAR_LIGHT_START_MS + index * STAR_LIGHT_DELAY_MS);
  }
}

function renderResultIntro() {
  resultIntroScore.textContent = formatScore(game.score);
}

function renderResultFinal() {
  const variant = getResultVariant(game.score);
  game.resultVariant = variant.id;
  resultLayer.dataset.variant = variant.id;
  resultFinalScore.textContent = formatScore(game.score);
  resultTitle.textContent = variant.title;
  resultText.textContent = variant.text;
  resultText.hidden = false;
}

function returnToIdleFromResult() {
  if (game.phase !== "result") {
    return;
  }
  setIdle();
}

function showResultFinal() {
  const variant = getResultVariant(game.score);
  resultIntro.classList.add("is-leaving");
  scheduleResultStep(() => {
    resultIntro.classList.remove("is-leaving", "is-animating");
    resultIntro.classList.add("is-hidden");
    resultFinal.hidden = false;
    resultFinal.classList.add("is-active");
    renderResultFinal();
    playResultAnimation(resultFinal);
    animateRatingStars(variant.starCount);
    scheduleResultStep(returnToIdleFromResult, RESULT_FINAL_HOLD_MS);
    send("event", {
      kind: "result-final",
      phase: "result",
      variant: variant.id,
      score: game.score,
      remaining: 0,
    });
  }, RESULT_TRANSITION_MS);
}

function setIdle() {
  clearResultFlow();
  game.phase = "idle";
  game.score = 0;
  game.remaining = game.duration;
  updateHud();
  setLayer(idleLayer);
  stage.dataset.phase = "idle";
  send("state", {
    phase: "idle",
    score: game.score,
    remaining: game.remaining,
  });
}

function startGame() {
  game.phase = "playing";
  game.score = 0;
  game.remaining = game.duration;
  game.startedAt = performance.now();
  game.lastFrameAt = game.startedAt;
  game.lastStateSentAt = 0;
  game.protector.x = 303;
  game.protector.y = 302;
  game.protector.targetX = 303;
  game.protector.targetY = 302;
  game.protector.nextTargetAt = 0;
  setupThreats();
  updateHud();
  setLayer(gameLayer);
  stage.dataset.phase = "playing";
  send("event", {
    kind: "start",
    phase: "playing",
    score: 0,
    remaining: game.remaining,
  });
}

function finishGame() {
  if (game.phase !== "playing") {
    return;
  }
  game.phase = "result";
  game.remaining = 0;
  updateHud();
  clearResultFlow();
  renderResultIntro();
  setLayer(resultLayer);
  stage.dataset.phase = "result";
  playResultAnimation(resultIntro);
  scheduleResultStep(showResultFinal, RESULT_INTRO_HOLD_MS);
  send("event", {
    kind: "result-intro",
    phase: "result",
    score: game.score,
    remaining: 0,
  });
}

function renderResult() {
  renderResultIntro();
  renderResultFinal();
}

function updateHud() {
  scoreValue.textContent = formatScore(game.score);
  timerValue.textContent = `${Math.ceil(game.remaining)} c`;
}

function updateThreat(threat, now, dt) {
  if (!threat.active) {
    if (now >= threat.respawnAt) {
      threat.active = true;
      threat.killed = false;
      threat.el.classList.remove("is-killed");
      threat.y = -threat.h - Math.random() * 260;
      threat.x = threat.startX + (Math.random() - 0.5) * 120;
      threat.seed = Math.random() * Math.PI * 2;
    }
    threat.el.style.opacity = "0";
    return;
  }

  threat.y += threat.speed * dt;
  const sway = Math.sin(now / 1000 * threat.freq + threat.seed) * threat.sway;
  const rotate = threat.rotate + Math.sin(now / 900 + threat.seed) * 8;
  const x = Math.max(-40, Math.min(STAGE - threat.w + 40, threat.x + sway));
  threat.el.style.opacity = "1";
  threat.el.style.transform = `translate(${x}px, ${threat.y}px) rotate(${rotate}deg)`;
  threat.currentX = x;

  if (threat.y > STAGE + 80) {
    threat.y = -threat.h - Math.random() * 320;
    threat.x = threat.startX + (Math.random() - 0.5) * 160;
  }
}

function chooseProtectorTarget(now) {
  if (now < game.protector.nextTargetAt) {
    return;
  }
  const margin = 54;
  game.protector.targetX = margin + Math.random() * (STAGE - margin * 2 - game.protector.w);
  game.protector.targetY = 100 + Math.random() * (STAGE - 190);
  game.protector.nextTargetAt = now + 900 + Math.random() * 850;
}

function updateProtector(now, dt) {
  chooseProtectorTarget(now);
  const p = game.protector;
  const stiffness = Math.min(1, dt * 2.8);
  const jitterX = Math.sin(now / 330) * 0.45;
  const jitterY = Math.cos(now / 410) * 0.45;
  p.x += (p.targetX - p.x) * stiffness + jitterX;
  p.y += (p.targetY - p.y) * stiffness + jitterY;
  p.x = Math.max(0, Math.min(STAGE - p.w, p.x));
  p.y = Math.max(0, Math.min(STAGE - p.h, p.y));
  protectorEl.style.transform = `translate(${p.x}px, ${p.y}px)`;
}

function hitBoxForThreat(threat) {
  return {
    x: (threat.currentX ?? threat.x) + threat.hit.x,
    y: threat.y + threat.hit.y,
    w: threat.hit.w,
    h: threat.hit.h,
  };
}

function hitBoxForProtector() {
  const pad = game.hitPadding;
  return {
    x: game.protector.x - pad,
    y: game.protector.y - pad,
    w: game.protector.w + pad * 2,
    h: game.protector.h + pad * 2,
  };
}

function intersectionArea(a, b) {
  const x = Math.max(a.x, b.x);
  const y = Math.max(a.y, b.y);
  const r = Math.min(a.x + a.w, b.x + b.w);
  const bottom = Math.min(a.y + a.h, b.y + b.h);
  return Math.max(0, r - x) * Math.max(0, bottom - y);
}

function attemptInsure() {
  if (game.phase !== "playing") {
    return;
  }

  const protectorBox = hitBoxForProtector();
  let bestThreat = null;
  let bestArea = 0;
  for (const threat of game.threats) {
    if (!threat.active) {
      continue;
    }
    const area = intersectionArea(protectorBox, hitBoxForThreat(threat));
    if (area > bestArea) {
      bestArea = area;
      bestThreat = threat;
    }
  }

  if (!bestThreat) {
    send("event", {
      kind: "miss",
      phase: "playing",
      score: game.score,
      remaining: Math.ceil(game.remaining),
    });
    pulseProtector();
    return;
  }

  bestThreat.active = false;
  bestThreat.killed = true;
  bestThreat.respawnAt = performance.now() + 1300;
  bestThreat.el.classList.add("is-killed");
  game.score += 1;
  updateHud();
  showHitFlash(bestThreat);
  send("event", {
    kind: "hit",
    threat: bestThreat.id,
    phase: "playing",
    score: game.score,
    remaining: Math.ceil(game.remaining),
  });
}

function pulseProtector() {
  protectorEl.animate(
    [
      { filter: "drop-shadow(0 0 0 rgba(255, 100, 162, 0))" },
      { filter: "drop-shadow(0 0 18px rgba(255, 100, 162, 0.95))" },
      { filter: "drop-shadow(0 8px 12px rgba(18, 38, 84, 0.22))" },
    ],
    { duration: 220, easing: "ease-out" }
  );
}

function showHitFlash(threat) {
  const box = hitBoxForThreat(threat);
  hitFlash.style.left = `${box.x + box.w / 2}px`;
  hitFlash.style.top = `${box.y + box.h / 2}px`;
  hitFlash.classList.add("is-visible");
  window.setTimeout(() => hitFlash.classList.remove("is-visible"), 520);
}

function renderDebug() {
  if (!isDebug || game.phase !== "playing") {
    debugLayer.innerHTML = "";
    return;
  }

  const boxes = [];
  const protectorBox = hitBoxForProtector();
  boxes.push({ ...protectorBox, protector: true });
  for (const threat of game.threats) {
    if (threat.active) {
      boxes.push(hitBoxForThreat(threat));
    }
  }
  debugLayer.innerHTML = boxes
    .map((box) => {
      const cls = box.protector ? "debug-box debug-box--protector" : "debug-box";
      return `<div class="${cls}" style="left:${box.x}px;top:${box.y}px;width:${box.w}px;height:${box.h}px"></div>`;
    })
    .join("");
}

function tick(now) {
  const dt = Math.min(0.05, Math.max(0, (now - game.lastFrameAt) / 1000 || 0));
  game.lastFrameAt = now;

  if (game.phase === "playing") {
    game.remaining = Math.max(0, game.duration - (now - game.startedAt) / 1000);
    if (game.remaining <= 0) {
      finishGame();
    } else {
      for (const threat of game.threats) {
        updateThreat(threat, now, dt);
      }
      updateProtector(now, dt);
      updateHud();
      renderDebug();
      if (now - game.lastStateSentAt > 250) {
        game.lastStateSentAt = now;
        send("state", {
          phase: "playing",
          score: game.score,
          remaining: Math.ceil(game.remaining),
        });
      }
    }
  }

  requestAnimationFrame(tick);
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    startGame();
  } else if (event.code === "Space") {
    attemptInsure();
  } else if (event.key.toLowerCase() === "r") {
    setIdle();
  }
});

setupThreats();
setIdle();
connectScreen();
requestAnimationFrame(tick);
