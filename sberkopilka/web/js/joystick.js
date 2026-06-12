/**
 * USB / Bluetooth геймпад (Gamepad API + опционально Phaser).
 * DualSense: Cross=0, Options=9, D-pad кнопки 12–15 или оси.
 */
class JoystickInput {
  constructor(deadzone = 0.35) {
    this.deadzone = deadzone;
    this.direction = null;
    this.startPressed = false;
    this.startJustPressed = false;
    this.crossJustPressed = false;
    this.optionsJustPressed = false;
    this.nameNav = null;
    this._prevCross = false;
    this._prevOptions = false;
    this._prevNav = "";
    this._prevButtons = [];
    this.anyButtonJustPressed = false;
    this.connected = false;
    this.activated = false;
    this.padLabel = "";
    this.padIndex = -1;
    this._activePadIndex = null;
    this._currentPadKey = "";
    this._selectorButtons = new Map();
    this._phaserPad = null;
  }

  setDeadzone(value) {
    this.deadzone = Math.max(0.1, Math.min(0.9, value));
  }

  setPhaserPad(pad) {
    this._phaserPad = pad || null;
    if (pad) {
      this.connected = true;
      this.padLabel = pad.id || "Gamepad";
    }
  }

  static _pads() {
    return navigator.getGamepads?.() || [];
  }

  static findActivePad() {
    let movedPad = null;
    for (const pad of JoystickInput._pads()) {
      if (!pad?.connected) continue;
      if (JoystickInput._anyButton(pad)) return pad;
      if (!movedPad && JoystickInput._moved(pad)) movedPad = pad;
    }
    return movedPad;
  }

  static findAnyPad() {
    for (const pad of JoystickInput._pads()) {
      if (pad?.connected) return pad;
    }
    return null;
  }

  static padByIndex(index) {
    if (!Number.isFinite(index)) return null;
    const pad = JoystickInput._pads()[index];
    return pad?.connected ? pad : null;
  }

  static _anyButton(pad) {
    return pad.buttons.some((b) => b?.pressed || (b?.value ?? 0) > 0.5);
  }

  static _btn(pad, i) {
    const b = pad.buttons[i];
    return !!(b?.pressed || (b?.value ?? 0) > 0.5);
  }

  static _moved(pad, threshold = 0.5) {
    return pad.axes.some((v) => Math.abs(v || 0) > threshold);
  }

  _padFromPhaser() {
    const p = this._phaserPad;
    if (!p) return null;
    return {
      id: p.id,
      index: p.index,
      connected: true,
      axes: p.axes.map((a) => a.getValue()),
      buttons: p.buttons.map((b) => ({ pressed: b.pressed, value: b.value })),
    };
  }

  _getPad() {
    const selected = this._selectNativePad(false);
    if (selected) return selected;

    const ph = this._padFromPhaser();
    if (ph) return ph;
    return JoystickInput.findAnyPad();
  }

  _selectNativePad(allowIdleFallback = false) {
    const pads = Array.from(JoystickInput._pads()).filter((pad) => pad?.connected);
    if (!pads.length) {
      this._selectorButtons.clear();
      return null;
    }

    const locked = JoystickInput.padByIndex(this._activePadIndex);
    const edge = this._buttonEdgePad(pads);
    if (edge) {
      this._activePadIndex = edge.index;
      return edge;
    }

    // Если устройство уже выбрано, удерживаем его. Шум от второго геймпада
    // не должен перебивать управление после первого нажатия.
    if (locked) return locked;

    const moved = pads.find((pad) => JoystickInput._moved(pad, Math.max(0.55, this.deadzone)));
    if (moved) {
      this._activePadIndex = moved.index;
      return moved;
    }

    return allowIdleFallback ? pads[0] : null;
  }

  _padKey(pad) {
    if (!pad) return "";
    if (Number.isFinite(pad.index)) return `idx:${pad.index}`;
    return `id:${pad.id || "Gamepad"}`;
  }

