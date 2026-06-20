const CONTROL_WIDTH = 1133;
const CONTROL_HEIGHT = 744;
const DEFAULT_GAME_DURATION = 59;
const RESULT_COUNTDOWN_SECONDS = 20;
const INITIAL_COUNTER_FLASH_GUARD_MS = 700;
const RATING_STAR_THRESHOLDS = [5, 8, 14];
const AIM_SEND_INTERVAL_MS = 33;
const AIM_HIT_DISTANCE_PX = 30;
const AIM_DRAG_DISTANCE_PX = 14;
const AIM_INITIAL_X = 352;
const AIM_INITIAL_Y = 413;

const control = document.querySelector("#control");
const connection = document.querySelector("#connection");
const screens = Array.from(document.querySelectorAll(".control-screen"));
const scoreEl = document.querySelector("#score");
const timerEl = document.querySelector("#timer");
const resultCountdownEl = document.querySelector("#resultCountdown");
const startButton = document.querySelector("#startButton");
const resetButton = document.querySelector("#resetButton");
const aimSurface = document.querySelector("#aimSurface");
const aimCursor = document.querySelector("#aimCursor");
const ratingStars = Array.from(document.querySelectorAll(".rating-stars__path"));

const state = {
  phase: "idle",
  score: 0,
  remaining: DEFAULT_GAME_DURATION,
  duration: DEFAULT_GAME_DURATION,
  resultCountdown: RESULT_COUNTDOWN_SECONDS,
  aim: {
    x: AIM_INITIAL_X,
    y: AIM_INITIAL_Y,
    nx: AIM_INITIAL_X / CONTROL_WIDTH,
    ny: AIM_INITIAL_Y / CONTROL_HEIGHT,
  },
};

let socket = null;
let lastPhase = "idle";
let lastInsureAt = 0;
let resultCountdownTimer = null;
let resultResetSent = false;
let activePointerId = null;
let lastAimSentAt = 0;
let lastTapPosition = null;
let pointerStartPosition = null;
let pointerHasDragged = false;
let hitPointerId = null;
let hitAnimationTimerId = 0;

