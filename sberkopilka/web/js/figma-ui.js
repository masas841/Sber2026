/**
 * Статические экраны: живой JSX из Figma (iframe 672×672) + CSS-анимации + динамика.
 * PNG — только fallback офлайн; анимации работают в iframe.
 */
(function () {
  "use strict";

  const D = () => window.KopilkaDesign;
  const OVERLAY_ID = "figma-overlay";
  const DESIGN = 672;
  const SCREENS_BASE = "/static/assets/figma/screens/";
  const HTML_BASE = "/static/figma-screens/";

  const DYNAMIC = {
    result_score: {
      label: { x: 333, y: 141, size: 21.4, color: "#01d701", bold: true, text: "счёт:" },
      score: { x: 333, y: 162, size: 49.3, color: "#122654", bold: true },
    },
    result_top: {
      label: { x: 333, y: 141, size: 21.4, color: "#ffffff", bold: true, text: "счёт:", onCloud: true },
      score: { x: 333, y: 162, size: 49.3, color: "#ffffff", bold: true, onCloud: true },
    },
    result_record: {
      label: { x: 333, y: 141, size: 21.4, color: "#01d701", bold: true, text: "рекорд" },
      score: { x: 333, y: 162, size: 49.3, color: "#122654", bold: true },
    },
    leaderboard: {
      rows: [
        { y: 206, nameX: 185, scoreX: 460 },
        { y: 251.56, nameX: 185, scoreX: 460 },
        { y: 297, nameX: 185, scoreX: 460, current: true },
        { y: 342.55, nameX: 185, scoreX: 460 },
        { y: 388.04, nameX: 185, scoreX: 460 },
        { y: 433.54, nameX: 185, scoreX: 460 },
        { y: 479.03, nameX: 185, scoreX: 460 },
        { y: 524.52, nameX: 185, scoreX: 460 },
      ],
      size: 22.9,
      nameColor: "#01d701",
      scoreColor: "#122654",
      currentColor: "#122654",
    },
  };

  function pct(v) {
    return `${(v / DESIGN) * 100}%`;
  }

  function scaleFont(px) {
    const el = document.getElementById(OVERLAY_ID);
    const h = el?.clientHeight || DESIGN;
    return Math.round(px * (h / DESIGN));
  }

  // Пересчитывает размеры динамических надписей (счёт, строки лидерборда)
  // под текущий размер оверлея. Позиции заданы в %, поэтому едут сами,
  // а font-size фиксируется в px при рендере — его надо обновлять на ресайзе.
  function relayoutDynamicFonts() {
    const el = document.getElementById(OVERLAY_ID);
    if (!el) return;
    el.querySelectorAll("[data-kop-font-size]").forEach((node) => {
      const sz = Number(node.dataset.kopFontSize);
      if (sz > 0) node.style.fontSize = `${scaleFont(sz)}px`;
    });
  }

  function ensureOverlay() {
    let el = document.getElementById(OVERLAY_ID);
    if (!el) {
      el = document.createElement("div");
      el.id = OVERLAY_ID;
      el.className = "figma-overlay";
      el.setAttribute("aria-hidden", "true");
      document.body.appendChild(el);
    }
    return el;
  }

  function hideStaticOverlay() {
    const el = document.getElementById(OVERLAY_ID);
    if (el) el.style.display = "none";
  }

  function showStaticOverlay() {
    ensureOverlay().style.display = "block";
  }

  function preload(scene) {
    const design = D();
    if (!design) return;

    scene.load.on("loaderror", (file) => {
      console.warn("[Kopilka] texture load failed:", file?.src || file?.key);
    });

    design.getTextureEntries().forEach(({ key, file }) => {
      if (!file.toLowerCase().endsWith(".png")) return;
      if (!scene.textures.exists(key)) {
        scene.load.image(key, design.url(file));
      }
    });
  }

  function drawGradientBg(scene) {
    const design = D();
    const w = scene.scale.width;
    const h = scene.scale.height;
    const g = scene.add.graphics().setDepth(0);
    const top = design?.gradient?.top ?? 0xecfffe;
    const bottom = design?.gradient?.bottom ?? 0x9effa8;
    g.fillGradientStyle(top, top, bottom, bottom, 1);
    g.fillRect(0, 0, w, h);
    return g;
  }

  function placeImage(scene, file, x, y, w, h, depth, originX, originY) {
    const design = D();
    const key = design.textureKey(file);
    if (!scene.textures.exists(key)) return null;
    const img = scene.add.image(design.sx(x), design.sy(y), key);
    img.setDisplaySize(design.sx(w), design.sy(h));
    img.setDepth(depth ?? 2);
    img.setOrigin(originX ?? 0.5, originY ?? 0.5);
    return img;
  }

  function ensureOverlayLayers(root) {
    let bg = root.querySelector(".figma-overlay__bg");
    if (!bg) {
      bg = document.createElement("div");
      bg.className = "figma-overlay__bg";
      root.appendChild(bg);
    }
    let stage = root.querySelector(".figma-overlay__stage");
    if (!stage) {
      stage = document.createElement("div");
      stage.className = "figma-overlay__stage";
      root.appendChild(stage);
    }
    let chrome = root.querySelector(".figma-overlay__chrome");
    if (!chrome) {
      chrome = document.createElement("div");
      chrome.className = "figma-overlay__chrome";
      root.appendChild(chrome);
    }
    return { bg, stage, chrome };
  }

  const FRAME_LOAD_TIMEOUT_MS = 6000;
  let _currentScreenId = null;

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function getActiveFrame(stage) {
    return stage?.querySelector(".figma-overlay__frame--active") || null;
  }

  function getCurrentScreenId() {
    return _currentScreenId;
  }

  function setCurrentScreenId(screenId) {
    _currentScreenId = screenId || null;
  }

  function waitFrameLoad(frame, timeoutMs) {
    timeoutMs = timeoutMs || FRAME_LOAD_TIMEOUT_MS;
    return new Promise((resolve) => {
      if (frame.contentDocument?.readyState === "complete") {
        resolve(frame);
        return;
      }
      const timer = window.setTimeout(() => resolve(frame), timeoutMs);
      frame.addEventListener(
        "load",
        () => {
          window.clearTimeout(timer);
          resolve(frame);
        },
        { once: true },
      );
    });
  }

  function htmlScreenId(screenId) {
    if (screenId === "result_top") return "result_score";
    return screenId;
  }

  function isLegacyResultScreen(screenId) {
    return screenId?.startsWith("result_") && !screenId.startsWith("result_stars_");
  }

  function mountIframe(stage, screenId, extraClass) {
    const frame = document.createElement("iframe");
    frame.className = `figma-overlay__frame${extraClass ? ` ${extraClass}` : ""}`;
    const FIGMA_IFRAME_V = 32;
    frame.src = HTML_BASE + htmlScreenId(screenId) + ".html?v=" + FIGMA_IFRAME_V;
    frame.setAttribute("scrolling", "no");
    frame.setAttribute("title", screenId);
    stage.appendChild(frame);
    return frame;
  }

  // ── Кэш постоянных экранов ──────────────────────────────────────────────
  // Статичные экраны (старт, онбординги, фон игры) монтируются ОДИН раз и
  // больше не перезагружаются: между ними переключаемся анимацией/видимостью,
  // а игра накладывается/убирается диссолвом. Это убирает декод-провал.
  const CACHE_SCREENS = new Set([
    "start",
    "onboarding_1",
    "onboarding_2",
    "game-bg",
  ]);
  const PRELOAD_ORDER = [
    "start",
    "onboarding_1",
    "onboarding_2",
    "game-bg",
  ];
  const isCachedScreen = (id) => CACHE_SCREENS.has(id);
  const frameCache = new Map(); // screenId -> iframe
  let _preloadStarted = false;

  // Берём кадр из кэша (или создаём и кэшируем для статичных экранов).
  function acquireFrame(stage, screenId, extraClass) {
    if (isCachedScreen(screenId)) {
      let frame = frameCache.get(screenId);
      if (frame) {
        if (frame.parentElement !== stage) stage.appendChild(frame);
        frame.className = `figma-overlay__frame${extraClass ? ` ${extraClass}` : ""}`;
        // Сбрасываем возможные остаточные классы анимации внутри кадра.
        postAnim(frame, "reset");
        return frame;
      }
      frame = mountIframe(stage, screenId, extraClass);
      frame.dataset.kopCached = "1";
      frameCache.set(screenId, frame);
      return frame;
    }
    return mountIframe(stage, screenId, extraClass);
  }

  // Убираем кадр: кэшированный — прячем (остаётся загруженным), иначе удаляем.
  function releaseFrame(frame) {
    if (!frame) return;
    if (frame.dataset && frame.dataset.kopCached === "1") {
      frame.className = "figma-overlay__frame figma-overlay__frame--prep";
      postAnim(frame, "reset");
      return;
    }
    frame.remove();
  }

  // Прячем все кадры в стопке (кэшированные — скрываем, прочие — удаляем).
  function hideAllStageFrames(stage) {
    if (!stage) return;
    stage.querySelectorAll(".figma-overlay__frame").forEach((f) => releaseFrame(f));
  }

  // Предзагрузка всех статичных экранов скрытыми (по одному, чтобы не было
  // пиковой нагрузки на главный поток от Babel в каждом iframe).
  function preloadStaticScreens() {
    if (_preloadStarted) return;
    _preloadStarted = true;
    const root = ensureOverlay();
    if (!root.style.display) root.style.display = "none";
    const { stage } = ensureOverlayLayers(root);
    PRELOAD_ORDER.forEach((id, i) => {
      window.setTimeout(() => {
        if (frameCache.has(id)) return;
        const frame = mountIframe(stage, id, "figma-overlay__frame--prep");
        frame.dataset.kopCached = "1";
        frameCache.set(id, frame);
      }, i * 140);
    });
  }

  function prefetchScreen(screenId) {
    const href = HTML_BASE + htmlScreenId(screenId) + ".html";
    if (document.querySelector(`link[data-prefetch="${href}"]`)) return;
    const link = document.createElement("link");
    link.rel = "prefetch";
    link.href = href;
    link.setAttribute("data-prefetch", href);
    document.head.appendChild(link);
  }

  function placeResultHeart(chrome) {
    const design = D();
    const src = design?.url(design.shared.resultHeart);
    if (!src) return;

    const wrap = document.createElement("div");
    wrap.className = "figma-result-heart figma-result-heart--enter";
    const img = document.createElement("img");
    img.className = "figma-result-heart__img";
    img.alt = "";
    img.src = src;
    wrap.appendChild(img);
    chrome.appendChild(wrap);
  }

  function preserveResultNickNodes(chrome) {
    if (!chrome) return [];
    return [
      ...chrome.querySelectorAll(
        ".figma-result-nick, .figma-result-nick__status, .figma-result-nick__countdown",
      ),
    ];
  }

  function applyChrome(chrome, screenId, opts) {
    const preservedNick =
      screenId.startsWith("result_") || opts?.preserveResultNick
        ? preserveResultNickNodes(chrome)
        : [];
    chrome.innerHTML = "";
    preservedNick.forEach((el) => chrome.appendChild(el));
    const spec = D().screens[screenId];
    if (spec?.hint) {
      const hint = document.createElement("p");
      hint.className = "figma-overlay__hint";
      hint.textContent = spec.hint;
      chrome.appendChild(hint);
    }
    if (opts?.leaderboard?.length) {
      renderLeaderboard(chrome, opts.leaderboard);
    }
    if (screenId === "result_top") {
      placeResultHeart(chrome);
    }
    const dyn = DYNAMIC[screenId];
    const animateResult = screenId.startsWith("result_");
    if (dyn?.label?.text) {
      placeDynamicText(chrome, dyn.label, dyn.label.text, { animateEnter: animateResult });
    }
    if (opts?.score != null && dyn?.score) {
      placeDynamicText(
        chrome,
        dyn.score,
        String(opts.score).padStart(3, "0"),
        { animateEnter: animateResult, delay: 0.08 },
      );
    }
  }

  const SCREEN_HIDDEN_NODES = {
    result_score: ["25:1704", "25:1705", "25:1706"],
    result_top: ["25:1704", "25:1705", "25:1706"],
    result_record: ["25:2017", "25:2018", "25:2019"],
    leaderboard: [
      "25:2224",
      "25:2226", "25:2227", "25:2229", "25:2230",
      "25:2232", "25:2233", "25:2235", "25:2236",
      "25:2237", "25:2238", "25:2239", "25:2241", "25:2242",
      "25:2244", "25:2245", "25:2247", "25:2248",
    ],
  };

  function injectScreenHiddenStyle(frame, screenId) {
    const doc = frame?.contentDocument;
    const ids = SCREEN_HIDDEN_NODES[screenId];
    if (!doc?.head || !ids?.length) return;

    const styleId = `kopilka-hidden-${screenId}`;
    let style = doc.getElementById(styleId);
    if (!style) {
      style = doc.createElement("style");
      style.id = styleId;
      doc.head.appendChild(style);
    }
    style.textContent = ids
      .map(
        (id) =>
          `[data-node-id="${id}"],[data-node-id="${id}"] *{display:none!important;visibility:hidden!important;}`,
      )
      .join("");
  }

  function applyScreenHidden(frame, screenId) {
    injectScreenHiddenStyle(frame, screenId);
  }

  function scheduleScreenHiddenRetries(frame, screenId) {
    if (!SCREEN_HIDDEN_NODES[screenId]) return;
    applyScreenHidden(frame, screenId);
    swapResultKopilka(frame, screenId);
    scheduleResultScreenFixes(frame, screenId);
    [500, 1500].forEach((ms) => {
      window.setTimeout(() => {
        if (!frame?.isConnected) return;
        applyScreenHidden(frame, screenId);
        swapResultKopilka(frame, screenId);
        fixResultScreenMonsters(frame, screenId);
      }, ms);
    });
  }

  const RESULT_KOPILKA = {
    result_score: { nodeId: "25:1645", assetKey: "resultPigMiss" },
    result_top: { nodeId: "25:1645", assetKey: "resultPigTop" },
    result_record: { nodeId: "25:1958", assetKey: "resultPigLeader" },
  };

  function swapResultKopilka(frame, screenId) {
    const spec = RESULT_KOPILKA[screenId];
    const design = D();
    const file = design?.shared?.[spec?.assetKey];
    const doc = frame?.contentDocument;
    if (!spec || !file || !doc) return;

    const img = doc.querySelector(`[data-node-id="${spec.nodeId}"] img`);
    if (!img) return;
    const src = design.url(file);
    if (img.getAttribute("src") !== src) img.setAttribute("src", src);
  }

  function waitFramePaint() {
    return new Promise((resolve) => window.setTimeout(resolve, 50));
  }

  function waitForIframeScreen(frame, timeoutMs) {
    timeoutMs = timeoutMs || 5000;
    return new Promise((resolve) => {
      const started = performance.now();
      let done = false;

      const finish = () => {
        if (done) return;
        done = true;
        window.removeEventListener("message", onMessage);
        resolve(frame);
      };

      const onMessage = (ev) => {
        if (ev.source !== frame.contentWindow) return;
        if (ev.data?.type === "kopilka-screen-ready") finish();
      };

      window.addEventListener("message", onMessage);

      const poll = () => {
        const doc = frame.contentDocument;
        const mount = doc?.getElementById("root");
        if (mount?.childElementCount) {
          requestAnimationFrame(() => requestAnimationFrame(finish));
          return;
        }
        if (performance.now() - started > timeoutMs) {
          finish();
          return;
        }
        requestAnimationFrame(poll);
      };

      if (frame.contentDocument?.readyState === "complete") poll();
      else {
        frame.addEventListener("load", () => poll(), { once: true });
        window.setTimeout(finish, timeoutMs);
      }
    });
  }

  function scheduleAnimReset(frame, action, Anim) {
    if (!Anim || !frame) return;
    // Вызывающие (playEnterAnimation / параллельный слайд) УЖЕ дождались
    // длительности анимации, поэтому сбрасываем класс почти сразу — иначе
    // получался «ступор»: ин-анимация давно закончилась (forwards держит
    // финальный кадр), а idle не стартует ещё ~длительность до сброса.
    window.setTimeout(() => Anim.runOnFrame(frame, "reset"), 24);
  }

  function nextFrame() {
    return new Promise((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(resolve)),
    );
  }

  // Собирает url() из mask-image / -webkit-mask-image / background-image
  // всех элементов кадра — это ассеты, которых нет в doc.images.
  function collectCssImageUrls(doc) {
    const urls = new Set();
    const win = doc.defaultView;
    if (!win) return urls;
    const els = doc.querySelectorAll("*");
    const re = /url\((['"]?)([^'")]+)\1\)/g;
    els.forEach((el) => {
      const cs = win.getComputedStyle(el);
      const props = [
        cs.getPropertyValue("mask-image"),
        cs.getPropertyValue("-webkit-mask-image"),
        cs.getPropertyValue("background-image"),
      ];
      props.forEach((val) => {
        if (!val || val === "none") return;
        let m;
        while ((m = re.exec(val))) {
          const u = m[2];
          if (u && !u.startsWith("data:") && !u.startsWith("linear-gradient")) {
            urls.add(u);
          }
        }
      });
    });
    return urls;
  }

  // Ждём, пока ВСЕ картинки кадра не просто загрузятся, а будут декодированы
  // и готовы к отрисовке (img.decode()), включая mask/background из CSS.
  // Это устраняет «выскакивание» ассетов в момент проигрывания анимации.
  function waitForIframeImages(frame, timeoutMs) {
    timeoutMs = timeoutMs || 4000;
    const doc = frame?.contentDocument;
    const win = frame?.contentWindow;
    if (!doc || !win) return Promise.resolve();

    const tasks = [];

    Array.from(doc.images || []).forEach((img) => {
      tasks.push(
        Promise.resolve()
          .then(() => (img.decode ? img.decode() : null))
          .catch(() => {
            if (img.complete) return;
            return new Promise((res) => {
              img.addEventListener("load", res, { once: true });
              img.addEventListener("error", res, { once: true });
            });
          }),
      );
    });

    collectCssImageUrls(doc).forEach((url) => {
      tasks.push(
        new Promise((res) => {
          const probe = new win.Image();
          const finish = () => res();
          probe.onload = () => {
            if (probe.decode) probe.decode().then(finish, finish);
            else finish();
          };
          probe.onerror = finish;
          probe.src = url;
        }),
      );
    });

    if (!tasks.length) return Promise.resolve();

    return Promise.race([
      Promise.all(tasks),
      new Promise((res) => window.setTimeout(res, timeoutMs)),
    ]);
  }

  function postAnim(frame, action) {
    frame?.contentWindow?.postMessage({ type: "kopilka-anim", action }, "*");
  }

  function reveal(frame, fade) {
    frame.classList.remove("figma-overlay__frame--prep");
    frame.classList.add("figma-overlay__frame--active");
    if (fade) {
      frame.classList.add("figma-overlay__frame--reveal");
      window.setTimeout(
        () => frame.classList.remove("figma-overlay__frame--reveal"),
        450,
      );
    }
  }

  /**
   * Входная анимация: класс ставится, пока кадр скрыт (prep), элементы
   * уходят в стартовое состояние (opacity:0), затем кадр показывается и
   * анимация проигрывается с самого начала — без мигания и рывков.
   */
  async function playEnterAnimation(frame, action, Anim) {
    if (!Anim || !frame.contentWindow) {
      reveal(frame);
      return;
    }
    postAnim(frame, action);
    await nextFrame();
    await new Promise((r) => window.setTimeout(r, 24));
    reveal(frame, true);
    const ms = Anim.DURATIONS?.[action] ?? 560;
    await new Promise((r) => window.setTimeout(r, ms));
    scheduleAnimReset(frame, action, Anim);
  }

  async function prepareResultFrame(frame, screenId) {
    if (!screenId?.startsWith("result_")) return;
    applyScreenHidden(frame, screenId);
    swapResultKopilka(frame, screenId);
    fixResultScreenMonsters(frame, screenId);
    await waitFramePaint(frame);
    swapResultKopilka(frame, screenId);
    fixResultScreenMonsters(frame, screenId);
  }

  const RESULT_INFLATION_MASK_NODES = [
    "25:1693",
    "25:1694",
    "25:1696",
    "25:1697",
    "25:1698",
    "25:1699",
    "25:1700",
    "25:2006",
    "25:2007",
    "25:2009",
    "25:2010",
    "25:2011",
    "25:2012",
    "25:2013",
  ];

  const RESULT_INFLATION_PLACE = {
    left: 428,
    top: 308,
    w: 124,
    h: 124,
  };

  function injectResultScreenFixStyle(doc) {
    if (!doc?.head) return;
    const styleId = "kop-result-screen-fix";
    let style = doc.getElementById(styleId);
    if (!style) {
      style = doc.createElement("style");
      style.id = styleId;
      doc.head.appendChild(style);
    }
    const hideMask = RESULT_INFLATION_MASK_NODES.map(
      (id) =>
        `[data-node-id="${id}"],[data-node-id="${id}"] *{display:none!important;visibility:hidden!important;}`,
    ).join("");
    style.textContent =
      `#capture,#root,[data-node-id="25:1632"],[data-node-id="25:1944"]{` +
      `overflow:hidden!important;` +
      `}` +
      hideMask +
      `.kop-result-inflation-fix{` +
      `position:absolute;left:${RESULT_INFLATION_PLACE.left}px;top:${RESULT_INFLATION_PLACE.top}px;` +
      `width:${RESULT_INFLATION_PLACE.w}px;height:${RESULT_INFLATION_PLACE.h}px;` +
      `pointer-events:none;z-index:6;transform-origin:50% 85%;` +
      `}` +
      `.kop-result-inflation-fix img{display:block;width:100%;height:100%;object-fit:contain;}`;
  }

  function ensureResultInflationSprite(doc) {
    const design = D();
    const src = design?.url(design.shared.ghostInflation);
    if (!src || !doc) return;

    const host = doc.getElementById("root") || doc.body;
    let el = doc.getElementById("kop-inflation-fix");
    if (!el) {
      el = doc.createElement("div");
      el.id = "kop-inflation-fix";
      el.className = "kop-result-inflation-fix";
      const img = doc.createElement("img");
      img.alt = "";
      el.appendChild(img);
      host.appendChild(el);
    }
    const img = el.querySelector("img");
    if (img && img.getAttribute("src") !== src) img.setAttribute("src", src);
  }

  function fixResultScreenMonsters(frame, screenId) {
    if (!screenId?.startsWith("result_")) return;
    const doc = frame?.contentDocument;
    if (!doc) return;
    injectResultScreenFixStyle(doc);
    ensureResultInflationSprite(doc);
  }

  function scheduleResultScreenFixes(frame, screenId) {
    if (!screenId?.startsWith("result_")) return;
    fixResultScreenMonsters(frame, screenId);
    [120, 500, 1500].forEach((ms) => {
      window.setTimeout(() => {
        if (!frame?.isConnected) return;
        fixResultScreenMonsters(frame, screenId);
      }, ms);
    });
  }

  function frameAnimAction(transitionKey) {
    if (transitionKey === "result-enter") return "transition-in";
    return transitionKey;
  }

  function markResultChromeExit(chrome) {
    if (!chrome) return;
    chrome
      .querySelectorAll(
        ".figma-text--dynamic, .figma-result-nick, .figma-result-nick__status, .figma-result-nick__countdown",
      )
      .forEach((el) => el.classList.add("figma-text--result-exit"));
  }

  async function prepareIncomingFrame(incoming, screenId) {
    const isResult = isLegacyResultScreen(screenId);
    if (SCREEN_HIDDEN_NODES[screenId]) {
      injectScreenHiddenStyle(incoming, screenId);
    }

    if (isResult) {
      await prepareResultFrame(incoming, screenId);
      scheduleScreenHiddenRetries(incoming, screenId);
    } else if (SCREEN_HIDDEN_NODES[screenId]) {
      scheduleScreenHiddenRetries(incoming, screenId);
    } else {
      swapResultKopilka(incoming, screenId);
    }
  }

  async function crossfadeTo(root, screenId, opts) {
    root = root || ensureOverlay();
    const { stage, chrome } = ensureOverlayLayers(root);
    const fromId = _currentScreenId;
    const Anim = window.KopilkaFigmaAnim;
    const tr = Anim?.resolveScreenTransition
      ? Anim.resolveScreenTransition(fromId, screenId)
      : {};
    const isResult = screenId.startsWith("result_");
    const needsPrep = !!tr.in || isResult;
    const deferChrome = tr.out === "result-exit";
    showStaticOverlay();
    if (!deferChrome) {
      applyChrome(chrome, screenId, opts || {});
    }

    const outgoing = getActiveFrame(stage);
    // При dropOutgoing (старт → онбординг) исходящий кадр НЕ убираем сразу:
    // после start-exit это просто фон-градиент, и он удерживает картинку, пока
    // входящий экран грузится и декодируется. Кадр удалится уже ПОСЛЕ показа
    // входящего (ветка tr.in ниже). Иначе виден пустой провал и резкое
    // «выскакивание» ассетов в момент анимации.
    const outgoingFrame = outgoing;
    const useGenericSlide = !tr.out && !tr.in && !!outgoingFrame;

    let incomingClass = "figma-overlay__frame--active";
    if (useGenericSlide) {
      incomingClass = "figma-overlay__frame--enter";
    } else if (needsPrep) {
      incomingClass = "figma-overlay__frame--prep";
    }

    const incoming = acquireFrame(stage, screenId, incomingClass);
    await waitFrameLoad(incoming);
    await waitForIframeScreen(incoming);
    await prepareIncomingFrame(incoming, screenId);
    await waitForIframeImages(incoming);
    await waitFramePaint();

    if (tr.out === "result-exit") {
      markResultChromeExit(chrome);
    }

    let chromeReadyCalled = false;
    const callChromeReady = () => {
      if (chromeReadyCalled) return;
      chromeReadyCalled = true;
      if (typeof opts?.onScreenReady === "function") {
        opts.onScreenReady(chrome, screenId);
      }
    };

    const DUR = (k) => Anim?.DURATIONS?.[k] ?? 560;

    if (tr.parallel && outgoingFrame && tr.out && tr.in) {
      // Онбординг 1→2→3: новый кадр уже скрыт (prep) — ставим стартовое
      // состояние slide-in, показываем и одновременно гоним старый влево.
      postAnim(incoming, tr.in);
      await nextFrame();
      await new Promise((r) => window.setTimeout(r, 24));
      reveal(incoming);
      postAnim(outgoingFrame, tr.out);
      await delay(Math.max(DUR(tr.in), DUR(tr.out)));
      releaseFrame(outgoingFrame);
      scheduleAnimReset(incoming, tr.in, Anim);
    } else if (tr.out && outgoingFrame) {
      // Результат → лидерборд: сначала выход старого, затем вход нового.
      if (Anim) await Anim.runOnFrame(outgoingFrame, tr.out);
      else await delay(560);
      releaseFrame(outgoingFrame);

      if (deferChrome) {
        applyChrome(chrome, screenId, opts || {});
        callChromeReady();
      }

      if (tr.in) {
        await playEnterAnimation(incoming, frameAnimAction(tr.in), Anim);
      } else {
        reveal(incoming);
      }
    } else if (tr.in) {
      // Старт → онбординг, либо вход результата.
      await playEnterAnimation(incoming, frameAnimAction(tr.in), Anim);
      if (outgoingFrame) releaseFrame(outgoingFrame);
    } else if (useGenericSlide && outgoingFrame) {
      incoming.classList.remove("figma-overlay__frame--prep");
      incoming.classList.add("figma-overlay__frame--active");
      outgoingFrame.classList.remove("figma-overlay__frame--active");
      outgoingFrame.classList.add("figma-overlay__frame--leave");
      await delay(520);
      releaseFrame(outgoingFrame);
      incoming.classList.remove("figma-overlay__frame--enter");
    } else {
      reveal(incoming);
      if (outgoingFrame) releaseFrame(outgoingFrame);
    }

    _currentScreenId = screenId;

    if (screenId === "leaderboard") {
      prefetchScreen("leaderboard");
    }

    if (Anim) {
      Anim.onRecord(screenId, root);
    }

    if (!deferChrome) {
      callChromeReady();
    }

    return incoming;
  }

  function placeDynamicText(root, spec, text, opts) {
    const p = document.createElement("p");
    p.className = "figma-text figma-text--dynamic";
    if (spec.onCloud) p.classList.add("figma-text--on-cloud");
    if (opts?.animateEnter) p.classList.add("figma-text--enter");
    if (opts?.delay != null) {
      p.style.animationDelay = `${opts.delay}s`;
    }
    p.style.left = pct(spec.x);
    p.style.top = pct(spec.y);
    p.dataset.kopFontSize = String(spec.size);
    p.style.fontSize = `${scaleFont(spec.size)}px`;
    p.style.color = spec.color;
    p.style.fontWeight = spec.bold ? "700" : "600";
    p.style.transform = "translateX(-50%)";
    p.style.fontFamily = '"SB Sans Display", "Segoe UI", sans-serif';
    p.style.lineHeight = "0.75";
    p.style.textTransform = "lowercase";
    p.style.letterSpacing = spec.size >= 40 ? "-0.07em" : "-0.07em";
    p.textContent = text;
    root.appendChild(p);
    return p;
  }

  function updateLeaderboardChrome(entries) {
    const root = ensureOverlay();
    const { chrome } = ensureOverlayLayers(root);
    chrome.querySelectorAll(".figma-lb-name, .figma-lb-score").forEach((el) => el.remove());
    renderLeaderboard(chrome, entries);
  }

  function primeLeaderboardOverlay(entries) {
    const root = ensureOverlay();
    showStaticOverlay();
    const { chrome } = ensureOverlayLayers(root);
    applyChrome(chrome, "leaderboard", { leaderboard: entries || [] });
    prefetchScreen("leaderboard");
  }

  function renderLeaderboard(root, entries) {
    const spec = DYNAMIC.leaderboard;
    const rows = (entries || []).slice(0, spec.rows.length);
    while (rows.length < spec.rows.length) {
      const i = rows.length;
      rows.push({
        name: i === 1 ? "текущий гость" : `гость ${i + 1}`,
        score: 0,
        current: i === 1,
      });
    }

    spec.rows.forEach((row, i) => {
      const e = rows[i] || {};
      const isCurrent = !!e.current;
      const name = document.createElement("p");
      name.className = "figma-lb-name";
      name.style.left = pct(row.nameX);
      name.style.top = pct(row.y);
      name.dataset.kopFontSize = String(spec.size);
      name.style.fontSize = `${scaleFont(spec.size)}px`;
      name.style.color = isCurrent ? spec.currentColor : spec.nameColor;
      name.textContent = e.name || `гость ${i + 1}`;
      root.appendChild(name);

      const score = document.createElement("p");
      score.className = "figma-lb-score";
      score.style.left = pct(row.scoreX);
      score.style.top = pct(row.y);
      score.dataset.kopFontSize = String(spec.size);
      score.style.fontSize = `${scaleFont(spec.size)}px`;
      score.style.color = spec.scoreColor;
      score.textContent =
        e.score != null ? String(e.score).padStart(3, "0") : "000";
      root.appendChild(score);
    });
  }

  function buildStaticScreen(_scene, screenId, opts) {
    const design = D();
    const spec = design.screens[screenId];
    if (!spec) return null;

    const root = ensureOverlay();
    const hadStage = !!root.querySelector(".figma-overlay__stage .figma-overlay__frame");

    if (!hadStage) {
      // Подчищаем только некэшированные элементы — кэшированные кадры (старт,
      // онбординги, фон игры) должны жить весь сеанс и не перезагружаться.
      root.querySelectorAll(".figma-overlay__preview, .figma-text, .figma-overlay__hint").forEach((el) => el.remove());
      root.querySelectorAll(".figma-overlay__frame").forEach((f) => {
        if (!(f.dataset && f.dataset.kopCached === "1")) f.remove();
      });
      _currentScreenId = null;
    }

    const framePromise = crossfadeTo(root, screenId, opts);
    return {
      spec,
      texts: [],
      hint: null,
      root,
      get frame() {
        return root.querySelector(".figma-overlay__frame--active");
      },
      framePromise,
    };
  }

  async function animateDissolve(root) {
    if (window.KopilkaFigmaAnim) {
      await window.KopilkaFigmaAnim.dissolve(root);
    } else {
      await delay(620);
    }
  }

  async function dissolveGameLayer() {
    const root = document.getElementById(OVERLAY_ID);
    const gameRoot = document.getElementById(GAME_ROOT_ID);
    const frame = root?.querySelector(".figma-overlay__frame--active");

    if (gameRoot) gameRoot.classList.add("kop-game-dissolve");
    if (frame) {
      await animateDissolve(root);
    } else {
      await delay(620);
    }

    hideGameLayer();
    gameRoot?.classList.remove("kop-game-dissolve");
    _currentScreenId = null;
  }

  async function dissolveStaticScreen() {
    const root = ensureOverlay();
    const frame = getActiveFrame(root.querySelector(".figma-overlay__stage"));
    if (frame) {
      await animateDissolve(root);
    } else {
      await delay(620);
    }
    _currentScreenId = null;
    hideStaticOverlay();
  }

  function drawGameBackground(scene) {
    const design = D();
    drawGradientBg(scene);
    placeImage(scene, design.shared.fieldShadow1, 336, 348, 722, 722, 2, 0.5, 0.5)?.setAlpha(0.45);
    placeImage(scene, design.shared.fieldShadow2, 336, 344, 722, 722, 2, 0.5, 0.5)?.setAlpha(0.4);
  }

  function createGameHud(scene, initialScore, initialLives, initialTime) {
    const design = D();
    const depth = 40;
    const cx = design.sx(336);
    const cy = design.sy(608);

    const cloud = scene.add.graphics().setDepth(depth);
    cloud.fillStyle(0xffffff, 0.96);
    cloud.fillCircle(cx, cy, design.sx(72));
    cloud.fillCircle(cx - design.sx(36), cy + design.sy(6), design.sx(48));
    cloud.fillCircle(cx + design.sx(36), cy + design.sy(6), design.sx(48));

    const scoreLabel = scene.add
      .text(cx - 4, cy - 14, "счёт:", {
        fontFamily: "Segoe UI, Arial, sans-serif",
        fontSize: "17px",
        color: "#01d701",
        fontStyle: "bold",
      })
      .setOrigin(1, 0.5)
      .setDepth(depth + 2);

    const scoreValue = scene.add
      .text(cx, cy + 2, String(initialScore).padStart(3, "0"), {
        fontFamily: "Segoe UI, Arial, sans-serif",
        fontSize: "28px",
        color: "#122654",
        fontStyle: "bold",
      })
      .setOrigin(0, 0.5)
      .setDepth(depth + 2);

    const livesText = scene.add
      .text(design.sx(336), design.sy(36), "♥".repeat(initialLives), {
        fontFamily: "Segoe UI, Arial, sans-serif",
        fontSize: "22px",
        color: "#ff4fa3",
      })
      .setOrigin(0.5)
      .setDepth(depth + 2);

    const timeText = scene.add
      .text(scene.scale.width - 12, 12, `${initialTime} с`, {
        fontFamily: "Segoe UI, Arial, sans-serif",
        fontSize: "14px",
        color: "#122654",
        fontStyle: "bold",
        backgroundColor: "#ffffffcc",
        padding: { x: 8, y: 3 },
      })
      .setOrigin(1, 0)
      .setDepth(depth + 2);

    const modeText = scene.add
      .text(scene.scale.width / 2, 8, "", {
        fontFamily: "Segoe UI, Arial, sans-serif",
        fontSize: "13px",
        color: "#122654",
        fontStyle: "bold",
        backgroundColor: "#ffffffdd",
        padding: { x: 10, y: 3 },
      })
      .setOrigin(0.5, 0)
      .setDepth(depth + 2);

    return { scoreCloud: cloud, livesCloud: null, scoreLabel, scoreValue, livesText, timeText, modeText };
  }

  const GAME_BG_SCREEN = "game-bg";
  const GAME_HUD_ID = "game-hud";
  const GAME_ROOT_ID = "game-root";

  let gameHudEls = null;
  let lastGameScore = 0;

  function refreshPhaserLayout(stageEl) {
    const game = window.kopilkaGame;
    const gameRoot = document.getElementById(GAME_ROOT_ID);
    if (!game?.scale || !gameRoot) return;
    const parent = stageEl || gameRoot.parentElement || gameRoot;
    const w = parent.clientWidth || DESIGN;
    const h = parent.clientHeight || DESIGN;
    if (w < 2 || h < 2) return;
    try {
      if (typeof game.scale.setParentSize === "function") {
        game.scale.setParentSize(Math.max(DESIGN, w), Math.max(DESIGN, h));
      }
      game.scale.refresh();
    } catch {
      /* ignore */
    }
  }

  // Сцена рендерится в фиксированном «разрешении киоска» (DESIGN×DESIGN)
  // и отображается постоянным scale, не зависящим от размера браузера.
  function applyKioskScale() {
    document.documentElement.style.setProperty("--kiosk-scale", "0.87");
  }

  // Единый обработчик ресайза окна: сохраняем фиксированный scale, обновляем
  // родителя Phaser и при необходимости font-size динамических надписей.
  let _viewportResizeRaf = 0;
  function handleViewportResize() {
    if (_viewportResizeRaf) return;
    _viewportResizeRaf = window.requestAnimationFrame(() => {
      _viewportResizeRaf = 0;
      applyKioskScale();
      try {
        refreshPhaserLayout();
      } catch {
        /* ignore */
      }
      relayoutDynamicFonts();
    });
  }
  applyKioskScale();
  window.addEventListener("resize", handleViewportResize);
  window.addEventListener("orientationchange", handleViewportResize);

  function mountGameCanvasToStage(stage) {
    const gameRoot = document.getElementById(GAME_ROOT_ID);
    if (!gameRoot || !stage) return;
    stage.appendChild(gameRoot);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => refreshPhaserLayout(stage));
    });
  }

  function restoreGameCanvasHome() {
    const gameRoot = document.getElementById(GAME_ROOT_ID);
    const anchor = document.getElementById("pad-status");
    if (!gameRoot) return;
    document.body.insertBefore(gameRoot, anchor || null);
    refreshPhaserLayout();
  }

  function ensureGameHudRoot() {
    let el = document.getElementById(GAME_HUD_ID);
    if (!el) {
      el = document.createElement("div");
      el.id = GAME_HUD_ID;
      document.body.appendChild(el);
    }
    return el;
  }

  /** Узлы Figma, которые рисуем в Phaser / DOM-HUD (не в фоне iframe) */
  const GAME_BG_HIDDEN_NODES = [
    "25:173", "25:174", "25:175", "25:176", "25:177", "25:178", "25:179",
    "25:180",
    "25:139", "25:186", "25:195",
  ];

  function injectGameBgHiddenStyle(frame) {
    const doc = frame?.contentDocument;
    if (!doc?.head) return;
    const styleId = "kopilka-hidden-game-bg";
    let style = doc.getElementById(styleId);
    if (!style) {
      style = doc.createElement("style");
      style.id = styleId;
      doc.head.appendChild(style);
    }
    style.textContent = GAME_BG_HIDDEN_NODES.map(
      (id) => `[data-node-id="${id}"],[data-node-id="${id}"] *{display:none!important;}`,
    ).join("");
  }

  function scheduleGameBgHiddenRetries(frame) {
    injectGameBgHiddenStyle(frame);
    [500, 1500].forEach((ms) => {
      window.setTimeout(() => {
        if (frame?.isConnected) injectGameBgHiddenStyle(frame);
      }, ms);
    });
  }

  const LIVES_STAR_PATH =
    "M92.2385 7.11998C96.629 3.09232 103.371 3.09232 107.762 7.11998L115.473 14.1942C118.358 16.8402 122.391 17.8345 126.175 16.832L136.291 14.1519C142.05 12.626 148.02 15.7591 150.036 21.3658L153.577 31.2134C154.901 34.8969 158.011 37.6518 161.827 38.5226L172.03 40.8505C177.839 42.1759 181.668 47.7244 180.848 53.6258L179.407 63.9909C178.867 67.8679 180.341 71.7524 183.315 74.2969L191.267 81.0996C195.795 84.9727 196.607 91.6654 193.138 96.5095L187.045 105.018C184.766 108.2 184.265 112.324 185.717 115.96L189.597 125.679C191.806 131.212 189.415 137.516 184.092 140.193L174.743 144.895C171.246 146.654 168.886 150.073 168.482 153.966L167.4 164.375C166.785 170.301 161.738 174.772 155.781 174.669L145.318 174.487C141.404 174.419 137.726 176.35 135.558 179.61L129.764 188.324C126.465 193.285 119.919 194.898 114.692 192.039L105.511 187.015C102.077 185.137 97.9227 185.137 94.4888 187.015L85.3084 192.039C80.0815 194.898 73.5355 193.285 70.2364 188.324L64.4418 179.61C62.2744 176.35 58.5957 174.419 54.682 174.487L44.2188 174.669C38.2615 174.772 33.2151 170.301 32.5996 164.375L31.5184 153.966C31.114 150.073 28.754 146.654 25.257 144.895L15.908 140.193C10.5851 137.516 8.19439 131.212 10.4034 125.679L14.2833 115.96C15.7346 112.324 15.2338 108.2 12.9547 105.018L6.86164 96.5095C3.39256 91.6655 4.2052 84.9727 8.73273 81.0996L16.6849 74.2969C19.6593 71.7524 21.1325 67.8679 20.5934 63.9909L19.1522 53.6258C18.3316 47.7244 22.1615 42.1759 27.9703 40.8505L38.1729 38.5226C41.9892 37.6518 45.0989 34.8969 46.4233 31.2134L49.964 21.3658C51.9799 15.7591 57.9496 12.6259 63.709 14.1519L73.8248 16.832C77.6086 17.8345 81.6424 16.8402 84.5269 14.1942L92.2385 7.11998Z";

  const SCORE_STAR_PATH =
    "M87.5241 3.02075C91.9147 -1.00692 98.6566 -1.00692 103.047 3.02075L110.759 10.0949C113.643 12.741 117.677 13.7352 121.461 12.7327L131.577 10.0526C137.336 8.52672 143.306 11.6598 145.322 17.2666L148.862 27.1142C150.187 30.7976 153.296 33.5526 157.113 34.4234L167.315 36.7513C173.124 38.0767 176.954 43.6252 176.133 49.5265L174.692 59.8916C174.153 63.7686 175.626 67.6532 178.601 70.1977L186.553 77.0004C191.08 80.8735 191.893 87.5662 188.424 92.4103L182.331 100.918C180.052 104.101 179.551 108.225 181.002 111.86L184.882 121.579C187.091 127.113 184.701 133.417 179.378 136.094L170.029 140.796C166.532 142.554 164.172 145.973 163.767 149.867L162.686 160.276C162.071 166.202 157.024 170.673 151.067 170.569L140.604 170.388C136.69 170.32 133.011 172.251 130.844 175.51L125.049 184.224C121.75 189.186 115.204 190.799 109.977 187.939L100.797 182.916C97.3629 181.037 93.2084 181.037 89.7745 182.916L80.594 187.939C75.3671 190.799 68.8211 189.186 65.522 184.224L59.7275 175.51C57.56 172.251 53.8814 170.32 49.9677 170.388L39.5044 170.569C33.5472 170.673 28.5008 166.202 27.8852 160.276L26.804 149.867C26.3996 145.973 24.0396 142.554 20.5426 140.796L11.1936 136.094C5.87075 133.417 3.48004 127.113 5.68905 121.579L9.56894 111.86C11.0202 108.225 10.5194 104.101 8.24035 100.918L2.14729 92.4103C-1.32179 87.5662 -0.509145 80.8735 4.01838 77.0004L11.9705 70.1977C14.945 67.6532 16.4182 63.7686 15.8791 59.8916L14.4378 49.5265C13.6173 43.6252 17.4471 38.0767 23.2559 36.7513L33.4586 34.4234C37.2748 33.5526 40.3845 30.7976 41.7089 27.1142L45.2497 17.2666C47.2656 11.6598 53.2352 8.52672 58.9947 10.0526L69.1105 12.7327C72.8942 13.7352 76.928 12.741 79.8125 10.0949L87.5241 3.02075Z";

  const HEART_PATHS = [
    "M43.6453 130.549C42.009 128.913 41 126.541 41 124.07C41 119.061 44.8146 115 49.9281 115C52.5188 115 55.1916 116.374 56.8721 118.054C58.5526 116.374 61.2254 115 63.8161 115C68.9296 115 72.7442 119.061 72.7442 124.07C72.7442 126.608 71.8138 128.902 70.0988 130.549L57.557 142.835C57.1737 143.21 56.5705 143.21 56.1871 142.835L43.7667 130.667C43.7259 130.628 43.6854 130.589 43.6453 130.549Z",
    "M86.3914 130.549C84.755 128.913 83.7461 126.541 83.7461 124.07C83.7461 119.061 87.5607 115 92.6741 115C95.2649 115 97.9377 116.374 99.6182 118.054C101.299 116.374 103.972 115 106.562 115C111.676 115 115.49 119.061 115.49 124.07C115.49 126.608 114.56 128.902 112.845 130.549L100.303 142.835C99.9198 143.21 99.3166 143.21 98.9332 142.835L86.5128 130.667C86.472 130.628 86.4315 130.589 86.3914 130.549Z",
    "M129.134 130.549C127.497 128.913 126.488 126.541 126.488 124.07C126.488 119.061 130.303 115 135.416 115C138.007 115 140.68 116.374 142.36 118.054C144.041 116.374 146.714 115 149.305 115C154.418 115 158.233 119.061 158.233 124.07C158.233 126.608 157.302 128.902 155.587 130.549L143.045 142.835C142.662 143.21 142.059 143.21 141.676 142.835L129.255 130.667C129.214 130.628 129.174 130.589 129.134 130.549Z",
  ];

  const HEART_VIEWBOX = ["38 113 36 32", "82 113 36 32", "126 113 36 32"];

  function makeLifeHeart(index) {
    const el = document.createElement("span");
    el.className = "figma-life-heart figma-life-heart--active";
    el.dataset.index = String(index);
    el.innerHTML =
      `<svg class="figma-life-heart__svg" viewBox="${HEART_VIEWBOX[index]}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">` +
      `<path d="${HEART_PATHS[index]}"/>` +
      "</svg>";
    return el;
  }

  function makeHudCloudImg(className, assetKey) {
    const design = D();
    const wrap = document.createElement("div");
    wrap.className = `${className}-wrap`;
    const img = document.createElement("img");
    img.className = className;
    img.alt = "";
    img.src = design?.url(design.shared[assetKey]) || "";
    wrap.appendChild(img);
    return wrap;
  }

  function makeLivesCloudEl() {
    const wrap = document.createElement("div");
    wrap.className = "figma-game-hud-lives-cloud-wrap";
    wrap.innerHTML =
      `<svg class="figma-game-hud-lives-cloud" viewBox="0 0 200 200" preserveAspectRatio="xMidYMid meet" aria-hidden="true">` +
      `<path class="figma-game-hud-cloud-shape" d="${LIVES_STAR_PATH}"/>` +
      "</svg>";
    return wrap;
  }

  function makeScoreCloudEl() {
    return makeHudCloudImg("figma-game-hud-score-cloud", "hudScoreCloud");
  }

  function makeTimerCloudEl() {
    return makeHudCloudImg("figma-game-hud-timer-cloud", "hudTimerCloud");
  }

  function ensureGameHudChrome() {
    const design = D();
    const root = ensureGameHudRoot();
    root.innerHTML = "";
    root.classList.add("game-hud--active");

    const livesBlock = document.createElement("div");
    livesBlock.className = "figma-game-hud-lives-block";
    livesBlock.style.left = pct(291);
    livesBlock.style.top = pct(-72);
    livesBlock.style.width = pct(200);

    const heartsRow = document.createElement("div");
    heartsRow.className = "figma-game-hud-hearts";
    heartsRow.append(makeLifeHeart(0), makeLifeHeart(1), makeLifeHeart(2));

    livesBlock.append(makeLivesCloudEl(), heartsRow);

    const timeBlock = document.createElement("div");
    timeBlock.className = "figma-game-hud-timer-block";
    timeBlock.style.left = pct(388);
    timeBlock.style.top = pct(31);
    timeBlock.style.width = pct(63);
    timeBlock.style.height = pct(62);

    const timeLabel = document.createElement("p");
    timeLabel.className = "figma-game-hud-timer-label";
    timeLabel.textContent = "таймер:";

    const time = document.createElement("p");
    time.className = "figma-game-hud figma-game-hud--time";

    timeBlock.append(makeTimerCloudEl(), timeLabel, time);

    const mode = document.createElement("p");
    mode.className = "figma-game-hud figma-game-hud--mode";
    mode.style.left = pct(336);
    mode.style.top = pct(88);
    mode.style.transform = "translateX(-50%)";

    const scoreBlock = document.createElement("div");
    scoreBlock.className = "figma-game-hud-score-block";
    scoreBlock.style.left = pct(336);
    scoreBlock.style.top = pct(568);
    scoreBlock.style.width = pct(200);

    const scoreLabel = document.createElement("p");
    scoreLabel.className = "figma-game-hud-score-label";
    scoreLabel.textContent = "счёт:";

    const score = document.createElement("p");
    score.className = "figma-game-hud-score-value";
    score.textContent = "000";

    const scoreDecorL = document.createElement("img");
    scoreDecorL.className = "figma-game-hud-score-decor figma-game-hud-score-decor--l";
    scoreDecorL.alt = "";
    scoreDecorL.src = design?.url(design.shared.hudScoreDecorL) || "";

    const scoreDecorR = document.createElement("img");
    scoreDecorR.className = "figma-game-hud-score-decor figma-game-hud-score-decor--r";
    scoreDecorR.alt = "";
    scoreDecorR.src = design?.url(design.shared.hudScoreDecorR) || "";

    scoreBlock.append(makeScoreCloudEl(), scoreDecorL, scoreDecorR, scoreLabel, score);

    root.append(livesBlock, timeBlock, mode, scoreBlock);
    gameHudEls = { livesBlock, heartsRow, timeBlock, time, mode, scoreEl: score };
    return gameHudEls;
  }

  async function showGameLayer() {
    const root = ensureOverlay();
    root.classList.add("figma-overlay--game");
    document.body.classList.add("kopilka-game-active");
    document.getElementById("game-root")?.classList.add("game-active");

    const { stage, chrome } = ensureOverlayLayers(root);
    if (chrome) chrome.innerHTML = "";
    // Не уничтожаем статичные кадры — только прячем; игра ляжет сверху.
    hideAllStageFrames(stage);

    ensureGameHudChrome();
    const frame = acquireFrame(stage, GAME_BG_SCREEN, "figma-overlay__frame--active");
    mountGameCanvasToStage(stage);
    root.style.display = "block";

    await waitFrameLoad(frame);
    scheduleGameBgHiddenRetries(frame);
    updateGameScore(lastGameScore);
    refreshPhaserLayout(stage);

    return frame;
  }

  function hideGameLayer() {
    const root = document.getElementById(OVERLAY_ID);
    root?.querySelectorAll(".figma-overlay__frame").forEach((frame) => {
      frame._kopilkaBgObserver = null;
      frame._kopilkaScreenObserver = null;
    });
    restoreGameCanvasHome();
    document.body.classList.remove("kopilka-game-active");
    document.getElementById(GAME_ROOT_ID)?.classList.remove("game-active");
    const hudRoot = document.getElementById(GAME_HUD_ID);
    if (hudRoot) {
      hudRoot.classList.remove("game-hud--active");
      hudRoot.innerHTML = "";
    }
    if (root) {
      root.classList.remove("figma-overlay--game");
      // Прячем кадры (кэшированные сохраняем загруженными), не уничтожаем.
      hideAllStageFrames(root.querySelector(".figma-overlay__stage"));
    }
    gameHudEls = null;
    hideStaticOverlay();
  }

  function updateGameScore(score) {
    lastGameScore = Number(score) || 0;
    const text = String(lastGameScore).padStart(3, "0");
    if (gameHudEls?.scoreEl) gameHudEls.scoreEl.textContent = text;
  }

  function updateGameLives(lives) {
    const row = gameHudEls?.heartsRow;
    if (!row) return;
    const n = Math.max(0, Math.min(3, Number(lives) || 0));
    row.querySelectorAll(".figma-life-heart").forEach((el, i) => {
      const active = i < n;
      el.classList.toggle("figma-life-heart--active", active);
      el.classList.toggle("figma-life-heart--lost", !active);
      el.style.visibility = n === 0 ? "hidden" : "visible";
    });
  }

  function updateGameTime(sec) {
    if (!gameHudEls?.time) return;
    gameHudEls.time.textContent = `${Math.max(0, sec)} с`;
  }

  function updateGameMode(msg) {
    if (!gameHudEls?.mode) return;
    const text = msg || "";
    gameHudEls.mode.textContent = text;
    gameHudEls.mode.classList.toggle("is-pause", /^Пауза\s+\d+/i.test(text));
  }

  function createResultNickPicker(chrome, initialName) {
    if (!chrome) return null;

    chrome
      .querySelectorAll(
        ".figma-result-nick, .figma-result-nick__status, .figma-result-nick__countdown",
      )
      .forEach((el) => el.remove());

    const block = document.createElement("div");
    block.className = "figma-result-nick";
    block.setAttribute("aria-label", "Выбор имени");

    const left = document.createElement("span");
    left.className = "figma-result-nick__arrow";
    left.textContent = "◀";
    left.setAttribute("aria-hidden", "true");

    const value = document.createElement("p");
    value.className = "figma-result-nick__value";
    value.textContent = initialName || "Гость";

    const right = document.createElement("span");
    right.className = "figma-result-nick__arrow";
    right.textContent = "▶";
    right.setAttribute("aria-hidden", "true");

    block.append(left, value, right);

    const status = document.createElement("p");
    status.className = "figma-result-nick__status";

    const countdown = document.createElement("p");
    countdown.className = "figma-result-nick__countdown";

    chrome.append(block, status, countdown);

    return {
      setName(name) {
        value.textContent = name;
      },
      setStatus(text) {
        status.textContent = text || "";
      },
      setCountdown(sec) {
        countdown.textContent =
          sec > 0 ? `Cross (×) — в топ · ${sec} с` : "Переход в топ…";
      },
      setHintVisible(visible) {
        const hint = chrome.querySelector(".figma-overlay__hint");
        if (hint) hint.style.display = visible ? "block" : "none";
      },
      destroy() {
        block.remove();
        status.remove();
        countdown.remove();
      },
    };
  }

  function createGameHudProxy(initialScore, initialLives, initialTime) {
    updateGameScore(initialScore);
    updateGameLives(initialLives);
    updateGameTime(initialTime);
    updateGameMode("");

    return {
      scoreCloud: null,
      livesCloud: null,
      scoreLabel: null,
      scoreValue: { setText(v) { updateGameScore(parseInt(String(v).replace(/\D/g, ""), 10) || 0); } },
      livesText: {
        setText(v) {
          const n = parseInt(String(v), 10);
          if (!Number.isNaN(n)) updateGameLives(n);
          else updateGameLives((String(v).match(/♥/g) || []).length);
        },
      },
      timeText: { setText(v) { updateGameTime(parseInt(v, 10) || 0); } },
      modeText: { setText(v) { updateGameMode(v); } },
    };
  }

  window.KopilkaFigmaUi = {
    preload,
    hideStaticOverlay,
    showStaticOverlay,
    drawGradientBg,
    buildStaticScreen,
    crossfadeTo,
    getCurrentScreenId,
    setCurrentScreenId,
    prefetchScreen,
    animateDissolve,
    dissolveGameLayer,
    dissolveStaticScreen,
    drawGameBackground,
    createGameHud,
    createGameHudProxy,
    showGameLayer,
    hideGameLayer,
    updateGameScore,
    updateGameLives,
    updateGameTime,
    updateGameMode,
    refreshPhaserLayout,
    placeImage,
    createResultNickPicker,
    updateLeaderboardChrome,
    primeLeaderboardOverlay,
    preloadStaticScreens,
  };

  // Предзагружаем статичные экраны заранее (скрытыми), чтобы переходы
  // старт↔онбординги и вход игры шли без перезагрузки и декода в кадре.
  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", () => preloadStaticScreens());
  } else {
    preloadStaticScreens();
  }
})();
