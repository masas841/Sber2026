const STAGE = 672;
const DEFAULT_DURATION = 59;
const THREAT_ASSET = "/static/assets/figma/threats/";
const THREAT_ASSET_VERSION = "figma-export-3";
const THREAT_FALL_SPEED_MULTIPLIER = 3;
const HIT_FLASH_VISIBLE_MS = 1000;
const HIT_FLASH_WIDTH = 382;

const THREAT_LAYOUTS = [
  {
    id: "flood",
    figma: "Group 2136141821",
    className: "threat--flood",
    src: "raw/exported/flood.png",
    labels: [
      ["соседский", "pill--pink"],
      ["потоп", "pill--pink"],
    ],
    badgeText: "защита квартиры и дома",
    badgeKey: "badge-home",
    w: 225,
    h: 230,
    startX: 28,
    startY: -300,
    speed: 82,
    sway: 30,
    freq: 1.15,
    rotate: -8,
  },
  {
    id: "fluffy-acrobat",
    figma: "Group 2136141820",
    className: "threat--fluffy-acrobat",
    src: "raw/exported/fluffy-acrobat.svg",
    labels: [
      ["пушистый", "pill--blue"],
      ["акробат", "pill--blue"],
    ],
    badgeText: "защита животных",
    badgeKey: "badge-animals",
    w: 214,
    h: 225,
    startX: 404,
    startY: -650,
    speed: 88,
    sway: 40,
    freq: 1.18,
    rotate: -12,
  },
  {
    id: "toe-menace",
    figma: "Group 2136141822",
    className: "threat--toe-menace",
    src: "raw/exported/toe-menace.svg",
    labels: [
      ["гроза", "pill--pink"],
      ["всех", "pill--pink"],
      ["мизинцев", "pill--pink"],
    ],
    badgeText: "защита от травм",
    badgeKey: "badge-injury",
    w: 205,
    h: 244,
    startX: 232,
    startY: -1000,
    speed: 94,
    sway: 24,
    freq: 1.08,
    rotate: 8,
  },
  {
    id: "fraud",
    figma: "Group 2136141823",
    className: "threat--fraud",
    src: "raw/exported/fraud.svg",
    labels: [
      ["атака", "pill--green"],
      ["мошенника", "pill--green"],
    ],
    badgeText: "защита денег",
    badgeKey: "badge-money",
    w: 228,
    h: 228,
    startX: 430,
    startY: -1350,
    speed: 86,
    sway: 36,
    freq: 0.98,
    rotate: 10,
  },
  {
    id: "soap-phone",
    figma: "Group 2136141824",
    className: "threat--soap-phone",
    src: "raw/exported/soap-phone.png",
    labels: [
      ["телефон", "pill--pink"],
      ["как мыло", "pill--pink"],
    ],
    badgeText: "защита экрана",
    badgeKey: "badge-screen",
    w: 230,
    h: 190,
    startX: 76,
    startY: -1700,
    speed: 92,
    sway: 38,
    freq: 1.32,
    rotate: -16,
  },
  {
    id: "ghost-plane",
    figma: "Group 2136141827",
    className: "threat--ghost-plane",
    src: "raw/exported/ghost-plane.svg",
    labels: [
      ["призрак", "pill--blue"],
      ["самолёт", "pill--blue"],
    ],
    badgeText: "полис «страхование путешественников»",
    badgeKey: "badge-travel",
    w: 220,
    h: 220,
    startX: 334,
    startY: -2050,
    speed: 80,
    sway: 44,
    freq: 1.24,
    rotate: -6,
  },
  {
    id: "brick-gadget",
    figma: "Group 2136141826",
    className: "threat--brick-gadget",
    src: "raw/exported/brick-gadget.svg",
    labels: [
      ["окирпичивание", "pill--pink"],
      ["гаджета", "pill--pink"],
    ],
    badgeText: "защита экрана",
    badgeKey: "badge-screen-alt",
    w: 206,
    h: 213,
    startX: 136,
    startY: -2400,
    speed: 100,
    sway: 30,
    freq: 1.05,
    rotate: 8,
  },
  {
    id: "dog-vacuum",
    figma: "Group 2136141828",
    className: "threat--dog-vacuum",
    src: "raw/exported/dog-vacuum.png",
    labels: [
      ["собака", "pill--blue"],
      ["пылесос", "pill--blue"],
    ],
    badgeText: "полис «питомец под защитой»",
    badgeKey: "badge-pet-policy",
    w: 215,
    h: 228,
    startX: 428,
    startY: -2750,
    speed: 90,
    sway: 42,
    freq: 0.9,
    rotate: -10,
  },
  {
    id: "micro-hater",
    figma: "Group 2136141825",
    className: "threat--micro-hater",
    src: "raw/exported/micro-hater.png",
    labels: [["микро-хейтер", "pill--pink"]],
    badgeText: "защита от клеща",
    badgeKey: "badge-tick",
    w: 190,
    h: 251,
    startX: 30,
    startY: -3100,
    speed: 96,
    sway: 28,
    freq: 1.18,
    rotate: 4,
  },
  {
    id: "slam-salto",
    figma: "Group 2136141829",
    className: "threat--slam-salto",
    src: "raw/exported/slam-salto.png",
    labels: [
      ["слэмовое", "pill--green"],
      ["сальто", "pill--green"],
    ],
    badgeText: "защита от травм",
    badgeKey: "badge-injury-alt",
    w: 235,
    h: 204,
    startX: 240,
    startY: -3450,
    speed: 108,
    sway: 34,
    freq: 1.0,
    rotate: -8,
  },
  {
    id: "lost-sneaker",
    figma: "Group 2136141830",
    className: "threat--lost-sneaker",
    src: "raw/exported/lost-sneaker.svg",
    labels: [
      ["кроссовок", "pill--blue"],
      ["потеряшка", "pill--blue"],
    ],
    badgeText: "защита багажа",
    badgeKey: "badge-baggage",
    w: 248,
    h: 188,
    startX: 398,
    startY: -3800,
    speed: 84,
    sway: 46,
    freq: 1.28,
    rotate: 11,
  },
  {
    id: "bumper-kiss",
    figma: "Group 2136141831",
    className: "threat--bumper-kiss",
    src: "raw/exported/bumper-kiss.png",
    labels: [
      ["бамперный", "pill--green"],
      ["поцелуй", "pill--green"],
    ],
    badgeText: "полис ОСАГО",
    badgeKey: "badge-osago",
    w: 250,
    h: 167,
    startX: 78,
    startY: -4150,
    speed: 102,
    sway: 30,
    freq: 1.08,
    rotate: -5,
  },
  {
    id: "pigeon-picasso",
    figma: "Group 2136141833",
    className: "threat--pigeon-picasso",
    src: "raw/exported/pigeon-picasso.png",
    labels: [
      ["голубь-", "pill--blue"],
      ["пикассо", "pill--blue"],
    ],
    badgeText: "полис КАСКО",
    badgeKey: "badge-kasko",
    w: 190,
    h: 250,
    startX: 286,
    startY: -4500,
    speed: 98,
    sway: 38,
    freq: 1.16,
    rotate: 7,
  },
];