  _resetEdges() {
    this._prevCross = false;
    this._prevOptions = false;
    this._prevNav = "";
    this._prevButtons.length = 0;
  }

  _buttonState(pad) {
    return (pad.buttons || []).map((_, i) => JoystickInput._btn(pad, i));
  }

  _buttonEdgePad(pads) {
    let edgePad = null;
    const alive = new Set();
    for (const pad of pads) {
      const key = this._padKey(pad);
      alive.add(key);
      const current = this._buttonState(pad);
      const prev = this._selectorButtons.get(key);
      if (!edgePad && prev && current.some((pressed, i) => pressed && !prev[i])) {
        edgePad = pad;
      }
      this._selectorButtons.set(key, current);
    }
    for (const key of this._selectorButtons.keys()) {
      if (!alive.has(key)) this._selectorButtons.delete(key);
    }
    return edgePad;
  }

  _readDirection(pad) {
    const dz = this.deadzone;
    const ax0 = pad.axes[0] ?? 0;
    const ay0 = pad.axes[1] ?? 0;

    if (Math.abs(ax0) >= dz || Math.abs(ay0) >= dz) {
      if (Math.abs(ax0) > Math.abs(ay0)) {
        return ax0 > 0 ? "right" : "left";
      }
      return ay0 > 0 ? "down" : "up";
    }

    // D-pad кнопки (Standard)
    if (JoystickInput._btn(pad, 12)) return "up";
    if (JoystickInput._btn(pad, 13)) return "down";
    if (JoystickInput._btn(pad, 14)) return "left";
    if (JoystickInput._btn(pad, 15)) return "right";

    // DualSense: иногда hat на осях 6/7 или 4/5
    const ax6 = pad.axes[6] ?? 0;
    const ax7 = pad.axes[7] ?? 0;
    if (Math.abs(ax6) > 0.5) return ax6 > 0 ? "right" : "left";
    if (Math.abs(ax7) > 0.5) return ax7 > 0 ? "down" : "up";

    return null;
  }

  /** Влево/вправо для выбора имени (без «вниз»). */
  _readNameNav(pad) {
    if (JoystickInput._btn(pad, 14)) return "left";
    if (JoystickInput._btn(pad, 15)) return "right";
    const ax = pad.axes[0] ?? 0;
    if (Math.abs(ax) >= this.deadzone) {
      return ax > 0 ? "right" : "left";
    }
    return null;
  }

  /** Вызывать один раз за кадр — только из Phaser update. */
  update() {
    this.crossJustPressed = false;
    this.optionsJustPressed = false;
    this.anyButtonJustPressed = false;
    this.nameNav = null;
    this.direction = null;

    const pad = this._getPad();
    const active = JoystickInput.padByIndex(this._activePadIndex);
    const anyNative = JoystickInput.findAnyPad();

    if (pad) {
      const key = this._padKey(pad);
      if (key !== this._currentPadKey) {
        this._currentPadKey = key;
        this._resetEdges();
      }
      this.connected = true;
      this.padLabel = pad.id || "Gamepad";
      this.padIndex = Number.isFinite(pad.index) ? pad.index : -1;
      this.activated = !!(active || JoystickInput._anyButton(pad));

      this.direction = this._readDirection(pad);
      this.nameNav = this._readNameNav(pad);
      const cross = JoystickInput._btn(pad, 0);
      const options = JoystickInput._btn(pad, 9);
      this.crossJustPressed = cross && !this._prevCross;
      this.optionsJustPressed = options && !this._prevOptions;
      this._prevCross = cross;
      this._prevOptions = options;

      const btnCount = pad.buttons?.length || 0;
      if (this._prevButtons.length < btnCount) {
        this._prevButtons.length = btnCount;
      }
      for (let i = 0; i < btnCount; i++) {
        const pressed = JoystickInput._btn(pad, i);
        if (pressed && !this._prevButtons[i]) {
          this.anyButtonJustPressed = true;
        }
        this._prevButtons[i] = pressed;
      }
      return;
    }

    if (anyNative) {
      this.connected = true;
      this.padLabel = anyNative.id || "Gamepad";
      this.activated = false;
    } else {
      this.connected = false;
      this.activated = false;
      this.padLabel = "";
      this.padIndex = -1;
      this._activePadIndex = null;
      this._currentPadKey = "";
    }
    this._resetEdges();
  }

