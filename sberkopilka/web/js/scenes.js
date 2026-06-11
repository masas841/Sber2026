(function () {
  "use strict";

  if (!window.KopilkaMaze) {
    window.__kopilkaLoadError = "Не загружен maze.js";
    return;
  }
  if (!window.KopilkaAssets) {
    window.__kopilkaLoadError = "Не загружен assets.js";
    return;
  }
  if (!window.KopilkaBoard) {
    window.__kopilkaLoadError = "Не загружен board.js";
    return;
  }
  if (!window.KopilkaDesign) {
    window.__kopilkaLoadError = "Не загружен design-manifest.js";
    return;
  }
  if (!window.KopilkaFigmaUi) {
    window.__kopilkaLoadError = "Не загружен figma-ui.js";
    return;
  }
  if (typeof Phaser === "undefined") {
    window.__kopilkaLoadError = "Не загружен Phaser";
    return;
  }

  const { TILE, TILE_W, TILE_H, MAZE, PORTFOLIO_DURATION_MS } = window.KopilkaMaze;
  const KopilkaAssets = window.KopilkaAssets;
  const KopilkaBoard = window.KopilkaBoard;
  const KopilkaDesign = window.KopilkaDesign;
  const KopilkaFigmaUi = window.KopilkaFigmaUi;

  /** Плавное движение: пиксели/сек, поворот у центра клетки */
  const PLAYER_SPEED = TILE * 5.6;
  const GHOST_SPEED = TILE * 3.2;
  const GHOST_SPEED_MOD = { impulse: 0.9, inflation: 0.75, fomo: 1.0 };
  const TURN_SNAP = 6;
  const HIT_RADIUS = TILE * 0.38;
  const GHOST_EATEN_RESPAWN_MS = 5000;

const COLORS = {
  wall: 0x0d8522,
  wallEdge: 0x21a038,
  bg: 0x0a1210,
  coin: 0xffd54f,
  percent: 0x5ecfff,
  logo: 0xff4fa3,
  player: 0xa6ff00,
  impulse: 0xff6b6b,
  inflation: 0x9b59b6,
  fomo: 0xff9500,
  frightened: 0x4fc3f7,
};

const GHOST_TYPES = [
  { id: "impulse", label: "Импульс", color: COLORS.impulse, mode: "random" },
  { id: "inflation", label: "Инфляция", color: COLORS.inflation, mode: "chase_slow" },
  { id: "fomo", label: "FOMO", color: COLORS.fomo, mode: "chase_fast" },
];

/** Figma 25:141 → fomo, 25:163 → inflation, 25:151 → impulse */
const GHOST_SPAWN_IDS = ["fomo", "inflation", "impulse"];

const NICKNAMES = ["Гость", "Инвестор", "Копилка", "Пилот", "Сбер"];

function linkGamepad(scene) {
  const joy = scene.registry?.get("joystick");
  if (!joy || !scene.input?.gamepad) return joy;
  const pad = scene.input.gamepad.pad1;
  if (pad) joy.setPhaserPad(pad);
  return joy;
}

class BootScene extends Phaser.Scene {
  constructor() {
    super("Boot");
  }

  preload() {
    KopilkaFigmaUi.preload(this);
    if (window.KopilkaFigmaBoard) {
      this.load.json(window.KopilkaFigmaBoard.LAYOUT_KEY, "/static/assets/figma/layouts/game-field.json");
    }
  }

  create() {
    const defaults = { game_duration_sec: 60, joystick_deadzone: 0.35 };
    this.registry.set("cfg", defaults);

    const joy = window.kopilkaJoystick || new JoystickInput(defaults.joystick_deadzone);
    window.kopilkaJoystick = joy;
    this.registry.set("joystick", joy);

    KopilkaFigmaUi.prefetchScreen("game-bg");
    this.scene.start("Start");

    const ac = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timer = ac ? setTimeout(() => ac.abort(), 3000) : null;
    fetch("/api/config", ac ? { signal: ac.signal } : {})
      .then((res) => (res.ok ? res.json() : defaults))
      .then((cfg) => {
        this.registry.set("cfg", { ...defaults, ...cfg });
        if (cfg.joystick_deadzone != null) joy.setDeadzone(cfg.joystick_deadzone);
      })
      .catch(() => {})
      .finally(() => {
        if (timer) clearTimeout(timer);
      });
  }
}

const ONBOARDING_SLIDES = ["onboarding_1", "onboarding_2", "onboarding_3"];
const ONBOARDING_AUTO_MS = 5000;

class FigmaFlowScene extends Phaser.Scene {
  constructor(key, screenId) {
    super(key);
    this.screenId = screenId;
  }

  create() {
    const spec = KopilkaDesign.screens[this.screenId];
    KopilkaFigmaUi.drawGradientBg(this);
    this.ui = KopilkaFigmaUi.buildStaticScreen(this, this.screenId);
    this.joy = linkGamepad(this) || this.registry.get("joystick");
    this.cursors = this.input.keyboard.createCursorKeys();
    this.keys = this.input.keyboard.addKeys("ENTER,SPACE");
    this.nextScene = spec?.next || "Start";
    this._navigating = false;

    if (this.screenId === "start") {
      this.loadBestScore();
    }
  }

  goNext() {
    if (this._navigating) return;
    this._navigating = true;
    this.scene.start(this.nextScene);
  }

  async loadBestScore() {
    try {
      const res = await fetch("/api/leaderboard?limit=1");
      if (!res.ok) return;
      const data = await res.json();
      if (data.entries?.length) {
        this.registry.set("bestScore", data.entries[0].score);
      }
    } catch {
      /* offline */
    }
  }

  update() {
    if (this.joy) {
      this.joy.update();
      if (this.joy.consumeOptionsPress() && this.screenId === "start") {
        this.registry.remove("lastPlayerName");
        this.registry.remove("lbHighlightPlayer");
        this.scene.start("Leaderboard");
        return;
      }
      if (this.joy.consumeConfirmPress()) {
        this.goNext();
        return;
      }
    }

    if (
      Phaser.Input.Keyboard.JustDown(this.keys.ENTER) ||
      Phaser.Input.Keyboard.JustDown(this.keys.SPACE)
    ) {
      this.goNext();
    }
  }
}

class StartScene extends FigmaFlowScene {
  constructor() {
    super("Start", "start");
  }

  async goNext() {
    if (this._navigating) return;
    this._navigating = true;
    const root = document.getElementById("figma-overlay");
    const frame = root?.querySelector(".figma-overlay__frame--active");
    if (window.KopilkaFigmaAnim?.runOnFrame && frame) {
      await KopilkaFigmaAnim.runOnFrame(frame, "start-exit");
    }
    this.scene.start(this.nextScene);
  }
}

class OnboardingScene extends Phaser.Scene {
  constructor() {
    super("Onboarding");
    this.slideIndex = 0;
    this._navigating = false;
    this._transitioning = false;
  }

  create() {
    this._navigating = false;
    this.slideIndex = 0;
    KopilkaFigmaUi.drawGradientBg(this);
    this.joy = linkGamepad(this) || this.registry.get("joystick");
    this.cursors = this.input.keyboard.createCursorKeys();
    this.keys = this.input.keyboard.addKeys("ENTER,SPACE");
    this.ui = KopilkaFigmaUi.buildStaticScreen(this, ONBOARDING_SLIDES[0]);
    if (ONBOARDING_SLIDES.length > 1) {
      KopilkaFigmaUi.prefetchScreen(ONBOARDING_SLIDES[1]);
    }
    this.scheduleAuto();
  }

  shutdown() {
    this.clearAuto();
  }

  clearAuto() {
    if (this._autoId) {
      clearTimeout(this._autoId);
      this._autoId = null;
    }
  }

  scheduleAuto() {
    this.clearAuto();
    if (this.slideIndex >= ONBOARDING_SLIDES.length - 1) return;
    const nextId = ONBOARDING_SLIDES[this.slideIndex + 1];
    KopilkaFigmaUi.prefetchScreen(nextId);
    this._autoId = window.setTimeout(() => this.advance(), ONBOARDING_AUTO_MS);
  }

  async showSlide(index) {
    this.slideIndex = index;
    const screenId = ONBOARDING_SLIDES[index];
    const root = this.ui?.root || document.getElementById("figma-overlay");
    await KopilkaFigmaUi.crossfadeTo(root, screenId);
    if (index < ONBOARDING_SLIDES.length - 1) {
      KopilkaFigmaUi.prefetchScreen(ONBOARDING_SLIDES[index + 1]);
    }
  }

  async advance() {
    if (this._navigating || this._transitioning || !this.scene.isActive("Onboarding")) return;
    this.clearAuto();

    if (this.slideIndex < ONBOARDING_SLIDES.length - 1) {
      this._transitioning = true;
      try {
        await this.showSlide(this.slideIndex + 1);
      } finally {
        this._transitioning = false;
      }
      this.scheduleAuto();
      return;
    }

    this._navigating = true;
    await KopilkaFigmaUi.dissolveStaticScreen();
    this.scene.start("Game");
  }

  update() {
    if (this._navigating || this._transitioning) return;

    if (this.joy) {
      this.joy.update();
      if (this.joy.consumeConfirmPress()) {
        this.advance();
        return;
      }
    }

    if (
      Phaser.Input.Keyboard.JustDown(this.keys.ENTER) ||
      Phaser.Input.Keyboard.JustDown(this.keys.SPACE)
    ) {
      this.advance();
    }
  }
}

class ErrorScene extends FigmaFlowScene {
  constructor() {
    super("Error", "error");
  }
}

class GameScene extends Phaser.Scene {
  constructor() {
    super("Game");
  }

  create() {
    KopilkaFigmaUi.hideStaticOverlay();
    KopilkaFigmaUi.showGameLayer().then(() => {
      if (this._ending) return;
      KopilkaFigmaUi.updateGameScore(this.score);
      KopilkaFigmaUi.updateGameLives(this.lives);
      KopilkaFigmaUi.updateGameTime(this.timeLeft);
      KopilkaFigmaUi.refreshPhaserLayout?.();
      this.syncPlayerSprite();
      this.pellets.forEach((p) => {
        const sprite = this.pelletGroup?.getChildren?.().find((c) => c.getData("pelletId") === p.id);
        if (sprite) {
          const w = this.pelletWorld(p);
          sprite.setPosition(w.x, w.y);
        }
      });
    });
    this.cameras.main.setBackgroundColor("rgba(0,0,0,0)");

    const cfg = this.registry.get("cfg") || { game_duration_sec: 60 };
    this.durationSec = cfg.game_duration_sec || 60;
    this.timeLeft = this.durationSec;
    this.score = 0;
    this.lives = 3;
    this.portfolioUntil = 0;
    this.respawnUntil = 0;
    this._respawnTimer = null;
    this._ending = false;
    this.scoreMultiplier = 1;
    this.nextDir = new Phaser.Math.Vector2(0, 0);
    this.currentDir = new Phaser.Math.Vector2(0, 0);
    this.playerGrid = { ...MAZE.playerStart };
    this._lastPelletGx = this.playerGrid.x;
    this._lastPelletGy = this.playerGrid.y;
    this.wallSet = new Set(MAZE.walls.map((w) => `${w.x},${w.y}`));
    this.pellets = new Map();
    const fieldPellets = window.KopilkaMaze.generateRandomPellets();
    fieldPellets.forEach((p) => this.pellets.set(p.id, { ...p }));

    const fieldMeta = window.KopilkaMaze?.FIGMA_FIELD || { x: 107.52, y: 74.39, tileW: TILE_W, tileH: TILE_H };
    this.offsetX = fieldMeta.x;
    this.offsetY = fieldMeta.y;
    this.tileW = fieldMeta.tileW ?? fieldMeta.tile ?? TILE_W ?? TILE;
    this.tileH = fieldMeta.tileH ?? fieldMeta.tile ?? TILE_H ?? TILE;

    if (KopilkaAssets) KopilkaAssets.register(this);

    this.pelletGroup = this.add.group();
    this.pellets.forEach((p) => this.spawnPelletSprite(p));

    this.player = KopilkaAssets
      ? KopilkaAssets.createPlayer(this, 0, 0)
      : this.add.circle(0, 0, TILE * 0.35, COLORS.player);
    this.syncPlayerSprite();

    this.ghosts = MAZE.ghostSpawns.map((sp, i) => {
      const ghostId = sp.id || GHOST_SPAWN_IDS[i] || GHOST_TYPES[0].id;
      const gt = GHOST_TYPES.find((g) => g.id === ghostId) || GHOST_TYPES[0];
      const gw = this.entityWorld(sp);
      const sprite = KopilkaAssets
        ? KopilkaAssets.createGhost(this, gw.x, gw.y, gt.id, true)
        : this.add.circle(gw.x, gw.y, TILE * 0.32, gt.color);
      return {
        ...gt,
        spawnGrid: { x: sp.x, y: sp.y },
        spawnWorld: this.entityWorld(sp),
        grid: { x: sp.x, y: sp.y },
        dir: new Phaser.Math.Vector2(-1, 0),
        sprite,
        frightenedUntil: 0,
        eaten: false,
      };
    });

    this.portfolioSprite = null;
    if (MAZE.portfolioTile) {
      const pt = MAZE.portfolioTile;
      const pw2 = this.entityWorld(pt);
      this.portfolioSprite = KopilkaAssets
        ? KopilkaAssets.createPortfolio(this, pw2.x, pw2.y)
        : this.add.star(pw2.x, pw2.y, 5, TILE * 0.15, TILE * 0.35, 0x21a038);
    }

    const hud = KopilkaFigmaUi.createGameHudProxy(this.score, this.lives, this.timeLeft);
    this.hudScoreValue = hud.scoreValue;
    this.hudTime = hud.timeText;
    this.hudLives = hud.livesText;
    this.hudMode = hud.modeText;

    this.cursors = this.input.keyboard.createCursorKeys();
    this.joy = this.registry.get("joystick") || window.kopilkaJoystick;
    if (this.joy && this.input.gamepad?.pad1) this.joy.setPhaserPad(this.input.gamepad.pad1);

    this.input.keyboard.enabled = true;
    if (this.input.keyboard) this.input.keyboard.clearCaptures();
    if (this.game.canvas) {
      this.game.canvas.setAttribute("tabindex", "1");
      this.game.canvas.focus();
    }

    this.clockTimer = this.time.addEvent({
      delay: 1000,
      loop: true,
      callback: () => this.tickClock(),
    });

    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      this._ending = true;
      if (this._respawnTimer) this._respawnTimer.remove();
      this.ghosts?.forEach((g) => {
        if (g._eatenRespawnTimer) g._eatenRespawnTimer.remove(false);
      });
      this.stopPortfolioBlink();
      KopilkaFigmaUi.hideGameLayer();
    });
  }

  isRespawning() {
    return this.respawnUntil > 0 && this.time.now < this.respawnUntil;
  }

  tickClock() {
    if (this._ending) return;
    this.timeLeft -= 1;
    this.hudTime.setText(`${Math.max(0, this.timeLeft)} с`);
    if (this.timeLeft <= 0) {
      this.hudMode.setText("Время вышло!");
      if (this.clockTimer) {
        this.clockTimer.remove(false);
        this.clockTimer = null;
      }
      this.endGame();
    }
  }

  entityWorld(ent) {
    if (ent?.x != null && ent?.y != null) return this.gridToWorld(ent.x, ent.y);
    if (ent?.wx != null && ent?.wy != null) return { x: ent.wx, y: ent.wy };
    return { x: 0, y: 0 };
  }

  pelletWorld(p) {
    if (p?.x != null && p?.y != null) return this.gridToWorld(p.x, p.y);
    if (p?.wx != null && p?.wy != null) return { x: p.wx, y: p.wy };
    return { x: 0, y: 0 };
  }

  spawnPelletSprite(p) {
    const w = this.pelletWorld(p);
    const sprite = KopilkaAssets
      ? KopilkaAssets.createPellet(this, w.x, w.y, p.type)
      : this.add.circle(w.x, w.y, 5, COLORS.coin);
    sprite.setDepth(4);
    sprite.setData("pelletId", p.id);
    this.pelletGroup.add(sprite);
  }

  isWall(gx, gy) {
    if (gx < 0 || gy < 0 || gx >= MAZE.cols || gy >= MAZE.rows) return true;
    return this.wallSet.has(`${gx},${gy}`);
  }

  gridToWorld(gx, gy) {
    return {
      x: this.offsetX + gx * this.tileW + this.tileW / 2,
      y: this.offsetY + gy * this.tileH + this.tileH / 2,
    };
  }

  update(_time, delta) {
    if (this._ending) return;
    linkGamepad(this);
    this.joy?.update();

    if (this.respawnUntil > 0 && this.time.now >= this.respawnUntil) {
      this.finishRespawn();
    } else if (this.isRespawning()) {
      const left = Math.ceil((this.respawnUntil - this.time.now) / 1000);
      this.hudMode.setText(`Пауза ${left} с…`);
      return;
    }

    this.updatePlayer(delta);
    this.updateGhosts(delta);
  }

  worldToGrid(wx, wy) {
    return {
      x: Phaser.Math.Clamp(Math.floor((wx - this.offsetX) / this.tileW), 0, MAZE.cols - 1),
      y: Phaser.Math.Clamp(Math.floor((wy - this.offsetY) / this.tileH), 0, MAZE.rows - 1),
    };
  }

  tileCenterAt(wx, wy) {
    const g = this.worldToGrid(wx, wy);
    return { grid: g, center: this.gridToWorld(g.x, g.y) };
  }

  isAtTileCenter(wx, wy, eps = TURN_SNAP) {
    const { center } = this.tileCenterAt(wx, wy);
    return Math.abs(wx - center.x) <= eps && Math.abs(wy - center.y) <= eps;
  }

  alignToCorridor(sprite, dir) {
    const { center } = this.tileCenterAt(sprite.x, sprite.y);
    if (dir.x) sprite.y = center.y;
    if (dir.y) sprite.x = center.x;
  }

  canMoveFromSprite(sprite, dir) {
    const { grid } = this.tileCenterAt(sprite.x, sprite.y);
    return this.canMove(grid.x, grid.y, dir);
  }

  canAdvance(sprite, dir, dist) {
    if (!dir.length() || dist <= 0) return false;
    const cell = this.worldToGrid(sprite.x, sprite.y);
    return this.canMove(cell.x, cell.y, dir);
  }

  applyPelletAtGrid(gx, gy) {
    if (gx === this._lastPelletGx && gy === this._lastPelletGy) return;
    this._lastPelletGx = gx;
    this._lastPelletGy = gy;
    this.playerGrid = { x: gx, y: gy };
    this.collectAt(gx, gy);
  }

  stepSprite(sprite, dir, speed, dt) {
    if (!dir.length()) return dir;
    const step = speed * (dt / 1000);
    if (!this.canAdvance(sprite, dir, step)) {
      const { center } = this.tileCenterAt(sprite.x, sprite.y);
      sprite.x = center.x;
      sprite.y = center.y;
      return new Phaser.Math.Vector2(0, 0);
    }
    sprite.x += dir.x * step;
    sprite.y += dir.y * step;
    return dir;
  }

  readDirection() {
    let dir = this.joy?.direction;
    if (!dir) {
      if (this.cursors.left.isDown) dir = "left";
      else if (this.cursors.right.isDown) dir = "right";
      else if (this.cursors.up.isDown) dir = "up";
      else if (this.cursors.down.isDown) dir = "down";
    }
    if (!dir) return;
    const map = {
      left: new Phaser.Math.Vector2(-1, 0),
      right: new Phaser.Math.Vector2(1, 0),
      up: new Phaser.Math.Vector2(0, -1),
      down: new Phaser.Math.Vector2(0, 1),
    };
    this.nextDir = map[dir];
    this.syncPlayerFacing();
  }

  canMove(gx, gy, dir) {
    return !this.isWall(gx + dir.x, gy + dir.y);
  }

  syncPlayerSprite() {
    const w = this.entityWorld(MAZE.playerStart);
    this.player.x = w.x;
    this.player.y = w.y;
    this.syncPlayerFacing();
  }

  syncPlayerFacing() {
    if (!this.player?.setAngle) return;
    const dir = this.currentDir?.length()
      ? this.currentDir
      : this.nextDir?.length()
        ? this.nextDir
        : null;
    if (!dir?.length()) return;
    const angle = KopilkaAssets?.playerAngleFromDirection?.(dir)
      ?? KopilkaAssets?.PLAYER_FACE_OFFSET
      ?? 270;
    this.player.setAngle(angle);
  }

  updatePlayer(dt) {
    this.readDirection();

    if (!this.isAtTileCenter(this.player.x, this.player.y) && !this.currentDir.length()) {
      const { center } = this.tileCenterAt(this.player.x, this.player.y);
      const snap = Math.min(4, PLAYER_SPEED * (dt / 1000));
      if (Math.abs(this.player.x - center.x) > 0.5) {
        this.player.x += Math.sign(center.x - this.player.x) * Math.min(snap, Math.abs(this.player.x - center.x));
      }
      if (Math.abs(this.player.y - center.y) > 0.5) {
        this.player.y += Math.sign(center.y - this.player.y) * Math.min(snap, Math.abs(this.player.y - center.y));
      }
    }

    if (this.isAtTileCenter(this.player.x, this.player.y)) {
      this.alignToCorridor(this.player, this.currentDir);
      if (this.nextDir.length() && this.canMoveFromSprite(this.player, this.nextDir)) {
        this.currentDir = this.nextDir.clone();
        this.alignToCorridor(this.player, this.currentDir);
        this.syncPlayerFacing();
      } else if (
        this.currentDir.length() &&
        !this.canMoveFromSprite(this.player, this.currentDir)
      ) {
        this.currentDir.set(0, 0);
      }
    }

    if (this.currentDir.length()) {
      this.currentDir = this.stepSprite(this.player, this.currentDir, PLAYER_SPEED, dt);
      this.syncPlayerFacing();
    }

    const g = this.worldToGrid(this.player.x, this.player.y);
    this.playerGrid = { x: g.x, y: g.y };
    this.collectNearbyPellets();
    this.checkGhostCollision();
  }

  addScore(base) {
    const mult = this.isPortfolioActive() ? 2 : 1;
    this.score += base * mult;
    if (this.hudScoreValue) {
      this.hudScoreValue.setText(String(this.score).padStart(3, "0"));
    }
  }

  isPortfolioActive() {
    return this.time.now < this.portfolioUntil;
  }

  collectPellet(id) {
    const p = this.pellets.get(id);
    if (!p) return;
    this.pellets.delete(id);
    this.addScore(p.points);
    this.pelletGroup.getChildren().forEach((child) => {
      if (child.getData("pelletId") === id) child.destroy();
    });
  }

  collectAt(gx, gy) {
    const legacyId = `${gx},${gy}`;
    if (this.pellets.has(legacyId)) {
      this.collectPellet(legacyId);
      return;
    }
    this.collectNearbyPellets();
  }

  collectNearbyPellets() {
    const px = this.player.x;
    const py = this.player.y;
    for (const [id, p] of this.pellets) {
      const pw = this.pelletWorld(p);
      if (Phaser.Math.Distance.Between(px, py, pw.x, pw.y) < HIT_RADIUS + 4) {
        this.collectPellet(id);
        break;
      }
    }
  }

  startPortfolioBlink() {
    this.stopPortfolioBlink();
    this._portfolioBlinkOn = true;
    this._portfolioBlinkEvt = this.time.addEvent({
      delay: 160,
      loop: true,
      callback: () => {
        if (!this.isPortfolioActive()) {
          this.stopPortfolioBlink();
          return;
        }
        this._portfolioBlinkOn = !this._portfolioBlinkOn;
        this.player?.setAlpha?.(this._portfolioBlinkOn ? 1 : 0.42);
      },
    });
  }

  stopPortfolioBlink() {
    this._portfolioBlinkEvt?.remove(false);
    this._portfolioBlinkEvt = null;
    if (this.player?.setAlpha) this.player.setAlpha(1);
  }

  activatePortfolio() {
    this.portfolioUntil = this.time.now + PORTFOLIO_DURATION_MS;
    this.scoreMultiplier = 2;
    this.hudMode.setText("Портфель: x2 — ешь всех монстров!");
    if (this.portfolioSprite) this.portfolioSprite.setVisible(false);
    this.ghosts.forEach((g) => {
      if (!g.eaten) {
        g.frightenedUntil = this.portfolioUntil;
        if (KopilkaAssets) KopilkaAssets.setGhostFrightened(g.sprite, true);
      }
    });
    this.startPortfolioBlink();
    this.time.delayedCall(PORTFOLIO_DURATION_MS, () => {
      if (this._ending) return;
      this.hudMode.setText("");
      this.stopPortfolioBlink();
      this.ghosts.forEach((g) => {
        if (!g.eaten && KopilkaAssets) KopilkaAssets.setGhostFrightened(g.sprite, false);
      });
    });
  }

  ghostChoices(g) {
    const { grid } = this.tileCenterAt(g.sprite.x, g.sprite.y);
    const dirs = [
      new Phaser.Math.Vector2(1, 0),
      new Phaser.Math.Vector2(-1, 0),
      new Phaser.Math.Vector2(0, 1),
      new Phaser.Math.Vector2(0, -1),
    ].filter((d) => this.canMove(grid.x, grid.y, d));

    if (dirs.length <= 1) return dirs;
    return dirs.filter((d) => !(d.x === -g.dir.x && d.y === -g.dir.y));
  }

  chooseGhostDir(g) {
    const choices = this.ghostChoices(g);
    if (!choices.length) return new Phaser.Math.Vector2(0, 0);

    const { grid } = this.tileCenterAt(g.sprite.x, g.sprite.y);
    let pick = choices[Phaser.Math.Between(0, choices.length - 1)];
    const dist =
      Math.abs(this.playerGrid.x - grid.x) + Math.abs(this.playerGrid.y - grid.y);

    if (g.mode === "chase_fast" && dist < 12 && Math.random() < 0.82) {
      const ranked = [...choices].sort((a, b) => {
        const da =
          Math.abs(grid.x + a.x - this.playerGrid.x) + Math.abs(grid.y + a.y - this.playerGrid.y);
        const db =
          Math.abs(grid.x + b.x - this.playerGrid.x) + Math.abs(grid.y + b.y - this.playerGrid.y);
        return da - db;
      });
      pick = ranked[0];
    } else if (g.mode === "chase_slow" && dist < 7) {
      const ranked = [...choices].sort((a, b) => {
        const da =
          Math.abs(grid.x + a.x - this.playerGrid.x) + Math.abs(grid.y + a.y - this.playerGrid.y);
        const db =
          Math.abs(grid.x + b.x - this.playerGrid.x) + Math.abs(grid.y + b.y - this.playerGrid.y);
        return da - db;
      });
      pick = ranked[0];
    } else if (g.mode === "random" && Math.random() < 0.3) {
      pick = choices[Phaser.Math.Between(0, choices.length - 1)];
    }

    return pick;
  }

  updateGhosts(dt) {
    for (const g of this.ghosts) {
      if (g.eaten) continue;

      if (g.frightenedUntil > 0 && this.time.now >= g.frightenedUntil) {
        g.frightenedUntil = 0;
        if (KopilkaAssets) KopilkaAssets.setGhostFrightened(g.sprite, false);
      }

      const speed = GHOST_SPEED * (GHOST_SPEED_MOD[g.id] || 1);
      g.grid = this.worldToGrid(g.sprite.x, g.sprite.y);

      if (this.isAtTileCenter(g.sprite.x, g.sprite.y)) {
        this.alignToCorridor(g.sprite, g.dir);
        const canKeep = g.dir.length() && this.canMoveFromSprite(g.sprite, g.dir);
        if (!canKeep) {
          g.dir = this.chooseGhostDir(g);
          if (g.dir.length()) this.alignToCorridor(g.sprite, g.dir);
        }
      }

      if (g.dir.length()) {
        g.dir = this.stepSprite(g.sprite, g.dir, speed, dt);
      }
      g.grid = this.worldToGrid(g.sprite.x, g.sprite.y);
    }
  }

  respawnGhost(g) {
    if (this._ending || !g?.sprite) return;
    if (g._eatenRespawnTimer) {
      g._eatenRespawnTimer.remove(false);
      g._eatenRespawnTimer = null;
    }
    g.eaten = false;
    g.frightenedUntil = 0;
    const sg = g.spawnGrid;
    g.grid = { x: sg.x, y: sg.y };
    g.dir = new Phaser.Math.Vector2(-1, 0);
    const w = g.spawnWorld || this.gridToWorld(sg.x, sg.y);
    g.sprite.x = w.x;
    g.sprite.y = w.y;
    g.sprite.setVisible(true);
    g.sprite.setAlpha(1);
    if (KopilkaAssets) KopilkaAssets.setGhostFrightened(g.sprite, false);
    if (this.isPortfolioActive()) {
      g.frightenedUntil = this.portfolioUntil;
      if (KopilkaAssets) KopilkaAssets.setGhostFrightened(g.sprite, true);
    }
  }

  eatGhost(g) {
    g.eaten = true;
    g.frightenedUntil = 0;
    g.sprite.setVisible(false);
    if (KopilkaAssets) KopilkaAssets.setGhostFrightened(g.sprite, false);
    this.addScore(200);
    const label = GHOST_TYPES.find((t) => t.id === g.id)?.label || g.id;
    this.hudMode.setText(`${label} съеден!`);
    if (g._eatenRespawnTimer) g._eatenRespawnTimer.remove(false);
    g._eatenRespawnTimer = this.time.delayedCall(GHOST_EATEN_RESPAWN_MS, () => {
      g._eatenRespawnTimer = null;
      this.respawnGhost(g);
    });
  }

  resetGhostsToSpawn() {
    this.ghosts.forEach((g) => {
      if (g._eatenRespawnTimer) {
        g._eatenRespawnTimer.remove(false);
        g._eatenRespawnTimer = null;
      }
      this.respawnGhost(g);
    });
  }

  finishRespawn() {
    this._respawnTimer = null;
    if (this._ending) return;
    this.respawnUntil = 0;
    if (this.player?.setAlpha) this.player.setAlpha(1);
    this._lastPelletGx = this.playerGrid.x;
    this._lastPelletGy = this.playerGrid.y;
    this.hudMode.setText("");
  }

  handlePlayerDeath() {
    if (this._ending || this.isRespawning()) return;

    this.lives -= 1;
    KopilkaFigmaUi.updateGameLives(this.lives);

    if (this.lives <= 0) {
      this.endGame();
      return;
    }

    const pauseMs = 3000;
    this.respawnUntil = this.time.now + pauseMs;
    this.playerGrid = { ...MAZE.playerStart };
    this.syncPlayerSprite();
    this._lastPelletGx = this.playerGrid.x;
    this._lastPelletGy = this.playerGrid.y;
    this.currentDir = new Phaser.Math.Vector2(0, 0);
    this.nextDir = new Phaser.Math.Vector2(0, 0);
    this.resetGhostsToSpawn();
    this.cameras.main.shake(200, 0.01);
    this.hudMode.setText("Пауза 3 с — можно снова двигаться");

    if (this.player?.setAlpha) this.player.setAlpha(0.45);

    if (this._respawnTimer) this._respawnTimer.remove(false);
    this._respawnTimer = this.time.addEvent({
      delay: pauseMs,
      callback: () => this.finishRespawn(),
    });
  }

  checkGhostCollision() {
    if (this.isRespawning()) return;

    for (const g of this.ghosts) {
      if (g.eaten) continue;
      if (
        Phaser.Math.Distance.Between(this.player.x, this.player.y, g.sprite.x, g.sprite.y) >=
        HIT_RADIUS
      ) {
        continue;
      }

      if (this.time.now < g.frightenedUntil) {
        this.eatGhost(g);
        return;
      }

      this.handlePlayerDeath();
      return;
    }

    if (this.portfolioSprite?.visible && MAZE.portfolioTile) {
      const pt = this.entityWorld(MAZE.portfolioTile);
      if (Phaser.Math.Distance.Between(this.player.x, this.player.y, pt.x, pt.y) < HIT_RADIUS) {
        this.activatePortfolio();
      }
    }
  }

  async endGame() {
    if (this._ending) return;
    this._ending = true;
    this.respawnUntil = 0;
    if (this._respawnTimer) this._respawnTimer.remove(false);
    this._respawnTimer = null;
    this.ghosts?.forEach((g) => {
      if (g._eatenRespawnTimer) g._eatenRespawnTimer.remove(false);
    });
    this.tweens.killAll();
    this.clockTimer?.remove(false);
    this.clockTimer = null;
    this.registry.set("lastScore", this.score);

    KopilkaFigmaUi.prefetchScreen("leaderboard");
    await KopilkaFigmaUi.dissolveGameLayer();
    this.scene.start("Result");
  }
}