const BADGE_ASSET_URLS = new Map(
  [...new Set(THREAT_LAYOUTS.map((layout) => layout.badgeKey ?? "badge-home"))].map((badgeKey) => [
    badgeKey,
    `${THREAT_ASSET}raw/exported/${badgeKey}.svg?v=${THREAT_ASSET_VERSION}`,
  ])
);
const preloadedBadgeImages = new Map(
  [...BADGE_ASSET_URLS].map(([badgeKey, src]) => {
    const image = new Image();
    image.src = src;
    return [badgeKey, image];
  })
);

const RESULT_INTRO_HOLD_MS = 6000;
const RESULT_TRANSITION_MS = 480;
const RESULT_FINAL_HOLD_MS = 15000;
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
    text: "Ты поймал все угрозы и стал настоящим супергероем фестиваля — Сбер одобряет! А\u00A0на случай неожиданностей есть СберСтрахование.",
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
const hitFlashBadge = document.querySelector("#hitFlashBadge");
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

let hitFlashToken = 0;
let hitFlashTimerId = 0;

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
  image.src = `${THREAT_ASSET}${layout.src}?v=${THREAT_ASSET_VERSION}`;
  image.alt = "";
  element.append(image);

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
  timerValue.textContent = `${Math.ceil(game.remaining)} с`;
}

