/**
 * Маппинг Figma-ассетов (672×672) → Phaser-сцены. Экран: 672×672.
 * Файлы: /static/assets/figma/shared/<hash>.<ext>
 */
(function () {
  "use strict";

  const BASE = "/static/assets/figma/shared/";
  const MONSTER_BASE = "/static/assets/Monster/";
  const DESIGN_W = 672;
  const DESIGN_H = 672;
  /** Исходники 80×80 → на поле ~40 px (клетка ~29 px) */
  const GHOST_FIELD_SIZE = 40;

  function url(file) {
    if (file.charAt(0) === "/") return file;
    return BASE + file;
  }

  /** Масштаб координат макета под игровой канвас */
  function sx(v) {
    const sw = window.KopilkaMaze?.SCREEN_W ?? DESIGN_W;
    return (v * sw) / DESIGN_W;
  }

  function sy(v) {
    const sh = window.KopilkaMaze?.SCREEN_H ?? DESIGN_H;
    return (v * sh) / DESIGN_H;
  }

  const shared = {
    logo: "dd849ce3e75e01bc98af7d108143446b11e5b96c.svg",
    piggy: "ba682dc3889044076820b4f23216dee0a7394771.png",
    grassA: "1563697d12155680b73c4d623f05f35318b669a6.png",
    grassB: "488b182ee2274bda0e42f0406d131ba5de756d0c.png",
    grassC: "199c5ba01a61e6cc478ed13de37575b68e5c4776.png",
    coinBig: "9c7a52cb0aaebeae10b7379074ad3d6c045c76aa.png",
    bgDecorStart: "eeb09f2d809e30f9e9d5007b9ceecd44d294b462.svg",
    bgDecorGame: "bd338f5b9b0f56d0bb2cc179fb704abde6cb4956.svg",
    bgDecorOnb1: "4a4721b9a290a272c96378fff4c00989caad9a80.svg",
    bgDecorResult: "ef20563d31b1b29159550b8fce4618ea743d9ce9.svg",
    bgDecorLeaderboard: "ef20563d31b1b29159550b8fce4618ea743d9ce9.svg",
    /** Копилка на поле — Figma image 2090010243 (25:172), маска rounded 28×29 */
    playerField: "player-field-masked.png",
    /** assets/Monster — 80×80, Group 2136140168 импульсивные покупки */
    ghostImpulse: MONSTER_BASE + "impulse.png",
    ghostImpulseScare: MONSTER_BASE + "impulse_scare.png",
    /** Group 2136140187 — инфляция */
    ghostInflation: MONSTER_BASE + "inflation.png",
    ghostInflationScare: MONSTER_BASE + "inflation_scare.png",
    /** Group 2136140169 — FOMO */
    ghostFomo: MONSTER_BASE + "fomo.png",
    ghostFomoScare: MONSTER_BASE + "fomo_scare.png",
    /** Монетка — основной объект на поле. */
    pelletCoin: "7cc85e02203da4dade7c18c7254748004b55a994.png",
    /** Проценты. */
    pelletPercent: "5461a78805872f48f1580cf04501583fba98b239.png",
    /** Слиток — редкий объект. */
    pelletLogo: "21d6bfc9e1e9691021c27e978b057a688e8e32d4.png",
    portfolio: "9c7a52cb0aaebeae10b7379074ad3d6c045c76aa.png",
    wallTile: "0f3207ec237fb8b352ca47534b914bc49b5505f4.png",
    wallCorner: "a1aeba078a8e20030c8a55f37f28123e6652d7ef.png",
    wallBlob: "ebf4ec67ce67d26629841cb2df68811acbfa8928.png",
    hudScoreCloud: "909228957421506a7ad5a248c8a5f61cc7a6ae3b.svg",
    hudResultScoreCloud: "3b9cdf664523959652466575484ae0f3481bfb23.svg",
    hudLivesCloud: "ff9809c9d0df86c5a06687dc402742720c2b2da7.svg",
    hudTimerCloud: "0747bba018661685d182a59d88588b54a787e0e0.svg",
    hudScoreDecorL: "ba47078de54d7143dc1bde2652234fe9ba7aa8c5.svg",
    hudScoreDecorR: "54085f72c9f34ea2479243b6fbd1a3260f02d2b2.svg",
    /** Экраны результата — три лица копилки (assets/img) */
    resultPigMiss: "/static/assets/img/pig_failure.png",
    resultPigTop: "/static/assets/img/pig_middle.png",
    resultPigLeader: "/static/assets/img/pig_champ.png",
    /** Сердечко вместо облака на result_top */
    resultHeart: "/static/assets/img/heart.png",
    fieldShadow1: "d0fdcdea6f470b21913662cbbe66c00de9890160.png",
    fieldShadow2: "7326c12827ced98e71e173542da09e8370c6df13.png",
    framePink: "642f0f05fcf47321284cf29a0940a19c2b9524bf.svg",
  };

  const screens = {
    start: {
      scene: "Start",
      next: "Onboarding",
      bgDecor: shared.bgDecorStart,
      layers: [
        { key: "grassB", file: shared.grassB, x: 336, y: 520, w: 480, h: 270, origin: 0.5 },
        { key: "grassC", file: shared.grassC, x: 336, y: 560, w: 420, h: 200, origin: 0.5 },
        { key: "piggy", file: shared.piggy, x: 336, y: 400, w: 220, h: 220, origin: 0.5 },
        { key: "grassA", file: shared.grassA, x: 336, y: 480, w: 500, h: 120, origin: 0.5 },
      ],
      texts: [
        { y: 0.12, lines: ["ИнвестКопилка"], size: 34, color: "#01d701", bold: true },
        { y: 0.18, lines: ["против"], size: 18, color: "#122654" },
        { y: 0.22, lines: ["монстров-расходов"], size: 22, color: "#122654", bold: true },
        { y: 0.62, lines: ["играть"], size: 28, color: "#ff4fa3", bold: true },
      ],
      hint: "Cross (×) — начать",
    },
    onboarding_1: {
      scene: "Onboarding1",
      next: "Onboarding2",
      bgDecor: shared.bgDecorOnb1,
      layers: [
        { key: "grassB", file: shared.grassB, x: 336, y: 530, w: 480, h: 260, origin: 0.5 },
        { key: "piggy", file: shared.piggy, x: 280, y: 420, w: 180, h: 180, origin: 0.5 },
        { key: "coinBig", file: shared.coinBig, x: 420, y: 400, w: 100, h: 100, origin: 0.5 },
        { key: "folder", file: "6d99ba2c1032d9f030f1c9c467ca810c4b25ca62.png", x: 480, y: 460, w: 90, h: 90, origin: 0.5 },
      ],
      texts: [
        { y: 0.14, lines: ["Собирай капитал"], size: 32, color: "#01d701", bold: true },
        {
          y: 0.22,
          lines: [
            "Управляй ИнвестКопилкой на экране,",
            "лови монеты, проценты и активы Сбер Инвестиций.",
          ],
          size: 16,
          color: "#122654",
        },
      ],
      hint: "Cross (×) — далее",
    },
    onboarding_2: {
      scene: "Onboarding2",
      next: "Game",
      bgDecor: shared.bgDecorOnb1,
      layers: [
        { key: "grassB", file: shared.grassB, x: 336, y: 530, w: 480, h: 260, origin: 0.5 },
        { key: "ghost1", file: "0710f8487791e07323ee24a4ad0a940add6c46db.png", x: 300, y: 400, w: 120, h: 120, origin: 0.5 },
        { key: "ghost2", file: "e8935b72eab06e9717bd348739810d7583b36fd8.png", x: 400, y: 420, w: 110, h: 110, origin: 0.5 },
        { key: "piggy", file: shared.piggy, x: 200, y: 430, w: 140, h: 140, origin: 0.5 },
      ],
      texts: [
        { y: 0.14, lines: ["Уворачивайся от препятствий"], size: 30, color: "#01d701", bold: true },
        {
          y: 0.22,
          lines: ["Импульсы, инфляция и FOMO охотятся за копилкой.", "Портфель даёт неуязвимость и x2 очки."],
          size: 16,
          color: "#122654",
        },
      ],
      hint: "Cross (×) — далее",
    },
    onboarding_3: {
      scene: "Onboarding3",
      next: "Game",
      bgDecor: shared.bgDecorOnb1,
      layers: [
        { key: "grassB", file: shared.grassB, x: 336, y: 530, w: 480, h: 260, origin: 0.5 },
        { key: "trophy", file: "c3d49cf3171c3aa91410dfb3aafb8526d3960654.png", x: 340, y: 392, w: 149, h: 168, origin: 0.5 },
        { key: "piggy", file: shared.piggy, x: 220, y: 450, w: 120, h: 120, origin: 0.5 },
      ],
      texts: [
        { y: 0.14, lines: ["Ворвись в топ"], size: 32, color: "#01d701", bold: true },
        { y: 0.22, lines: ["Сохрани результат и попади в таблицу лидеров дня."], size: 16, color: "#122654" },
      ],
      hint: "Cross (×) — играть",
    },
    error: {
      scene: "Error",
      next: "Start",
      bgDecor: shared.bgDecorStart,
      layers: [
        { key: "piggy", file: shared.piggy, x: 336, y: 380, w: 160, h: 160, origin: 0.5 },
        { key: "folder", file: "a323defe5446b134ade9b820d7a5de36e7964b4d.png", x: 420, y: 360, w: 140, h: 140, origin: 0.5 },
      ],
      texts: [
        { y: 0.2, lines: ["Простой"], size: 34, color: "#122654", bold: true },
        {
          y: 0.3,
          lines: ["Идёт ребалансировка портфеля.", "Попробуйте чуть позже."],
          size: 18,
          color: "#122654",
        },
      ],
      hint: "Cross (×) — назад",
    },
    result_score: {
      scene: "Result",
      variant: "miss",
      bgDecor: shared.bgDecorResult,
      layers: [
        { key: "grassB", file: shared.grassB, x: 336, y: 540, w: 460, h: 240, origin: 0.5 },
        { key: "piggy", file: shared.piggy, x: 336, y: 360, w: 180, h: 180, origin: 0.5 },
      ],
      texts: [
        { y: 0.12, lines: ["счёт:"], size: 24, color: "#01d701", bold: true },
        { y: 0.18, lines: ["{score}"], size: 42, color: "#122654", bold: true, dynamic: "score" },
      ],
      hint: "Cross (×) — далее",
    },
    result_top: {
      scene: "Result",
      variant: "top",
      bgDecor: shared.bgDecorResult,
      layers: [
        { key: "grassB", file: shared.grassB, x: 336, y: 540, w: 460, h: 240, origin: 0.5 },
        { key: "piggy", file: shared.piggy, x: 336, y: 360, w: 180, h: 180, origin: 0.5 },
      ],
      texts: [
        { y: 0.12, lines: ["счёт:"], size: 24, color: "#ffffff", bold: true },
        { y: 0.18, lines: ["{score}"], size: 42, color: "#ffffff", bold: true, dynamic: "score" },
      ],
      hint: "◀ ▶ — имя   Cross (×) — сохранить",
    },
    result_record: {
      scene: "Result",
      variant: "leader",
      bgDecor: shared.bgDecorResult,
      layers: [
        { key: "grassB", file: shared.grassB, x: 336, y: 540, w: 460, h: 240, origin: 0.5 },
        { key: "piggy", file: shared.piggy, x: 336, y: 340, w: 200, h: 200, origin: 0.5 },
        { key: "confetti", file: "4cb639982a36e9bf5c2aef2c4dbbbfa2831249b3.png", x: 336, y: 200, w: 300, h: 120, origin: 0.5 },
      ],
      texts: [
        { y: 0.12, lines: ["рекорд"], size: 24, color: "#01d701", bold: true },
        { y: 0.18, lines: ["{score}"], size: 42, color: "#122654", bold: true, dynamic: "score" },
      ],
      hint: "Cross (×) — далее",
    },
    result_stars_0: {
      scene: "ResultStars",
      stars: 0,
      hint: "Cross (×) — в меню",
    },
    result_stars_1: {
      scene: "ResultStars",
      stars: 1,
      hint: "Cross (×) — в меню",
    },
    result_stars_2: {
      scene: "ResultStars",
      stars: 2,
      hint: "Cross (×) — в меню",
    },
    result_stars_3: {
      scene: "ResultStars",
      stars: 3,
      hint: "Cross (×) — в меню",
    },
    leaderboard: {
      scene: "Leaderboard",
      next: "Start",
      bgDecor: shared.bgDecorLeaderboard,
      layers: [
        { key: "grassB", file: shared.grassB, x: 336, y: 560, w: 440, h: 200, origin: 0.5 },
        { key: "boardBg", file: "fda304959692ab205391cde62c578889f6a6e95d.svg", x: 336, y: 380, w: 420, h: 360, origin: 0.5 },
      ],
      texts: [{ y: 0.1, lines: ["Топ дня"], size: 34, color: "#01d701", bold: true }],
      hint: "Cross (×) — в меню",
    },
  };

  function textureKey(file) {
    const base = file.replace(/^.*[/\\]/, "");
    return "fig_" + base.replace(/\.[a-z]+$/i, "");
  }

  function spriteEntry(file, size) {
    return { file, key: textureKey(file), size };
  }

  const gameSprites = {
    player: { ...spriteEntry(shared.playerField, 28), maskW: 28, maskH: 29, figmaRotate: 90 },
    ghost_impulse: spriteEntry(shared.ghostImpulse, GHOST_FIELD_SIZE),
    ghost_impulse_scare: spriteEntry(shared.ghostImpulseScare, GHOST_FIELD_SIZE),
    ghost_inflation: spriteEntry(shared.ghostInflation, GHOST_FIELD_SIZE),
    ghost_inflation_scare: spriteEntry(shared.ghostInflationScare, GHOST_FIELD_SIZE),
    ghost_fomo: spriteEntry(shared.ghostFomo, GHOST_FIELD_SIZE),
    ghost_fomo_scare: spriteEntry(shared.ghostFomoScare, GHOST_FIELD_SIZE),
    pellet_coin: spriteEntry(shared.pelletCoin, 28),
    pellet_percent: spriteEntry(shared.pelletPercent, 24),
    pellet_logo: spriteEntry(shared.pelletLogo, 32),
    portfolio: spriteEntry(shared.portfolio, 38),
    wall_tile: spriteEntry(shared.wallTile, 26),
    wall_corner: spriteEntry(shared.wallCorner, 26),
    wall_blob: spriteEntry(shared.wallBlob, 26),
  };

  const hud = {
    scoreCloud: { file: shared.hudScoreCloud, key: textureKey(shared.hudScoreCloud), w: 200, h: 200, x: 336, y: 600 },
    livesCloud: { file: shared.hudLivesCloud, key: textureKey(shared.hudLivesCloud), w: 200, h: 200, x: 336, y: 28 },
    timerCloud: { file: shared.hudTimerCloud, key: textureKey(shared.hudTimerCloud), w: 63, h: 62, x: 388, y: 31 },
    scoreDecorL: { file: shared.hudScoreDecorL, key: textureKey(shared.hudScoreDecorL), w: 46, h: 57, x: 234, y: 610 },
    scoreDecorR: { file: shared.hudScoreDecorR, key: textureKey(shared.hudScoreDecorR), w: 34, h: 34, x: 400, y: 608 },
  };

  const gradient = { top: 0xecfffe, bottom: 0x9effa8 };

  function collectFiles() {
    const set = new Set(Object.values(shared));
    Object.values(screens).forEach((scr) => {
      if (scr.bgDecor) set.add(scr.bgDecor);
      (scr.layers || []).forEach((l) => set.add(l.file));
    });
    Object.values(gameSprites).forEach((s) => set.add(s.file));
    Object.values(hud).forEach((h) => set.add(h.file));
    return [...set];
  }

  function getTextureEntries() {
    const map = new Map();
    collectFiles().forEach((file) => map.set(textureKey(file), file));
    return [...map.entries()].map(([key, file]) => ({ key, file }));
  }

  window.KopilkaDesign = {
    BASE,
    DESIGN_W,
    DESIGN_H,
    sx,
    sy,
    url,
    shared,
    screens,
    gameSprites,
    hud,
    gradient,
    collectFiles,
    getTextureEntries,
    textureKey,
  };
})();
