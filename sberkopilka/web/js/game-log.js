/**
 * Анонимный учёт сессий киоска: визит, старт/финиш игры.
 * session_id живёт в sessionStorage (одна вкладка = одна сессия).
 */
(function () {
  const SESSION_KEY = "kop_session_id";

  function sessionId() {
    try {
      let id = sessionStorage.getItem(SESSION_KEY);
      if (!id) {
        id =
          typeof crypto !== "undefined" && crypto.randomUUID
            ? crypto.randomUUID()
            : `s${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
        sessionStorage.setItem(SESSION_KEY, id);
      }
      return id;
    } catch {
      return `s${Date.now()}`;
    }
  }

  function log(event, extra) {
    const payload = {
      session_id: sessionId(),
      event,
      ...(extra || {}),
    };
    try {
      fetch("/api/log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(function () {});
    } catch {
      /* offline kiosk */
    }
  }

  window.KopilkaLog = { log, sessionId };
})();
