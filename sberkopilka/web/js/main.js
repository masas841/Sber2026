function showBootError(msg) {
  const root = document.getElementById("game-root");
  if (root) {
    root.innerHTML = `<p style="color:#ff6b6b;padding:24px;font:18px Segoe UI,sans-serif;max-width:640px;line-height:1.5">${msg}</p>`;
  }
  console.error("[SberKopilka]", msg);
}

if (window.__kopilkaLoadError) {
  showBootError(window.__kopilkaLoadError);
} else if (typeof Phaser === "undefined") {
  showBootError(
    "Не загрузился Phaser (файл /static/vendor/phaser.min.js). Перезапустите сервер и обновите Ctrl+F5.",
  );
} else if (!window.KopilkaMaze) {
  showBootError("Не загружен maze.js — проверьте консоль (F12).");
} else if (!window.KopilkaDesign) {
  showBootError("Не загружен design-manifest.js — обновите Ctrl+F5.");
} else if (!window.KopilkaFigmaUi) {
  showBootError("Не загружен figma-ui.js — обновите Ctrl+F5.");
} else if (!window.KopilkaAssets) {
  showBootError("Не загружен assets.js — обновите Ctrl+F5.");
} else if (!window.KopilkaScenes) {
  showBootError("Не загружен scenes.js — проверьте консоль (F12).");
} else {
  const {
    BootScene,
    StartScene,
    OnboardingScene,
    ErrorScene,
    GameScene,
    ResultScene,
    LeaderboardScene,
  } = window.KopilkaScenes;

  const gameW = window.KopilkaMaze.SCREEN_W;
  const gameH = window.KopilkaMaze.SCREEN_H;

  try {
    const game = new Phaser.Game({
      type: Phaser.AUTO,
      parent: "game-root",
      width: gameW,
      height: gameH,
      transparent: true,
      backgroundColor: "#00000000",
      input: {
        gamepad: true,
      },
      scale: {
        mode: Phaser.Scale.NONE,
        autoCenter: Phaser.Scale.NO_CENTER,
      },
      scene: [
        BootScene,
        StartScene,
        OnboardingScene,
        ErrorScene,
        GameScene,
        ResultScene,
        LeaderboardScene,
      ],
    });

    window.kopilkaGame = game;

    game.events.once("ready", () => {
      const joy = window.kopilkaJoystick;
      if (!joy || !game.input?.gamepad) return;
      const linkPad = (pad) => {
        if (pad && pad.index === 0) joy.setPhaserPad(pad);
      };
      game.input.gamepad.on("connected", (pad) => linkPad(pad));
      if (game.input.gamepad.pad1) linkPad(game.input.gamepad.pad1);
    });
  } catch (e) {
    showBootError(`Ошибка запуска Phaser: ${e.message}`);
  }
}