function isNumber(value) {
  return Number.isFinite(Number(value));
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function formatScore(score) {
  return String(score ?? 0).padStart(3, "0");
}

function formatTimer(remaining) {
  return `${Math.ceil(remaining ?? 0)} с`;
}

function normalizePhase(phase) {
  if (phase === "playing" || phase === "result") {
    return phase;
  }
  return "idle";
}

function applyPayload(payload) {
  if (!payload) {
    return;
  }
  if ("phase" in payload) {
    state.phase = payload.phase;
  }
  if (isNumber(payload.score)) {
    state.score = Number(payload.score);
  }
  if (isNumber(payload.remaining)) {
    state.remaining = Number(payload.remaining);
  }
}

function syncScale() {
  const scale = Math.max(
    window.innerWidth / CONTROL_WIDTH,
    window.innerHeight / CONTROL_HEIGHT
  );
  control.style.setProperty("--control-scale", String(scale));
}

function renderAimCursor() {
  aimCursor.style.setProperty("--aim-x", `${state.aim.x}px`);
  aimCursor.style.setProperty("--aim-y", `${state.aim.y}px`);
}

function normalizeAimPosition(x, y) {
  const clampedX = clamp(x, 0, CONTROL_WIDTH);
  const clampedY = clamp(y, 0, CONTROL_HEIGHT);
  return {
    x: clampedX,
    y: clampedY,
    nx: clampedX / CONTROL_WIDTH,
    ny: clampedY / CONTROL_HEIGHT,
  };
}

function getAimPositionFromEvent(event) {
  const rect = aimSurface.getBoundingClientRect();
  const scaleX = CONTROL_WIDTH / rect.width;
  const scaleY = CONTROL_HEIGHT / rect.height;
  return normalizeAimPosition(
    (event.clientX - rect.left) * scaleX,
    (event.clientY - rect.top) * scaleY
  );
}

function distanceBetween(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function sendAim(position, force = false) {
  if (state.phase !== "playing") {
    return;
  }
  const now = performance.now();
  if (!force && now - lastAimSentAt < AIM_SEND_INTERVAL_MS) {
    return;
  }
  lastAimSentAt = now;
  send("aim", { x: position.nx, y: position.ny });
}

function setAimPosition(position, force = false) {
  state.aim = position;
  renderAimCursor();
  sendAim(position, force);
}

function pulseAimCursor() {
  window.clearTimeout(hitAnimationTimerId);
  aimCursor.classList.add("is-hit");
  hitAnimationTimerId = window.setTimeout(() => {
    aimCursor.classList.remove("is-hit");
  }, 160);
}

function sendHit(position) {
  lastInsureAt = performance.now();
  setAimPosition(position, true);
  pulseAimCursor();
  navigator.vibrate?.(25);
  send("insure", { x: position.nx, y: position.ny });
}

function renderResultCountdown() {
  resultCountdownEl.textContent = String(Math.max(0, state.resultCountdown));
}

function stopResultCountdown() {
  if (resultCountdownTimer) {
    window.clearInterval(resultCountdownTimer);
    resultCountdownTimer = null;
  }
}

function startResultCountdown() {
  stopResultCountdown();
  state.resultCountdown = RESULT_COUNTDOWN_SECONDS;
  resultResetSent = false;
  renderResultCountdown();
  resultCountdownTimer = window.setInterval(() => {
    state.resultCountdown -= 1;
    renderResultCountdown();
    if (state.resultCountdown <= 0) {
      stopResultCountdown();
      if (!resultResetSent) {
        resultResetSent = true;
        send("reset");
      }
    }
  }, 1000);
}

function syncResultCountdown(phase) {
  if (phase === "result" && lastPhase !== "result") {
    startResultCountdown();
  } else if (phase !== "result" && lastPhase === "result") {
    stopResultCountdown();
    state.resultCountdown = RESULT_COUNTDOWN_SECONDS;
    renderResultCountdown();
  } else {
    renderResultCountdown();
  }
}

function renderGameCounters(phase) {
  const nextScore = Number(state.score);
  const nextRemaining = Number(state.remaining);
  const showsProgress =
    scoreEl.textContent !== formatScore(0) ||
    timerEl.textContent !== formatTimer(state.duration);
  const looksLikeInitialState =
    nextScore === 0 && Math.ceil(nextRemaining) >= state.duration;
  const justPressedInsure =
    phase === "playing" &&
    performance.now() - lastInsureAt < INITIAL_COUNTER_FLASH_GUARD_MS;

  if (justPressedInsure && looksLikeInitialState && showsProgress) {
    return;
  }

  scoreEl.textContent = formatScore(nextScore);
  timerEl.textContent = formatTimer(nextRemaining);
  renderRatingStars(nextScore);
}

function getRatingStarCount(score) {
  return RATING_STAR_THRESHOLDS.filter((threshold) => score >= threshold).length;
}

function renderRatingStars(score) {
  const litCount = getRatingStarCount(Number(score) || 0);
  for (const star of ratingStars) {
    const index = Number(star.dataset.star);
    star.classList.toggle("is-lit", index < litCount);
  }
}

function updateUi() {
  const phase = normalizePhase(state.phase);

  control.dataset.phase = phase;
  screens.forEach((screen) => {
    const isActive = screen.dataset.screen === phase;
    screen.hidden = !isActive;
    screen.setAttribute("aria-hidden", String(!isActive));
  });
  renderGameCounters(phase);
  syncResultCountdown(phase);
  startButton.disabled = phase === "playing";
  aimSurface.setAttribute("aria-disabled", String(phase !== "playing"));
  if (phase === "playing" && lastPhase !== "playing") {
    sendAim(state.aim, true);
  }
  if (phase !== "playing" && lastPhase === "playing") {
    activePointerId = null;
    lastTapPosition = null;
    pointerStartPosition = null;
    pointerHasDragged = false;
    hitPointerId = null;
  }
  lastPhase = phase;
}

function setConnection(online) {
  connection.classList.toggle("is-online", online);
  connection.classList.toggle("is-offline", !online);
  connection.textContent = online ? "Подключено" : "Нет связи";
}

function connectControl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${protocol}//${window.location.host}/ws/control`);

  socket.addEventListener("open", () => {
    setConnection(true);
  });

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "hello") {
      if (isNumber(message.config?.gameDurationSec)) {
        state.duration = Number(message.config.gameDurationSec);
      }
      applyPayload(message.state);
      updateUi();
      return;
    }

    if (message.type === "state") {
      applyPayload(message.payload);
      updateUi();
      return;
    }

    if (message.type === "event") {
      applyPayload(message.payload);
      updateUi();
      if (message.payload?.kind === "hit") {
        navigator.vibrate?.(45);
      } else if (message.payload?.kind === "miss") {
        navigator.vibrate?.([25, 25, 25]);
      }
    }
  });

  socket.addEventListener("close", () => {
    setConnection(false);
    window.setTimeout(connectControl, 1000);
  });
}

