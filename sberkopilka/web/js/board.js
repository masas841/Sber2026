/**
 * Поле по макету ТЗ: бирюзовый фон, «травяные» стены, розовая рамка.
 */
(function () {
  const REF = {
    sky: 0xd4f4f7,
    skyBlob: 0xa8e6ef,
    skyHi: 0xffffff,
    path: 0xb8ebe8,
    pathHi: 0xcff5f2,
    grassDark: 0x2e7d32,
    grass: 0x43a047,
    grassHi: 0x66bb6a,
    grassLight: 0x9ccc65,
    frame: 0xff5cab,
    frameInner: 0xff89c0,
    frameGlow: 0xffb3d9,
  };

  function drawSky(scene, w, h) {
    if (window.KopilkaFigmaUi?.drawGradientBg) {
      return window.KopilkaFigmaUi.drawGradientBg(scene);
    }
    const bg = scene.add.graphics().setDepth(0);
    bg.fillStyle(REF.sky, 1);
    bg.fillRect(0, 0, w, h);
    bg.fillStyle(REF.skyBlob, 0.45);
    bg.fillEllipse(w * 0.25, h * 0.2, w * 0.55, h * 0.35);
    bg.fillEllipse(w * 0.78, h * 0.35, w * 0.4, h * 0.28);
    bg.fillStyle(REF.skyHi, 0.35);
    bg.fillEllipse(w * 0.5, h * 0.85, w * 0.7, h * 0.25);
    return bg;
  }

  function drawPathCell(g, cx, cy, tile) {
    const half = tile / 2 - 1;
    g.fillStyle(REF.path, 1);
    g.fillRect(cx - half, cy - half, half * 2, half * 2);
    g.fillStyle(REF.pathHi, 0.35);
    g.fillRect(cx - half + 2, cy - half + 2, half * 2 - 4, 3);
  }

  function drawGrassTuft(g, cx, cy, tile) {
    const r = tile * 0.46;
    g.fillStyle(REF.grassDark, 0.35);
    g.fillEllipse(cx + 2, cy + 3, r * 1.9, r * 1.5);
    g.fillStyle(REF.grassDark, 1);
    g.fillCircle(cx, cy + 2, r * 0.95);
    g.fillStyle(REF.grass, 1);
    g.fillCircle(cx - 2, cy - 1, r * 0.82);
    g.fillStyle(REF.grassHi, 1);
    g.fillCircle(cx + 3, cy - 3, r * 0.62);
    g.fillStyle(REF.grassLight, 0.75);
    g.fillCircle(cx - 4, cy - 4, r * 0.28);
    g.fillCircle(cx + 5, cy + 1, r * 0.22);
    g.fillStyle(0x1b5e20, 0.25);
    g.fillCircle(cx, cy + 5, r * 0.55);
  }

  function drawGrassSprite(scene, layer, cx, cy, tile) {
    const key = window.KopilkaAssets?.wallTextureKey?.(scene);
    if (!key) return false;
    const img = scene.add.image(cx, cy, key);
    img.setDisplaySize(tile, tile);
    img.setDepth(3);
    layer.add(img);
    return true;
  }

  function drawPinkFrame(g, ox, oy, mw, mh, pad) {
    const x = ox - pad;
    const y = oy - pad;
    const w = mw + pad * 2;
    const h = mh + pad * 2;
    g.fillStyle(REF.frameGlow, 0.25);
    g.fillRoundedRect(x - 6, y - 6, w + 12, h + 12, 48);
    g.lineStyle(14, REF.frame, 1);
    g.strokeRoundedRect(x, y, w, h, 42);
    g.lineStyle(5, REF.frameInner, 0.9);
    g.strokeRoundedRect(x + 6, y + 6, w - 12, h - 12, 36);
  }

  function drawDecor(scene, w, h) {
    const d = scene.add.graphics().setDepth(50);
    d.lineStyle(3, 0xff4fa3, 0.7);
    d.beginPath();
    d.moveTo(24, h - 72);
    d.lineTo(34, h - 58);
    d.lineTo(28, h - 48);
    d.lineTo(40, h - 40);
    d.strokePath();
    d.fillStyle(0x5ecfff, 1);
    d.fillCircle(w - 36, h - 52, 8);
    d.fillStyle(0xffffff, 0.6);
    d.fillCircle(w - 39, h - 55, 3);
    return d;
  }

  function draw(scene, ox, oy, maze, tile, opts = {}) {
    const wallSet = new Set(maze.walls.map((w) => `${w.x},${w.y}`));
    const pad = opts.framePad ?? 26;
    const mw = maze.cols * tile;
    const mh = maze.rows * tile;

    if (!opts.skipSky) drawSky(scene, scene.scale.width, scene.scale.height);

    const floorG = scene.add.graphics().setDepth(1);
    const wallG = scene.add.graphics().setDepth(3);
    const wallLayer = scene.add.layer().setDepth(3);
    const useFigmaWalls = !!window.KopilkaAssets?.wallTextureKey?.(scene);

    for (let y = 0; y < maze.rows; y++) {
      for (let x = 0; x < maze.cols; x++) {
        const cx = ox + x * tile + tile / 2;
        const cy = oy + y * tile + tile / 2;
        if (wallSet.has(`${x},${y}`)) {
          if (!useFigmaWalls || !drawGrassSprite(scene, wallLayer, cx, cy, tile)) {
            drawGrassTuft(wallG, cx, cy, tile);
          }
        } else {
          drawPathCell(floorG, cx, cy, tile);
        }
      }
    }

    const frameG = scene.add.graphics().setDepth(2);
    drawPinkFrame(frameG, ox, oy, mw, mh, pad);

    const decor = opts.decor !== false ? drawDecor(scene, scene.scale.width, scene.scale.height) : null;

    return { floorG, wallG, frameG, decor, wallSet };
  }

  window.KopilkaBoard = {
    REF,
    draw,
    drawSky,
  };
})();