const RESULT_LEADERBOARD_SEC = 10;
const LEADERBOARD_TOP_LIMIT = 8;

function classifyResultScreen(score, entries) {
  const list = entries || [];
  if (score <= 0) return "result_score";

  const topScore = list[0]?.score;
  const eighthScore = list.length >= LEADERBOARD_TOP_LIMIT ? list[LEADERBOARD_TOP_LIMIT - 1].score : null;

  if (topScore == null || score > topScore) return "result_record";
  if (score === topScore) return "result_record";
  if (eighthScore == null || score >= eighthScore) return "result_top";
  return "result_score";
}

async function fetchLeaderboardEntries(limit) {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), 4000);
  try {
    const res = await fetch(`/api/leaderboard?limit=${limit}`, { signal: ac.signal });
    if (!res.ok) return [];
    const data = await res.json();
    return data.entries || [];
  } catch {
    return [];
  } finally {
    clearTimeout(timer);
  }
}

class ResultScene extends Phaser.Scene {
  constructor() {
    super("Result");
  }

  async create() {
    const score = this.registry.get("lastScore") || 0;
    const bestBefore = this.registry.get("bestScore") || 0;
    this.nickIndex = 0;
    this.score = score;
    this._finished = false;
    this._uiReady = false;
    this._submitting = false;
    this.screenId = "result_score";
    this.nickUi = null;
    this._countdownTimer = null;

    this.joy = linkGamepad(this) || this.registry.get("joystick");
    this.cursors = this.input.keyboard.createCursorKeys();
    this.keys = this.input.keyboard.addKeys("ENTER,SPACE");

    KopilkaFigmaUi.drawGradientBg(this);
    KopilkaFigmaUi.prefetchScreen("result_score");
    KopilkaFigmaUi.prefetchScreen("result_top");
    KopilkaFigmaUi.prefetchScreen("result_record");
    KopilkaFigmaUi.prefetchScreen("leaderboard");
    this.registry.remove("lbPrefetch");

    const entries = await fetchLeaderboardEntries(LEADERBOARD_TOP_LIMIT);
    if (!this.scene.isActive("Result")) return;

    this.screenId = classifyResultScreen(score, entries);
    const ui = KopilkaFigmaUi.buildStaticScreen(this, this.screenId, { score });
    await ui.framePromise;
    if (!this.scene.isActive("Result")) return;

    this.mountResultNickUi();

    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      this._countdownTimer?.remove(false);
      this._countdownTimer = null;
      if (this._resultKeyHandler && this.input?.keyboard) {
        this.input.keyboard.off("keydown", this._resultKeyHandler);
      }
      this._resultKeyHandler = null;
      this.nickUi?.destroy();
      this.nickUi = null;
    });

    if (score > bestBefore) this.registry.set("bestScore", score);
  }

  startResultCountdownTimer() {
    this._countdownTimer?.remove(false);
    this._countdownTimer = this.time.addEvent({
      delay: 1000,
      loop: true,
      callback: () => {
        if (this._finished) return;
        this._countdownLeft -= 1;
        if (this._countdownLeft > 0) {
          this.nickUi?.setCountdown(this._countdownLeft);
          return;
        }
        this.finishAndGoToLeaderboard();
      },
    });
  }

  mountResultNickUi() {
    const chrome = document.querySelector("#figma-overlay .figma-overlay__chrome");
    this.nickUi = KopilkaFigmaUi.createResultNickPicker(chrome, NICKNAMES[this.nickIndex]);
    this.nickUi?.setHintVisible(false);
    this._countdownLeft = RESULT_LEADERBOARD_SEC;
    this.nickUi?.setCountdown(this._countdownLeft);
    this.startResultCountdownTimer();

    this.bindResultKeyboardIdleReset();
    this._uiReady = true;
  }

  resetResultIdleTimer() {
    if (this._finished || !this._uiReady) return;
    this._countdownLeft = RESULT_LEADERBOARD_SEC;
    this.nickUi?.setCountdown(this._countdownLeft);
    this.startResultCountdownTimer();
  }

  bindResultKeyboardIdleReset() {
    if (!this.input?.keyboard || this._resultKeyHandler) return;
    this._resultKeyHandler = () => this.resetResultIdleTimer();
    this.input.keyboard.on("keydown", this._resultKeyHandler);
  }

  shiftNick(delta) {
    this.nickIndex = (this.nickIndex + delta + NICKNAMES.length) % NICKNAMES.length;
    this.nickUi?.setName(NICKNAMES[this.nickIndex]);
    this.resetResultIdleTimer();
  }

  finishAndGoToLeaderboard() {
    if (this._finished) return;
    this._finished = true;
    this._countdownTimer?.remove(false);
    this._countdownTimer = null;
    this.nickUi?.setCountdown(0);
    const name = NICKNAMES[this.nickIndex];
    this.registry.set("lastPlayerName", name);
    this.registry.set("lbHighlightPlayer", true);
    this.registry.set("lbPrefetch", this.submitAndLoadLeaderboard(name, this.score));
    this.nickUi?.destroy();
    this.nickUi = null;
    this.scene.start("Leaderboard");
  }

  update() {
    if (this._finished || !this._uiReady) return;
    this.joy?.update();

    if (this.joy?.consumeAnyButtonEdge()) {
      this.resetResultIdleTimer();
    }

    if (this.joy?.consumeOptionsPress()) {
      this._finished = true;
      this._countdownTimer?.remove(false);
      this._countdownTimer = null;
      this.nickUi?.destroy();
      this.nickUi = null;
      this.scene.start("Start");
      return;
    }

    const nav = this.joy?.consumeNameNavEdge();
    if (nav === "left") this.shiftNick(-1);
    if (nav === "right") this.shiftNick(1);
    if (this.cursors && Phaser.Input.Keyboard.JustDown(this.cursors.left)) this.shiftNick(-1);
    if (this.cursors && Phaser.Input.Keyboard.JustDown(this.cursors.right)) this.shiftNick(1);

    const confirm =
      this.joy?.consumeCrossPress() ||
      (this.keys && Phaser.Input.Keyboard.JustDown(this.keys.ENTER)) ||
      (this.keys && Phaser.Input.Keyboard.JustDown(this.keys.SPACE));
    if (confirm) {
      this.finishAndGoToLeaderboard();
    }
  }

  submitAndLoadLeaderboard(name, score) {
    if (this._submitting) {
      return this.registry.get("lbPrefetch") || Promise.resolve({ entries: [] });
    }
    this._submitting = true;

    const ac = new AbortController();
    const timeoutId = setTimeout(() => ac.abort(), 5000);

    return fetch("/api/leaderboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_name: name, score }),
      signal: ac.signal,
    })
      .catch(() => {})
      .then(() => fetch("/api/leaderboard?limit=8", { signal: ac.signal }))
      .then((res) => (res.ok ? res.json() : { entries: [] }))
      .catch(() => ({ entries: [] }))
      .finally(() => clearTimeout(timeoutId));
  }
}