  consumeNameNavEdge() {
    const nav = this.nameNav;
    if (!nav) {
      this._prevNav = "";
      return null;
    }
    if (nav === this._prevNav) return null;
    this._prevNav = nav;
    return nav;
  }

  consumeCrossPress() {
    if (!this.crossJustPressed) return false;
    this.crossJustPressed = false;
    return true;
  }

  consumeOptionsPress() {
    if (!this.optionsJustPressed) return false;
    this.optionsJustPressed = false;
    return true;
  }

  consumeAnyButtonEdge() {
    if (!this.anyButtonJustPressed) return false;
    this.anyButtonJustPressed = false;
    return true;
  }

  consumeConfirmPress() {
    return this.consumeCrossPress() || this.consumeOptionsPress();
  }

  consumeStartPress() {
    return this.consumeConfirmPress();
  }

  refreshHud() {
    const active = this._selectNativePad(false);
    const any = JoystickInput.findAnyPad();
    if (active) {
      this.connected = true;
      this.activated = true;
      this.padLabel = active.id || "Gamepad";
      this.padIndex = active.index;
      this._activePadIndex = active.index;
    } else if (any) {
      this.connected = true;
      this.activated = false;
      this.padLabel = any.id || "Gamepad";
      this.padIndex = any.index;
    } else if (!this._phaserPad) {
      this.connected = false;
      this.activated = false;
      this.padLabel = "";
      this.padIndex = -1;
      this._activePadIndex = null;
    }
    updatePadStatus(this);
  }
}

function updatePadStatus(joy) {
  const el = document.getElementById("pad-status");
  if (!el || !joy) return;

  if (!navigator.getGamepads) {
    el.textContent = "Gamepad API недоступен — Chrome/Edge";
    el.className = "pad-status off";
    return;
  }

  if (joy.activated) {
    const short = (joy.padLabel || "Gamepad").replace(/\s+/g, " ").slice(0, 42);
    const index = joy.padIndex >= 0 ? ` #${joy.padIndex + 1}` : "";
    el.textContent = `Джойстик${index}: ${short} — Cross = действие`;
    el.className = "pad-status ok";
    return;
  }

  if (joy.connected) {
    const short = (joy.padLabel || "Gamepad").replace(/\s+/g, " ").slice(0, 36);
    const index = joy.padIndex >= 0 ? ` #${joy.padIndex + 1}` : "";
    el.textContent = `Джойстик${index}: ${short} — нажмите любую кнопку`;
    el.className = "pad-status warn";
    return;
  }

  el.textContent = "Джойстик: нажмите любую кнопку (кликните по экрану)";
  el.className = "pad-status off";
}

function startPadMonitor() {
  const joy = new JoystickInput(0.35);
  window.kopilkaJoystick = joy;

  const tick = () => {
    joy.refreshHud();
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  window.addEventListener("gamepadconnected", (e) => {
    joy.connected = true;
    joy.padLabel = e.gamepad.id || "Gamepad";
    joy.refreshHud();
  });

  window.addEventListener("gamepaddisconnected", () => {
    joy.refreshHud();
  });

  const wake = () => {
    if (navigator.getGamepads) {
      for (const p of navigator.getGamepads()) {
        if (p) void p.buttons.length;
      }
    }
    joy.refreshHud();
  };

  window.addEventListener("pointerdown", wake, { passive: true });
  window.addEventListener("keydown", wake);
  window.addEventListener("focus", wake);
}

window.JoystickInput = JoystickInput;
window.updatePadStatus = updatePadStatus;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startPadMonitor);
} else {
  startPadMonitor();
}
