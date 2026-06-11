"""Автономный тест stride-логики GFPGAN (без torch/gfpgan).

Проверяет _restore_strided: число кадров на выходе == входу, порядок сохранён,
keyframe'ы прогоняются через restorer каждые every_n, интерполяция корректна.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import face_restore as fr


class FakeCap:
    """Отдаёт заранее заданный список кадров через read()."""

    def __init__(self, frames):
        self._frames = list(frames)
        self._i = 0

    def read(self):
        if self._i >= len(self._frames):
            return False, None
        f = self._frames[self._i]
        self._i += 1
        return True, f


class FakeWriter:
    def __init__(self):
        self.frames = []

    def write(self, frame):
        self.frames.append(frame.copy())


class FakeRestorer:
    """enhance() прибавляет +10 ко всем пикселям (имитация «улучшения»)."""

    def __init__(self):
        self.calls = 0

    def enhance(self, frame_bgr, **kwargs):
        self.calls += 1
        restored = np.clip(frame_bgr.astype(np.int32) + 10, 0, 255).astype(np.uint8)
        return None, None, restored


def _make_frames(n, h=8, w=8):
    # Каждый кадр заполнен своим значением i (0..n-1), чтобы отслеживать порядок.
    return [np.full((h, w, 3), i, dtype=np.uint8) for i in range(n)]


def test_count_and_order():
    for n in (1, 5, 7, 10, 13):
        for every_n in (1, 2, 3, 4):
            for interp in (True, False):
                frames = _make_frames(n)
                cap = FakeCap(frames)
                writer = FakeWriter()
                restorer = FakeRestorer()
                written, restored = fr._restore_strided(
                    cap, writer, restorer, every_n, interp
                )
                assert written == n, f"n={n} every={every_n}: written {written} != {n}"
                assert len(writer.frames) == n, "writer count mismatch"
                expected_keys = len(range(0, n, every_n))
                assert restored == expected_keys, (
                    f"n={n} every={every_n}: restored {restored} != {expected_keys}"
                )
                # Базовое значение каждого выходного кадра (минус residual) должно
                # соответствовать порядковому номеру i (residual >= 0 у нас).
                for i, out in enumerate(writer.frames):
                    base = int(out[0, 0, 0])
                    # residual в диапазоне 0..10, поэтому base ∈ [i, i+10]
                    assert i <= base <= i + 10, (
                        f"n={n} every={every_n} interp={interp}: "
                        f"frame {i} base {base} вне [i, i+10]"
                    )
    print("test_count_and_order: OK")


def test_keyframe_full_enhance():
    # every_n=3, n=7 → keyframes 0,3,6 полностью +10
    frames = _make_frames(7)
    cap = FakeCap(frames)
    writer = FakeWriter()
    restorer = FakeRestorer()
    fr._restore_strided(cap, writer, restorer, 3, True)
    for k in (0, 3, 6):
        assert int(writer.frames[k][0, 0, 0]) == k + 10, (
            f"keyframe {k} должен быть полностью улучшен (+10)"
        )
    print("test_keyframe_full_enhance: OK")


def test_interpolation_monotonic():
    # Между двумя keyframe'ами residual растёт линейно от prev к next (оба +10),
    # значит промежуточные тоже ~+10. Проверяем, что residual в пределах [0,10].
    frames = _make_frames(7)
    cap = FakeCap(frames)
    writer = FakeWriter()
    restorer = FakeRestorer()
    fr._restore_strided(cap, writer, restorer, 3, True)
    for i, out in enumerate(writer.frames):
        residual = int(out[0, 0, 0]) - i
        assert 0 <= residual <= 10, f"frame {i}: residual {residual} вне [0,10]"
    print("test_interpolation_monotonic: OK")


if __name__ == "__main__":
    test_count_and_order()
    test_keyframe_full_enhance()
    test_interpolation_monotonic()
    print("ALL OK")
