const connection = document.querySelector("#connection");
const phaseEl = document.querySelector("#phase");
const scoreEl = document.querySelector("#score");
const timerEl = document.querySelector("#timer");
const startButton = document.querySelector("#startButton");
const insureButton = document.querySelector("#insureButton");
const resetButton = document.querySelector("#resetButton");
const hint = document.querySelector("#hint");

const PHASE_LABELS = {
  idle: "заставка",
  playing: "игра",
  result: "финал",
};

let socket = null;
let state = {
  phase: "idle",
  score: 0,
  remaining: 59,
};

function formatScore(score) {
  return String(score ?? 0).padStart(3, "0");
}

function updateUi() {
  phaseEl.textContent = PHASE_LABELS[state.phase] ?? state.phase;
  scoreEl.textContent = formatScore(state.score);
  timerEl.textContent = `${Math.ceil(state.remaining ?? 0)} c`;
  startButton.disabled = state.phase === "playing";
  insureButton.disabled = state.phase !== "playing";

  if (state.phase === "idle") {
    hint.textContent = "На заставке нажмите «Старт».";
  } else if (state.phase === "playing") {
    hint.textContent = "Жмите «Страхуй», когда белое кольцо находится над угрозой.";
  } else {
    hint.textContent = "Раунд завершён. Можно сбросить заставку или начать заново.";
  }
}

function setConnection(online) {
  connection.classList.toggle("is-online", online);
  connection.classList.toggle("is-offline", !online);
  connection.textContent = online ? "подключено" : "нет связи";
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
      state = { ...state, ...message.state };
      updateUi();
      return;
    }

    if (message.type === "state") {
      state = { ...state, ...message.payload };
      updateUi();
      return;
    }

    if (message.type === "event") {
      state = { ...state, ...message.payload };
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

setConnection(false);
updateUi();
connectControl();
