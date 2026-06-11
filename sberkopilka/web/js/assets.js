/**
 * Спрайты: Figma PNG (приоритет) + процедурный fallback.
 */
(function () {
  const GHOST_META = {
    impulse: { letter: "!", label: "Импульс", body: 0xff6b8a, dark: 0xe84a6a },
    inflation: { letter: "%", label: "Инфляция", body: 0xb57edc, dark: 0x8e44ad },
    fomo: { letter: "?", label: "FOMO", body: 0xffb347, dark: 0xf39c12 },
  };

  const BRAND = {
    piggy: 0xff6b9d,
    piggyDark: 0xe84a7a,
    piggyHi: 0xffb3c8,
    card: 0x4a9fd8,
    cardDark: 0x2d7ab8,
    coin: 0xffc928,
    coinEdge: 0xe6a800,
    coinHi: 0xfff59d,
    sky: 0x5ecfff,
    pink: 0xff4fa3,
    white: 0xffffff,
    frightened: 0x7ec8f7,
    scoreInk: 0x1a4a6e,
  };

  function designSprites() {
    return window.KopilkaDesign?.gameSprites;
  }

  function ghostTexKey(ghostId) {
    const sp = designSprites()?.[`ghost_${ghostId}`];
    return sp?.key;
  }

  function hasTex(scene, key) {
    return key && scene.textures.exists(key);
  }

  /** Figma 25:172 — image 2090010243: rounded mask 28×29, img 147.53% / 144.64%, offset −23.76% / −17.76% */
  const FIGMA_PLAYER_MASK = {
    maskW: 28,
    maskH: 29,
    imgScaleW: 1.4753,
    imgScaleH: 1.4464,
    imgLeft: -0.2376,
    imgTop: -0.1776,
    bakeScale: 4,
  };

  function bakePlayerTextureWithFigmaMask(scene, srcKey, outKey) {
    if (!hasTex(scene, srcKey)) return null;
    if (hasTex(scene, outKey)) return outKey;

    const src = scene.textures.get(srcKey).getSourceImage();
    const m = FIGMA_PLAYER_MASK;
    const cw = Math.round(m.maskW * m.bakeScale);
    const ch = Math.round(m.maskH * m.bakeScale);
    const canvas = document.createElement("canvas");
    canvas.width = cw;
    canvas.height = ch;
    const ctx = canvas.getContext("2d");
    if (!ctx) return srcKey;

    const imgW = m.maskW * m.imgScaleW * m.bakeScale;
    const imgH = m.maskH * m.imgScaleH * m.bakeScale;
    const dx = m.maskW * m.imgLeft * m.bakeScale;
    const dy = m.maskH * m.imgTop * m.bakeScale;
    ctx.drawImage(src, dx, dy, imgW, imgH);
    ctx.globalCompositeOperation = "destination-in";
    ctx.beginPath();
    ctx.ellipse(cw / 2, ch / 2, cw / 2, ch / 2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = "source-over";

    scene.textures.addCanvas(outKey, canvas);
    return outKey;
  }

  function playerTexKey(scene) {
    const sp = designSprites();
    const base = sp?.player?.key;
    if (!hasTex(scene, base)) return "kopilka_player";
    if (sp?.player?.file === "player-field-masked.png") return base;
    const masked = `${base}_masked`;
    return bakePlayerTextureWithFigmaMask(scene, base, masked) || base;
  }

  function drawPiggyTex(scene) {
    const g = scene.make.graphics({ x: 0, y: 0, add: false });
    const s = 40;
    g.fillStyle(0x000000, 0.12);
    g.fillEllipse(20, 34, 22, 8);
    g.fillStyle(BRAND.piggyDark, 1);
    g.fillEllipse(20, 22, 18, 16);
    g.fillStyle(BRAND.piggy, 1);
    g.fillEllipse(20, 20, 17, 15);
    g.fillStyle(BRAND.piggyHi, 0.9);
    g.fillEllipse(14, 16, 8, 7);
    g.fillStyle(BRAND.piggyDark, 1);
    g.fillEllipse(28, 22, 7, 6);
    g.fillStyle(BRAND.piggyHi, 1);
    g.fillCircle(12, 12, 4);
    g.fillCircle(26, 11, 4);
    g.fillStyle(0x333333, 1);
    g.fillCircle(13, 12, 1.5);
    g.fillCircle(27, 11, 1.5);
    g.fillStyle(BRAND.piggyDark, 1);
    g.fillRect(17, 8, 8, 5);
    g.fillStyle(BRAND.piggy, 1);
    g.fillRect(18, 9, 6, 3);
    g.fillStyle(BRAND.coin, 1);
    g.fillCircle(21, 6, 2.5);
    g.lineStyle(2, BRAND.white, 0.8);
    g.strokeEllipse(20, 20, 17, 15);
    g.generateTexture("kopilka_player", s, s);
    g.destroy();
  }

  function drawGhostTex(scene, id, meta) {
    const g = scene.make.graphics({ x: 0, y: 0, add: false });
    const c = 18;
    g.fillStyle(meta.dark, 0.3);
    g.fillEllipse(c, c + 4, 24, 18);
    g.fillStyle(meta.body, 1);
    g.fillRoundedRect(c - 11, c - 8, 22, 20, 10);
    const waveY = c + 10;
    for (let i = 0; i < 4; i++) {
      g.fillCircle(c - 9 + i * 6, waveY + (i % 2 ? 2 : 0), 5);
    }
    g.fillStyle(BRAND.white, 1);
    g.fillCircle(c - 5, c - 2, 4);
    g.fillCircle(c + 5, c - 2, 4);
    g.fillStyle(0x222222, 1);
    g.fillCircle(c - 5, c - 1, 2);
    g.fillCircle(c + 5, c - 1, 2);
    g.generateTexture(`ghost_${id}`, c * 2, c * 2 + 6);
    g.destroy();
  }

  function drawCoinTex(scene) {
    const g = scene.make.graphics({ x: 0, y: 0, add: false });
    const c = 8;
    g.fillStyle(0x000000, 0.15);
    g.fillCircle(c + 0.5, c + 1, 5);
    g.fillStyle(BRAND.coin, 1);
    g.fillCircle(c, c, 5);
    g.lineStyle(1.5, BRAND.coinEdge, 1);
    g.strokeCircle(c, c, 5);
    g.fillStyle(BRAND.coinHi, 0.9);
    g.fillCircle(c - 1.5, c - 1.5, 2);
    g.generateTexture("pellet_coin", c * 2, c * 2);
    g.destroy();
  }

  function drawPercentTex(scene) {
    const g = scene.make.graphics({ x: 0, y: 0, add: false });
    const c = 10;
    g.fillStyle(BRAND.sky, 1);
    g.fillCircle(c, c, 8);
    g.lineStyle(1.5, 0x2d7ab8, 1);
    g.strokeCircle(c, c, 8);
    g.fillStyle(BRAND.white, 1);
    g.fillRect(c - 4, c - 1, 3, 2);
    g.fillRect(c + 1, c + 2, 3, 2);
    g.generateTexture("pellet_percent", c * 2, c * 2);
    g.destroy();
  }

  function drawLogoTex(scene) {
    const g = scene.make.graphics({ x: 0, y: 0, add: false });
    const c = 11;
    g.fillStyle(BRAND.pink, 1);
    g.fillCircle(c, c, 9);
    g.fillStyle(BRAND.coin, 1);
    g.fillCircle(c, c, 5);
    g.fillStyle(BRAND.white, 0.7);
    g.fillCircle(c - 2, c - 2, 2);
    g.generateTexture("pellet_logo", c * 2, c * 2);
    g.destroy();
  }

  function drawPortfolioTex(scene) {
    const g = scene.make.graphics({ x: 0, y: 0, add: false });
    const w = 44;
    const h = 44;
    g.fillStyle(0x000000, 0.1);
    g.fillRoundedRect(14, 12, 22, 26, 4);
    g.fillStyle(BRAND.cardDark, 1);
    g.fillRoundedRect(10, 14, 22, 26, 5);
    g.fillStyle(BRAND.card, 1);
    g.fillRoundedRect(14, 10, 22, 26, 5);
    g.fillStyle(BRAND.white, 0.95);
    g.fillCircle(24, 20, 7);
    g.lineStyle(2, BRAND.cardDark, 1);
    g.strokeCircle(24, 20, 7);
    g.lineStyle(2, BRAND.cardDark, 1);
    g.beginPath();
    g.moveTo(24, 20);
    g.lineTo(24, 16);
    g.lineTo(27, 18);
    g.strokePath();
    g.lineStyle(2, BRAND.white, 0.8);
    g.strokeRoundedRect(14, 10, 22, 26, 5);
    g.generateTexture("kopilka_portfolio", w, h);
    g.destroy();
  }

  function register(scene) {
    const sp = designSprites();
    if (!hasTex(scene, sp?.player?.key) && !scene.textures.exists("kopilka_player")) drawPiggyTex(scene);
    if (hasTex(scene, sp?.player?.key)) playerTexKey(scene);
    if (!hasTex(scene, sp?.pellet_coin?.key)) drawCoinTex(scene);
    if (!hasTex(scene, sp?.pellet_percent?.key)) drawPercentTex(scene);
    if (!hasTex(scene, sp?.pellet_logo?.key)) drawLogoTex(scene);
    if (!hasTex(scene, sp?.portfolio?.key)) drawPortfolioTex(scene);
    Object.entries(GHOST_META).forEach(([id, meta]) => {
      if (!hasTex(scene, ghostTexKey(id))) drawGhostTex(scene, id, meta);
    });
  }

  function resolveKey(scene, kind, ghostId) {
    const sp = designSprites();
    if (kind === "player") {
      return playerTexKey(scene);
    }
    if (kind === "ghost") {
      const k = ghostTexKey(ghostId);
      return hasTex(scene, k) ? k : `ghost_${ghostId}`;
    }
    if (kind === "pellet") {
      const map = { coin: sp?.pellet_coin, percent: sp?.pellet_percent, logo: sp?.pellet_logo };
      const entry = map[ghostId];
      const k = entry?.key;
      const fallback = ghostId === "percent" ? "pellet_percent" : ghostId === "logo" ? "pellet_logo" : "pellet_coin";
      return hasTex(scene, k) ? k : fallback;
    }
    if (kind === "portfolio") {
      const k = sp?.portfolio?.key;
      return hasTex(scene, k) ? k : "kopilka_portfolio";
    }
    return null;
  }

  function displaySize(kind, ghostId, compact) {
    const sp = designSprites();
    if (kind === "player") return sp?.player?.size ?? 28;
    if (kind === "ghost") return (sp?.[`ghost_${ghostId}`]?.size ?? (compact ? 36 : 40));
    if (kind === "pellet") {
      const map = { coin: sp?.pellet_coin, percent: sp?.pellet_percent, logo: sp?.pellet_logo };
      return map[ghostId]?.size ?? (ghostId === "coin" ? 28 : ghostId === "percent" ? 24 : 10);
    }
    if (kind === "portfolio") return sp?.portfolio?.size ?? 34;
    return 28;
  }

  /** Figma rotate-90 (25:172) + разворот на 180° — лицом вперёд по ходу */
  const PLAYER_FACE_OFFSET = 270;

  function playerAngleFromDirection(dir, offset = PLAYER_FACE_OFFSET) {
    if (!dir?.length()) return offset;
    return offset + Phaser.Math.RadToDeg(Math.atan2(dir.y, dir.x));
  }

  function createPlayer(scene, x, y) {
    window.__lastScene = scene;
    const key = resolveKey(scene, "player");
    const sp = designSprites()?.player;
    const size = displaySize("player");
    const aspect = sp?.maskH && sp?.maskW ? sp.maskH / sp.maskW : 1;
    const c = scene.add.container(x, y);
    const body = scene.add.image(0, 0, key);
    body.setDisplaySize(size, size * aspect);
    body.setBlendMode(Phaser.BlendModes.NORMAL);
    c.add(body);
    c.setAngle(PLAYER_FACE_OFFSET);
    c.setDepth(20);
    c.setData("body", body);
    return c;
  }

  function createGhost(scene, x, y, ghostId, compact) {
    window.__lastScene = scene;
    const meta = GHOST_META[ghostId] || GHOST_META.impulse;
    const key = resolveKey(scene, "ghost", ghostId);
    const size = displaySize("ghost", ghostId, compact);
    const c = scene.add.container(x, y);
    const body = scene.add.image(0, 0, key);
    body.setDisplaySize(size, size);
    const useLetter = !hasTex(scene, ghostTexKey(ghostId));
    const parts = [body];
    if (useLetter) {
      const letter = scene.add
        .text(0, compact ? 0 : -1, meta.letter, {
          fontSize: compact ? "11px" : "13px",
          color: "#ffffff",
          fontStyle: "bold",
          stroke: compact ? "#1a4a6e" : "#000000",
          strokeThickness: 2,
        })
        .setOrigin(0.5);
      parts.push(letter);
    }
    c.add(parts);
    c.setDepth(15);
    c.setData("ghostId", ghostId);
    c.setData("body", body);
    return c;
  }

  function createPellet(scene, x, y, type) {
    window.__lastScene = scene;
    const key = resolveKey(scene, "pellet", type);
    const size = displaySize("pellet", type);
    const img = scene.add.image(x, y, key);
    img.setDisplaySize(size, size);
    img.setDepth(4);
    return img;
  }

  function createPortfolio(scene, x, y) {
    window.__lastScene = scene;
    const key = resolveKey(scene, "portfolio");
    const size = displaySize("portfolio");
    const c = scene.add.container(x, y);
    const img = scene.add.image(0, 0, key);
    img.setDisplaySize(size, size);
    c.add(img);
    c.setDepth(6);
    return c;
  }

  function setGhostFrightened(sprite, frightened) {
    const body = sprite?.getData?.("body") || sprite?.list?.[0];
    if (!body) return;
    body.setTint(frightened ? BRAND.frightened : 0xffffff);
  }

  function wallTextureKey(scene) {
    const k = designSprites()?.wall_blob?.key;
    return hasTex(scene, k) ? k : null;
  }

  window.KopilkaAssets = {
    register,
    createPlayer,
    createGhost,
    createPellet,
    createPortfolio,
    setGhostFrightened,
    wallTextureKey,
    playerAngleFromDirection,
    PLAYER_FACE_OFFSET,
    GHOST_META,
    BRAND,
  };
})();
