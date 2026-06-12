/**
 * Игровое поле и HUD по макету Figma (game 25:6).
 */
(function () {
  "use strict";

  const LAYOUT_KEY = "kopilka_game_field";

  function design() {
    return window.KopilkaDesign;
  }

  function figmaUi() {
    return window.KopilkaFigmaUi;
  }

  function loadLayout(scene) {
    if (layoutCache) return layoutCache;
    if (scene?.cache?.json?.has(LAYOUT_KEY)) {
      layoutCache = scene.cache.json.get(LAYOUT_KEY);
      return layoutCache;
    }
    return null;
  }

  let layoutCache = null;

  function place(scene, file, x, y, w, h, depth, rot, scaleY) {
    const d = design();
    const ui = figmaUi();
    if (!d || !ui) return null;
    const img = ui.placeImage(scene, file, x, y, w, h, depth, 0.5, 0.5);
    if (!img) return null;
    if (rot) img.setAngle(rot);
    if (scaleY === -1) img.setScale(img.scaleX, -Math.abs(img.scaleY));
    return img;
  }

  function drawChrome(scene, layout) {
    const c = layout.chrome || {};
    const depth = 1;
    figmaUi()?.drawGradientBg(scene);
    if (c.bgDecor) {
      place(scene, c.bgDecor, 336, 307, 728, 882, depth, 0, 1);
    }
    if (c.shadow1) {
      const s = place(scene, c.shadow1, 336, 347, 722, 722, depth + 1, 0, 1);
      if (s) s.setAlpha(0.5);
    }
    if (c.shadow2) {
      const s = place(scene, c.shadow2, 334, 344, 722, 722, depth + 1, 0, 1);
      if (s) s.setAlpha(0.45);
    }
    if (c.fieldFrame) {
      const ox = layout.fieldOrigin[0];
      const oy = layout.fieldOrigin[1];
      const fw = layout.cols * layout.tile;
      const fh = layout.rows * layout.tile;
      place(scene, c.fieldFrame, ox + fw / 2, oy + fh / 2, fw + 52, fh + 52, depth + 2, 0, 1);
    }
  }

  function drawStaticWalls(scene, layout) {
    const walls = layout.walls || [];
    walls.forEach((L) => {
      place(
        scene,
        L.file,
        L.x + L.w / 2,
        L.y + L.h / 2,
        L.w,
        L.h,
        3,
        L.rot || 0,
        L.scaleY || 1,
      );
    });
  }

  function drawPathFloor(scene, ox, oy, cols, rows, tile) {
    const g = scene.add.graphics().setDepth(2);
    g.fillStyle(0xd8f5f2, 0.55);
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const cx = ox + x * tile + tile / 2;
        const cy = oy + y * tile + tile / 2;
        g.fillRoundedRect(cx - tile / 2 + 1, cy - tile / 2 + 1, tile - 2, tile - 2, 4);
      }
    }
    return g;
  }

  function createFigmaHud(scene, score, lives, timeLeft) {
    const d = design();
    const ui = figmaUi();
    const hud = d?.hud || {};
    const depth = 45;

    const livesCloud = hud.livesCloud
      ? place(scene, hud.livesCloud.file, hud.livesCloud.x, 64, hud.livesCloud.w, hud.livesCloud.h, depth, 0, 1)
      : null;

    const scoreCloud = hud.scoreCloud
      ? place(scene, hud.scoreCloud.file, hud.scoreCloud.x, hud.scoreCloud.y, hud.scoreCloud.w, hud.scoreCloud.h, depth, 0.5, 0.5)
      : null;

    if (hud.scoreDecorL) {
      place(scene, hud.scoreDecorL.file, hud.scoreDecorL.x, hud.scoreDecorL.y, hud.scoreDecorL.w, hud.scoreDecorL.h, depth + 1, 2.74, 1);
    }
    if (hud.scoreDecorR) {
      place(scene, hud.scoreDecorR.file, hud.scoreDecorR.x, hud.scoreDecorR.y, hud.scoreDecorR.w, hud.scoreDecorR.h, depth + 1, 24.87, 1);
    }

    const scoreLabel = scene.add
      .text(d.sx(336), d.sy(606), "счёт:", {
        fontFamily: '"SB Sans Display", "Segoe UI", sans-serif',
        fontSize: `${d.sx(23)}px`,
        color: "#01d701",
        fontStyle: "bold",
      })
      .setOrigin(0.5, 0)
      .setDepth(depth + 2);

    const scoreValue = scene.add
      .text(d.sx(336), d.sy(628), String(score).padStart(3, "0"), {
        fontFamily: '"SB Sans Display", "Segoe UI", sans-serif',
        fontSize: `${d.sx(37)}px`,
        color: "#122654",
        fontStyle: "bold",
      })
      .setOrigin(0.5, 0)
      .setDepth(depth + 2);

    const livesText = scene.add
      .text(d.sx(336), d.sy(52), "♥".repeat(lives), {
        fontFamily: '"Segoe UI", sans-serif',
        fontSize: `${d.sx(20)}px`,
        color: "#ff4fa3",
      })
      .setOrigin(0.5, 0.5)
      .setDepth(depth + 3);

    const timeText = scene.add
      .text(d.sx(620), d.sy(18), `${timeLeft} с`, {
        fontFamily: '"SB Sans Display", "Segoe UI", sans-serif',
        fontSize: `${d.sx(14)}px`,
        color: "#122654",
        fontStyle: "600",
        backgroundColor: "#ffffffcc",
        padding: { x: 8, y: 3 },
      })
      .setOrigin(1, 0)
      .setDepth(depth + 2);

    const modeText = scene.add
      .text(d.sx(336), d.sy(8), "", {
        fontFamily: '"Segoe UI", sans-serif',
        fontSize: `${d.sx(13)}px`,
        color: "#122654",
        fontStyle: "bold",
        backgroundColor: "#ffffffdd",
        padding: { x: 10, y: 3 },
      })
      .setOrigin(0.5, 0)
      .setDepth(depth + 2);

    return {
      livesCloud,
      scoreCloud,
      scoreLabel,
      scoreValue,
      livesText,
      timeText,
      modeText,
    };
  }

  function build(scene, maze, tile, wallSet) {
    const layout = loadLayout(scene);
    if (!layout) return null;
    const ox = layout.fieldOrigin[0];
    const oy = layout.fieldOrigin[1];

    drawChrome(scene, layout);

    if (wallSet) {
      for (let y = 0; y < maze.rows; y++) {
        for (let x = 0; x < maze.cols; x++) {
          if (!wallSet.has(`${x},${y}`)) {
            const cx = ox + x * tile + tile / 2;
            const cy = oy + y * tile + tile / 2;
            const g = scene.add.graphics().setDepth(2);
            g.fillStyle(0xc8ede9, 0.7);
            g.fillRoundedRect(cx - tile / 2 + 1, cy - tile / 2 + 1, tile - 2, tile - 2, 3);
          }
        }
      }
    }

    drawStaticWalls(scene, layout);
    return { ox, oy, layout };
  }

  window.KopilkaFigmaBoard = {
    LAYOUT_KEY,
    loadLayout,
    build,
    createFigmaHud,
    drawChrome,
  };
})();
