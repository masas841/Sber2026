"""SimSwap 512 face-swap engine (ONNX).

Отдельный движок свопа на нативные 512x512 — альтернатива inswapper_128.
В отличие от inswapper (InsightFace model_zoo), SimSwap имеет свой пайплайн:

  1) identity-вектор источника берётся из ArcFace (отдельная ONNX-модель,
     вход 112x112 RGB), L2-нормализуется;
  2) кадр-цель выравнивается по arcface-шаблону на 512x512 (warpAffine);
  3) SimSwap-ONNX принимает выровненный кроп (NCHW, RGB, /255) + identity-вектор,
     возвращает свопнутое лицо 512x512;
  4) результат вклеивается обратно по обратной аффинной матрице с мягкой маской.

ВНИМАНИЕ (валидировать через scripts/probe_swapper.py перед продом):
  Точные имена входов и нормализация зависят от конкретного simswap_512_beta.onnx.
  Параметры нормализации вынесены в поля движка — если на probe выход «мусорный»,
  меняем SIMSWAP_INPUT_MEAN/STD и порядок каналов, не трогая остальную логику.

Лицензия SimSwap — non-commercial (ответственность за использование на стороне
оператора, см. обсуждение в задаче).
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Шаблон выравнивания ArcFace (5 точек, база 112x112) — стандартный для InsightFace/SimSwap.
# Масштабируется под нужный размер кропа в _build_align_matrix.
ARCFACE_5PT_112 = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


class SimSwapEngine:
    """Загрузка SimSwap-512 + ArcFace и покадровый своп лица.

    Использование (в ref_video.py):
        engine = SimSwapEngine(model_path, arcface_path, providers)
        src_id = engine.embed_identity(src_bgr, src_face_kps)   # один раз на гостя
        out = engine.swap(frame_bgr, target_face_kps, src_id)   # на каждый кадр
    """

    # Размер кропа SimSwap (нативный выход модели).
    crop_size: int = 512
    # Нормализация входа SimSwap. Для большинства SimSwap-ONNX: просто /255 (mean=0,std=1).
    # Если probe даст «мусор» — типичные альтернативы: mean=0.5/std=0.5 или ImageNet.
    input_mean: float = 0.0
    input_std: float = 1.0

    def __init__(
        self,
        model_path: Path,
        arcface_path: Path,
        providers: list,
    ) -> None:
        import onnxruntime as ort

        self.model_path = Path(model_path)
        self.arcface_path = Path(arcface_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"SimSwap модель не найдена: {self.model_path}")
        if not self.arcface_path.exists():
            raise FileNotFoundError(f"ArcFace модель не найдена: {self.arcface_path}")

        self._sess = ort.InferenceSession(str(self.model_path), providers=providers)
        self._arcface = ort.InferenceSession(str(self.arcface_path), providers=providers)

        # SimSwap обычно имеет 2 входа: target-image (NCHW 512) и source-identity (вектор).
        self._inputs = {i.name: i for i in self._sess.get_inputs()}
        self._img_input = self._pick_image_input()
        self._id_input = self._pick_identity_input()
        self._arcface_input = self._arcface.get_inputs()[0].name
        logger.info(
            "SimSwap loaded: img_input=%s, id_input=%s, arcface_input=%s",
            self._img_input,
            self._id_input,
            self._arcface_input,
        )

    # --- разбор входов ONNX ---------------------------------------------------

    def _pick_image_input(self) -> str:
        """Вход-картинка: 4D тензор (N,C,H,W)."""
        for name, inp in self._inputs.items():
            shape = inp.shape
            if len(shape) == 4:
                return name
        raise RuntimeError(
            f"SimSwap: не найден 4D вход-картинка среди {list(self._inputs)}"
        )

    def _pick_identity_input(self) -> str:
        """Вход-идентичность: 2D тензор (N, D), напр. (1, 512)."""
        for name, inp in self._inputs.items():
            if name == self._img_input:
                continue
            if len(inp.shape) == 2:
                return name
        # fallback: первый вход, не являющийся картинкой
        for name in self._inputs:
            if name != self._img_input:
                return name
        raise RuntimeError(
            f"SimSwap: не найден вход-идентичность среди {list(self._inputs)}"
        )

    # --- выравнивание лица ----------------------------------------------------

    @staticmethod
    def _build_align_matrix(kps: np.ndarray, out_size: int) -> np.ndarray:
        """Аффинная матрица выравнивания 5 точек лица под arcface-шаблон out_size."""
        dst = ARCFACE_5PT_112 * (out_size / 112.0)
        src = np.asarray(kps, dtype=np.float32)
        matrix, _ = cv2.estimateAffinePartial2D(
            src, dst, method=cv2.LMEDS
        )
        if matrix is None:
            raise RuntimeError("SimSwap: не удалось построить матрицу выравнивания")
        return matrix

    def _warp_face(self, frame_bgr: np.ndarray, kps: np.ndarray, out_size: int):
        matrix = self._build_align_matrix(kps, out_size)
        crop = cv2.warpAffine(
            frame_bgr, matrix, (out_size, out_size), borderMode=cv2.BORDER_REPLICATE
        )
        return crop, matrix

    # --- identity (ArcFace) ---------------------------------------------------

    def embed_identity(self, frame_bgr: np.ndarray, kps: np.ndarray) -> np.ndarray:
        """Identity-вектор источника для SimSwap из ArcFace (вход 112 RGB, /127.5-1)."""
        crop, _ = self._warp_face(frame_bgr, kps, 112)
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32)
        rgb = (rgb - 127.5) / 127.5
        blob = np.transpose(rgb, (2, 0, 1))[np.newaxis, ...].astype(np.float32)
        emb = self._arcface.run(None, {self._arcface_input: blob})[0]
        emb = emb.reshape(1, -1).astype(np.float32)
        norm = np.linalg.norm(emb, axis=1, keepdims=True)
        norm[norm == 0] = 1.0
        return emb / norm

    # --- основной своп --------------------------------------------------------

    def swap(
        self,
        frame_bgr: np.ndarray,
        kps: np.ndarray,
        source_identity: np.ndarray,
    ) -> np.ndarray:
        """Свопнуть лицо в кадре на источник (по identity-вектору)."""
        crop, matrix = self._warp_face(frame_bgr, kps, self.crop_size)

        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        if self.input_mean != 0.0 or self.input_std != 1.0:
            rgb = (rgb - self.input_mean) / self.input_std
        blob = np.transpose(rgb, (2, 0, 1))[np.newaxis, ...].astype(np.float32)

        out = self._sess.run(
            None,
            {self._img_input: blob, self._id_input: source_identity.astype(np.float32)},
        )[0]

        swapped = out[0]
        # (C,H,W) -> (H,W,C), денормализация обратно в 0..255
        swapped = np.transpose(swapped, (1, 2, 0))
        if self.input_mean != 0.0 or self.input_std != 1.0:
            swapped = swapped * self.input_std + self.input_mean
        swapped = np.clip(swapped * 255.0, 0, 255).astype(np.uint8)
        swapped_bgr = cv2.cvtColor(swapped, cv2.COLOR_RGB2BGR)

        return self._paste_back(frame_bgr, swapped_bgr, matrix)

    @staticmethod
    def _paste_back(
        frame_bgr: np.ndarray, swapped_crop: np.ndarray, matrix: np.ndarray
    ) -> np.ndarray:
        """Вклеить свопнутый кроп обратно по обратной аффинной матрице с мягкой маской."""
        h, w = frame_bgr.shape[:2]
        crop_size = swapped_crop.shape[0]
        inv = cv2.invertAffineTransform(matrix)

        warped = cv2.warpAffine(swapped_crop, inv, (w, h), borderMode=cv2.BORDER_CONSTANT)

        # Мягкая ЭЛЛИПТИЧЕСКАЯ маска: квадратная даёт видимый шов на однотонном фоне.
        # Эллипс вписан в кроп, слегка ужат и размыт → бесшовный овал вокруг лица.
        mask = np.zeros((crop_size, crop_size), dtype=np.uint8)
        center = (crop_size // 2, crop_size // 2)
        axes = (int(crop_size * 0.42), int(crop_size * 0.48))
        cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
        mask = cv2.GaussianBlur(mask, (0, 0), crop_size / 16.0)
        warped_mask = cv2.warpAffine(mask, inv, (w, h), borderMode=cv2.BORDER_CONSTANT)
        alpha = (warped_mask.astype(np.float32) / 255.0)[..., np.newaxis]

        out = warped.astype(np.float32) * alpha + frame_bgr.astype(np.float32) * (1 - alpha)
        return np.clip(out, 0, 255).astype(np.uint8)