function updateThreat(threat, now, dt) {
  if (!threat.active) {
    if (now >= threat.respawnAt) {
      threat.active = true;
      threat.killed = false;
      threat.el.classList.remove("is-killed");
      threat.y = -threat.h - 700 - Math.random() * 1400;
      threat.x = threat.startX + (Math.random() - 0.5) * 120;
      threat.seed = Math.random() * Math.PI * 2;
    }
    threat.el.style.opacity = "0";
    return;
  }

  threat.y += threat.speed * THREAT_FALL_SPEED_MULTIPLIER * dt;
  const sway = Math.sin(now / 1000 * threat.freq + threat.seed) * threat.sway;
  const rotate = threat.rotate + Math.sin(now / 900 + threat.seed) * 8;
  const x = Math.max(-40, Math.min(STAGE - threat.w + 40, threat.x + sway));
  threat.el.style.opacity = "1";
  threat.el.style.transform = `translate(${x}px, ${threat.y}px) rotate(${rotate}deg)`;
  threat.currentX = x;

  if (threat.y > STAGE + 80) {
    threat.y = -threat.h - 700 - Math.random() * 1800;
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
  const hit = threat.hit ?? {
    x: threat.w * 0.22,
    y: threat.h * 0.22,
    w: threat.w * 0.56,
    h: threat.h * 0.56,
  };
  return {
    x: (threat.currentX ?? threat.x) + hit.x,
    y: threat.y + hit.y,
    w: hit.w,
    h: hit.h,
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
  const hitX = box.x + box.w / 2;
  const hitY = box.y + box.h / 2;
  const hitFlashWidth = hitFlash.offsetWidth || HIT_FLASH_WIDTH;
  const hitFlashHalfWidth = hitFlashWidth / 2;
  const showOnRight = hitX < STAGE / 2;
  const targetX = showOnRight ? hitX + hitFlashHalfWidth : hitX - hitFlashHalfWidth;
  const badgeKey = threat.badgeKey ?? "badge-home";
  const badgeSrc = BADGE_ASSET_URLS.get(badgeKey) ?? BADGE_ASSET_URLS.get("badge-home");
  const badgeImage = preloadedBadgeImages.get(badgeKey) ?? preloadedBadgeImages.get("badge-home");
  const token = ++hitFlashToken;

  window.clearTimeout(hitFlashTimerId);
  hitFlash.classList.add("is-resetting");
  hitFlash.classList.remove("is-visible");
  void hitFlash.offsetWidth;
  hitFlash.setAttribute("aria-label", threat.badgeText);
  hitFlash.dataset.badge = badgeKey;
  hitFlash.dataset.side = showOnRight ? "right" : "left";
  hitFlash.style.left = `${targetX}px`;
  hitFlash.style.top = `${hitY}px`;

  const reveal = () => {
    if (token !== hitFlashToken) {
      return;
    }
    hitFlashBadge.src = badgeSrc;
    requestAnimationFrame(() => {
      if (token !== hitFlashToken) {
        return;
      }
      hitFlash.classList.remove("is-resetting");
      hitFlash.classList.add("is-visible");
      hitFlashTimerId = window.setTimeout(() => {
        if (token === hitFlashToken) {
          hitFlash.classList.remove("is-visible");
        }
      }, HIT_FLASH_VISIBLE_MS);
    });
  };

  if (!badgeImage || (badgeImage.complete && badgeImage.naturalWidth > 0)) {
    reveal();
    return;
  }

  if (typeof badgeImage.decode === "function") {
    badgeImage.decode().then(reveal).catch(reveal);
    return;
  }

  badgeImage.addEventListener("load", reveal, { once: true });
  badgeImage.addEventListener("error", reveal, { once: true });
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



