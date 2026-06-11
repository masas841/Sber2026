const CONTROL_WIDTH = 1133;
const CONTROL_HEIGHT = 744;

const control = document.querySelector("#control");
const connection = document.querySelector("#connection");
const screens = Array.from(document.querySelectorAll(".control-screen"));
const scoreEl = document.querySelector("#score");
const timerEl = document.querySelector("#timer");
const startButton = document.querySelector("#startButton");
const insureButton = document.querySelector("#insureButton");
const resetButton = document.querySelector("#resetButton");

const state = {
  phase: "idle",
  score: 0,
  remaining: 59,
};

let socket = null;

function formatScore(score) {
  return String(score ?? 0).padStart(3, "0");
}

function formatTimer(remaining) {
  return `${Math.ceil(remaining ?? 0)} c`;
}

function normalizePhase(phase) {
  if (phase === "playing" || phase === "result") {
    return phase;
  }
  return "idle";
}

function syncScale() {
  const scale = Math.max(
    window.innerWidth / CONTROL_WIDTH,
    window.innerHeight / CONTROL_HEIGHT
  );
  control.style.setProperty("--control-scale", String(scale));
}

function updateUi() {
  const phase = normalizePhase(state.phase);

  control.dataset.phase = phase;
  screens.forEach((screen) => {
    const isActive = screen.dataset.screen === phase;
    screen.hidden = !isActive;
    screen.setAttribute("aria-hidden", String(!isActive));
  });
  scoreEl.textContent = formatScore(state.score);
  timerEl.textContent = formatTimer(state.remaining);
  startButton.disabled = phase === "playing";
  insureButton.disabled = phase !== "playing";
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
      Object.assign(state, message.state);
      updateUi();
      return;
    }

    if (message.type === "state") {
      Object.assign(state, message.payload);
      updateUi();
      return;
    }

    if (message.type === "event") {
      Object.assign(state, message.payload);
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
  send("insure");
});
resetButton.addEventListener("click", () => send("reset"));
window.addEventListener("resize", syncScale);

syncScale();
setConnection(false);
updateUi();
connectControl();