function send(type, payload = null) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload ? { type, payload } : { type }));
  }
}

startButton.addEventListener("click", () => send("start"));
aimSurface.addEventListener("pointerdown", (event) => {
  if (state.phase !== "playing") {
    return;
  }
  event.preventDefault();
  activePointerId = event.pointerId;
  try {
    aimSurface.setPointerCapture?.(event.pointerId);
  } catch {
    // Synthetic pointer events in browser checks may not be capturable.
  }
  const position = getAimPositionFromEvent(event);
  pointerStartPosition = position;
  pointerHasDragged = false;
  const shouldHit =
    lastTapPosition && distanceBetween(lastTapPosition, position) <= AIM_HIT_DISTANCE_PX;

  if (shouldHit) {
    hitPointerId = event.pointerId;
    sendHit(position);
  } else {
    hitPointerId = null;
  }
});
aimSurface.addEventListener("pointermove", (event) => {
  if (state.phase !== "playing" || activePointerId !== event.pointerId) {
    return;
  }
  event.preventDefault();
  if (hitPointerId === event.pointerId) {
    return;
  }
  const position = getAimPositionFromEvent(event);
  if (!pointerHasDragged) {
    if (!pointerStartPosition || distanceBetween(pointerStartPosition, position) < AIM_DRAG_DISTANCE_PX) {
      return;
    }
    pointerHasDragged = true;
  }
  setAimPosition(position);
});
aimSurface.addEventListener("pointerup", (event) => {
  if (activePointerId !== event.pointerId) {
    return;
  }
  event.preventDefault();
  if (hitPointerId === event.pointerId) {
    hitPointerId = null;
    activePointerId = null;
    pointerStartPosition = null;
    pointerHasDragged = false;
    return;
  }
  lastTapPosition = pointerHasDragged ? state.aim : pointerStartPosition;
  activePointerId = null;
  pointerStartPosition = null;
  pointerHasDragged = false;
});
aimSurface.addEventListener("pointercancel", (event) => {
  if (activePointerId === event.pointerId) {
    activePointerId = null;
  }
  if (hitPointerId === event.pointerId) {
    hitPointerId = null;
  }
  pointerStartPosition = null;
  pointerHasDragged = false;
});
aimSurface.addEventListener("keydown", (event) => {
  if (state.phase !== "playing") {
    return;
  }
  if (event.key === "Enter" || event.code === "Space") {
    event.preventDefault();
    sendHit(state.aim);
  }
});
resetButton.addEventListener("click", () => {
  resultResetSent = true;
  send("reset");
});
window.addEventListener("resize", syncScale);

syncScale();
setConnection(false);
renderAimCursor();
updateUi();
connectControl();