class LeaderboardScene extends Phaser.Scene {
  constructor() {
    super("Leaderboard");
  }

  create() {
    const ui = KopilkaFigmaUi.buildStaticScreen(this, "leaderboard");
    // Строки таблицы рисуем только после готовности экрана: иначе отложенный
    // applyChrome (chrome.innerHTML="") в переходе результат→лидерборд стирает
    // уже отрисованные имена/очки.
    this._screenReady = ui?.framePromise || Promise.resolve();

    this.joy = linkGamepad(this) || this.registry.get("joystick");
    this.keys = this.input.keyboard.addKeys("ENTER");

    const prefetched = this.registry.get("lbPrefetch");
    if (prefetched?.then) {
      prefetched
        .then((data) => this.renderBoard(data.entries || []))
        .catch(() => this.renderBoard([]))
        .finally(() => {
          this.registry.remove("lbPrefetch");
          this.registry.remove("lbHighlightPlayer");
        });
    } else {
      this.loadBoard();
    }
  }

  renderBoard(entries) {
    const ready = this._screenReady || Promise.resolve();
    ready
      .then(() => this._renderBoardNow(entries))
      .catch(() => this._renderBoardNow(entries));
  }

  _renderBoardNow(entries) {
    if (!this.scene.isActive("Leaderboard")) return;
    const highlightPlayer = this.registry.get("lbHighlightPlayer");
    const lastName = highlightPlayer ? this.registry.get("lastPlayerName") : null;
    const lastScore = highlightPlayer ? Number(this.registry.get("lastScore") || 0) : 0;

    let rows = (entries || []).slice(0, 8).map((e) => ({
      name: e.name,
      score: e.score,
      current:
        !!lastName &&
        e.name === lastName &&
        Number(e.score) === lastScore,
    }));

    const playerInList = rows.some((r) => r.current);
    if (highlightPlayer && lastName && lastScore > 0 && !playerInList) {
      const playerRow = { name: lastName, score: lastScore, current: true };
      const insertAt = rows.findIndex((r) => lastScore >= Number(r.score || 0));
      if (insertAt === -1) {
        rows = rows.slice(0, 7).concat([playerRow]);
      } else {
        rows.splice(insertAt, 0, playerRow);
        rows = rows.slice(0, 8);
      }
    }

    while (rows.length < 8) {
      const n = rows.length + 1;
      rows.push({ name: `гость ${n}`, score: 0, current: false });
    }

    KopilkaFigmaUi.updateLeaderboardChrome(rows);
  }

  loadBoard() {
    const ac = new AbortController();
    const timeoutId = setTimeout(() => ac.abort(), 4000);
    fetch("/api/leaderboard?limit=8", { signal: ac.signal })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        this.renderBoard(data.entries || []);
      })
      .catch(() => {
        this.renderBoard([]);
      })
      .finally(() => clearTimeout(timeoutId));
  }

  update() {
    this.joy?.update();
    if (this.joy?.consumeCrossPress() || Phaser.Input.Keyboard.JustDown(this.keys.ENTER)) {
      this.scene.start("Start");
    }
  }
}

  window.KopilkaScenes = {
    BootScene,
    StartScene,
    OnboardingScene,
    ErrorScene,
    GameScene,
    ResultScene,
    LeaderboardScene,
  };
})();
