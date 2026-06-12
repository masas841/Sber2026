const CONTROL_WIDTH = 1133;
const CONTROL_HEIGHT = 744;
const DEFAULT_GAME_DURATION = 59;
const RESULT_COUNTDOWN_SECONDS = 15;
const INITIAL_COUNTER_FLASH_GUARD_MS = 700;

const control = document.querySelector("#control");
const connection = document.querySelector("#connection");
const screens = Array.from(document.querySelectorAll(".control-screen"));
const scoreEl = document.querySelector("#score");
const timerEl = document.querySelector("#timer");
const resultCountdownEl = document.querySelector("#resultCountdown");
const startButton = document.querySelector("#startButton");
const insureButton = document.querySelector("#insureButton");
const resetButton = document.querySelector("#resetButton");

const state = {
  phase: "idle",
  score: 0,
  remaining: DEFAULT_GAME_DURATION,
  duration: DEFAULT_GAME_DURATION,
  resultCountdown: RESULT_COUNTDOWN_SECONDS,
};

let socket = null;
let lastPhase = "idle";
let lastInsureAt = 0;
let resultCountdownTimer = null;
let resultResetSent = false;

function isNumber(value) {
  return Number.isFinite(Number(value));
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
  insureButton.disabled = phase !== "playing";
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

function send(type) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type }));
  }
}

startButton.addEventListener("click", () => send("start"));
insureButton.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  lastInsureAt = performance.now();
  send("insure");
});
resetButton.addEventListener("click", () => {
  resultResetSent = true;
  send("reset");
});
window.addEventListener("resize", syncScale);

syncScale();
setConnection(false);
updateUi();
connectControl();
