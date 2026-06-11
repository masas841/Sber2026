"""inswapper_128 face-swap engine.

Два пути инференса:
  1. GPU-резидентный конвейер (приём Rope, по умолчанию на CUDA):
     кадр загружается в VRAM ОДИН раз за кадр, кроп лица и вклейка результата
     идут через torch.grid_sample на GPU, io-binding буферы постоянные
     (без numpy↔GPU копий и аллокаций на каждом кадре). Это убирает CPU-warp
     (cv2.warpAffine) и тройной перегон CPU↔GPU, которые съедали ~88% времени.
  2. CPU-fallback (старый путь через cv2.warpAffine) — если torch недоступен.

Препроцессинг identity (latent = emb @ emap) переиспользуем из insightface,
чтобы гарантировать совпадение identity с оригиналом.

Лицензия inswapper — non-commercial (ответственность на операторе).
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class InswapperEngine:
    """inswapper_128 с GPU-резидентным конвейером. Интерфейс:

        eng = InswapperEngine(model_path, providers, device_id=0)
        latent = eng.embed_latent(source_face.normed_embedding)  # 1 раз на гостя
        out = eng.swap(frame_bgr, target_face.kps, latent)       # на каждый кадр
    """

    input_mean: float = 0.0
    input_std: float = 255.0

    def __init__(
        self,
        model_path: Path,
        providers: list,
        device_id: int = 0,
        emap_source_path: Path | None = None,
        gpu_pipeline: bool = True,
    ) -> None:
        import onnx
        import onnxruntime as ort

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"inswapper модель не найдена: {self.model_path}")

        self.device_id = int(device_id)
        self._use_cuda = any(
            (p == "CUDAExecutionProvider")
            or (isinstance(p, (tuple, list)) and p[0] == "CUDAExecutionProvider")
            for p in providers
        )

        # emap нужен для формирования latent. В fp16-версиях модели он часто
        # свёрнут в Constant-узел и недоступен как initializer — тогда берём его
        # из оригинальной fp32-модели (emap одинаков для всех версий inswapper).
        model = onnx.load(str(self.model_path))
        emap = self._extract_emap(model)
        if emap is None and emap_source_path is not None and Path(emap_source_path).exists():
            logger.info("inswapper_fast: emap не найден в %s, беру из %s",
                        self.model_path.name, Path(emap_source_path).name)
            emap = self._extract_emap(onnx.load(str(emap_source_path)))
        if emap is None:
            raise RuntimeError(
                "inswapper: не найден 'emap' ни в модели, ни в fallback. "
                "Укажите emap_source_path к оригинальному inswapper_128.onnx"
            )
        self.emap = emap.astype(np.float32)

        self._sess = ort.InferenceSession(str(self.model_path), providers=providers)
        ins = self._sess.get_inputs()
        outs = self._sess.get_outputs()
        # target = 4D вход (картинка), source = 2D (latent-вектор).
        self._img_name = next(i.name for i in ins if len(i.shape) == 4)
        self._lat_name = next(i.name for i in ins if len(i.shape) == 2)
        self._out_name = outs[0].name
        img_in = next(i for i in ins if i.name == self._img_name)
        self.input_size = int(img_in.shape[2])  # 128
        # fp16 или fp32 по типу входа модели.
        self._fp16 = "float16" in img_in.type

        # torch — только если есть CUDA (io-binding/grid_sample имеют смысл на GPU).
        self._torch = None
        if self._use_cuda:
            try:
                import torch

                torch.set_grad_enabled(False)
                self._torch = torch
            except Exception as exc:  # pragma: no cover
                logger.warning("InswapperEngine: torch недоступен, fallback на run(): %s", exc)
                self._torch = None

        self.gpu_pipeline = bool(gpu_pipeline) and self._torch is not None

        # --- постоянные GPU-ресурсы (аллоцируются один раз) -------------------
        self._io = None              # io_binding, создаётся один раз
        self._img_buf = None         # вход модели (1,3,S,S) — постоянный буфер
        self._out_buf = None         # выход модели (1,3,S,S) — постоянный буфер
        self._lat_buf = None         # latent (1,512) на GPU
        self._lat_id = None          # id() последнего latent (кэш-инвалидация)
        self._frame_buf = None       # кадр (1,3,Hf,Wf) на GPU
        self._frame_hw = None        # (Hf,Wf) текущего буфера кадра
        self._white_crop = None      # (1,1,S,S) для InsightFace paste на GPU

        logger.info(
            "InswapperEngine: size=%d, fp16=%s, gpu_pipeline=%s",
            self.input_size, self._fp16, self.gpu_pipeline,
        )

    # --- emap извлечение -------------------------------------------------------

    @staticmethod
    def _extract_emap(model):
        """Достаёт emap (512x512) из ONNX: сначала как initializer, затем как
        Constant-узел (fp16-модели часто сворачивают emap в Constant)."""
        from onnx import numpy_helper

        for init in model.graph.initializer:
            if init.name == "emap":
                return numpy_helper.to_array(init)
        for init in model.graph.initializer:
            arr = numpy_helper.to_array(init)
            if arr.ndim == 2 and arr.shape == (512, 512):
                return arr
        for node in model.graph.node:
            if node.op_type != "Constant":
                continue
            for attr in node.attribute:
                if attr.name == "value":
                    arr = numpy_helper.to_array(attr.t)
                    if arr.ndim == 2 and arr.shape == (512, 512):
                        return arr
        return None

    # --- identity latent -------------------------------------------------------

    def embed_latent(self, normed_embedding: np.ndarray) -> np.ndarray:
        """latent = normed_embedding @ emap, L2-нормализованный (как в INSwapper)."""
        latent = normed_embedding.reshape((1, -1)).astype(np.float32)
        latent = np.dot(latent, self.emap)
        latent /= np.linalg.norm(latent)
        return latent

    # --- GPU-резидентный конвейер ---------------------------------------------

    def _np_dtype(self):
        return np.float16 if self._fp16 else np.float32

    def _theta(self, M, win, hin, wout, hout):
        """Аффинная матрица M (2x3, output-пиксели → input-пиксели) → theta для
        torch.affine_grid (нормализованные координаты, align_corners=True)."""
        torch = self._torch
        a, b, c = M[0]
        d, e, f = M[1]
        t00 = a * (wout - 1) / (win - 1)
        t01 = b * (hout - 1) / (win - 1)
        t02 = t00 + t01 + 2 * c / (win - 1) - 1
        t10 = d * (wout - 1) / (hin - 1)
        t11 = e * (hout - 1) / (hin - 1)
        t12 = t10 + t11 + 2 * f / (hin - 1) - 1
        return torch.tensor(
            [[[t00, t01, t02], [t10, t11, t12]]],
            dtype=torch.float32, device=self.device_id,
        )

    def _set_latent(self, latent: np.ndarray):
        """Кладёт latent в постоянный GPU-буфер один раз на гостя (по id массива)."""
        torch = self._torch
        if self._lat_id == id(latent) and self._lat_buf is not None:
            return
        dtype = torch.float16 if self._fp16 else torch.float32
        self._lat_buf = torch.from_numpy(latent).to(self.device_id).to(dtype).contiguous()
        self._lat_id = id(latent)
        self._io = None  # latent сменился — перепривяжем io-binding

    def _bind_io(self):
        """Создаёт io_binding ОДИН раз на постоянные буферы img/lat/out."""
        if self._io is not None:
            return
        s = self.input_size
        torch = self._torch
        dtype = torch.float16 if self._fp16 else torch.float32
        if self._img_buf is None:
            self._img_buf = torch.empty((1, 3, s, s), dtype=dtype, device=self.device_id).contiguous()
            self._out_buf = torch.empty((1, 3, s, s), dtype=dtype, device=self.device_id).contiguous()
        nd = self._np_dtype()
        io = self._sess.io_binding()
        io.bind_input(name=self._img_name, device_type="cuda", device_id=self.device_id,
                      element_type=nd, shape=(1, 3, s, s), buffer_ptr=self._img_buf.data_ptr())
        io.bind_input(name=self._lat_name, device_type="cuda", device_id=self.device_id,
                      element_type=nd, shape=tuple(self._lat_buf.shape), buffer_ptr=self._lat_buf.data_ptr())
        io.bind_output(name=self._out_name, device_type="cuda", device_id=self.device_id,
                       element_type=nd, shape=(1, 3, s, s), buffer_ptr=self._out_buf.data_ptr())
        self._io = io

    def _ensure_white_crop(self):
        torch = self._torch
        if self._white_crop is not None:
            return
        s = self.input_size
        self._white_crop = torch.full(
            (1, 1, s, s), 255.0, dtype=torch.float32, device=self.device_id
        )

    def _paste_gpu_diff_tensors(
        self,
        frame_t,
        crop_bgr,
        fake_bgr,
        M: np.ndarray,
        hf: int,
        wf: int,
    ):
        """GPU diff-paste → tensor (1,3,H,W)."""
        import torch.nn.functional as F

        from app.config import settings
        from app.generators.face_workspace import paste_crop_diff_gpu

        s = int(crop_bgr.shape[2])
        Minv = cv2.invertAffineTransform(M)
        theta_paste = self._theta(Minv, wf, hf, s, s)
        grid_paste = F.affine_grid(theta_paste, (1, 3, hf, wf), align_corners=True)
        diff_amount = float(getattr(settings, "ref_video_diff_amount", 10.0))
        return paste_crop_diff_gpu(
            frame_t,
            crop_bgr,
            fake_bgr,
            grid_paste,
            diff_amount=diff_amount,
            diff_thresh=10.0,
        )

    def _paste_gpu_diff(
        self,
        frame_t,
        crop_bgr,
        fake_bgr,
        M: np.ndarray,
        hf: int,
        wf: int,
    ) -> np.ndarray:
        from app.generators.face_workspace import numpy_from_frame_tensor

        return numpy_from_frame_tensor(
            self._paste_gpu_diff_tensors(frame_t, crop_bgr, fake_bgr, M, hf, wf)
        )

    def _swap_gpu_rope_v1(
        self,
        frame_t,
        frame_bgr: np.ndarray,
        crop_bgr,
        fake_bgr,
        M128: np.ndarray,
        kps: np.ndarray,
        hf: int,
        wf: int,
        gfpgan=None,
        restore_weight: float = 0.5,
    ) -> np.ndarray:
        """rope_v1: diff-paste; при gfpgan — restore 512 ONNX до вклейки."""
        import torch.nn.functional as F

        from app.generators.face_workspace import numpy_from_frame_tensor

        if gfpgan is None:
            from app.config import settings

            use_cpu_paste = bool(getattr(settings, "ref_video_swap_cpu_paste", True))
            restore_eng = (
                getattr(settings, "ref_video_restore_engine", "facexlib") or "facexlib"
            ).strip().lower()
            if use_cpu_paste or restore_eng == "facexlib":
                return self._paste_from_gpu_crops(frame_bgr, crop_bgr, fake_bgr, M128)
            try:
                return self._paste_gpu_diff(frame_t, crop_bgr, fake_bgr, M128, hf, wf)
            except RuntimeError as exc:
                logger.warning("GPU diff-paste failed (%s), CPU fallback", exc)
                return self._paste_from_gpu_crops(frame_bgr, crop_bgr, fake_bgr, M128)

        # Полностью GPU (приём Rope): GFPGAN ONNX 512 → diff-paste 512 на тензорах,
        # без возврата на CPU и без parsenet. norm_crop-матрица similarity линейна
        # по размеру кропа, поэтому M512 = M128 * (512/128) — без повторного
        # norm_crop2 на CPU.
        ws = 512
        s = self.input_size
        fake_512 = F.interpolate(
            fake_bgr,
            size=(ws, ws),
            mode="bilinear",
            align_corners=False,
        )
        if fake_512.device != gfpgan._device:
            fake_512 = fake_512.to(gfpgan._device)
        restored = gfpgan.restore_blend_bgr(fake_512, blend=restore_weight)
        if restored.dim() == 3:
            restored = restored.unsqueeze(0)
        if restored.device != frame_t.device:
            restored = restored.to(frame_t.device)

        M512 = (M128.astype(np.float32)) * (float(ws) / float(s))
        # Оригинальный кроп 512 на GPU (для diff-маски вклейки).
        Minv512 = cv2.invertAffineTransform(M512)
        theta_crop = self._theta(Minv512, wf, hf, ws, ws)
        grid_crop = F.affine_grid(theta_crop, (1, 3, ws, ws), align_corners=True)
        orig_512 = F.grid_sample(
            frame_t, grid_crop, mode="bilinear", padding_mode="border", align_corners=True
        )

        # Face parser (приём VisoMaster): в зонах глаз/рта возвращаем оригинал
        # референса поверх свопа — чёткие зубы и живой взгляд без артефактов GFPGAN.
        parser = getattr(self, "_rope_parser", None)
        if parser is not None:
            try:
                from app.config import settings
                from app.generators.face_parser_onnx import (
                    BROW_CLASSES,
                    EYE_CLASSES,
                    MOUTH_CLASSES,
                )

                eyes_on = bool(getattr(settings, "ref_video_parser_eyes", True))
                classes: tuple[int, ...] = ()
                if eyes_on:
                    classes = classes + EYE_CLASSES
                if bool(getattr(settings, "ref_video_parser_mouth", True)):
                    classes = classes + MOUTH_CLASSES
                # Брови всегда от свопа (гостя): иначе feather глаз дублирует бровь.
                exclude = BROW_CLASSES if eyes_on else ()
                if classes:
                    strength = float(getattr(settings, "ref_video_parser_strength", 0.8))
                    feather = int(getattr(settings, "ref_video_parser_feather", 6))
                    pmask = parser.region_mask(
                        orig_512, classes, feather=feather, exclude=exclude
                    )
                    if pmask.device != restored.device:
                        pmask = pmask.to(restored.device)
                    pmask = pmask * strength
                    restored = restored * (1.0 - pmask) + orig_512 * pmask
            except Exception as exc:
                logger.warning("face parser mask skip: %s", exc)

        try:
            pasted = self._paste_gpu_diff_tensors(
                frame_t, orig_512, restored, M512, hf, wf
            )
            return numpy_from_frame_tensor(pasted)
        except RuntimeError as exc:
            logger.warning("GPU diff-paste 512 failed (%s), CPU fallback", exc)
            from insightface.utils import face_align

            aimg_512, M512cpu = face_align.norm_crop2(frame_bgr, kps, ws)
            bgr_fake_512 = (
                restored.squeeze(0).clamp(0, 255).permute(1, 2, 0).byte().cpu().numpy()
            )
            return self._paste_back_insightface(
                frame_bgr, bgr_fake_512, aimg_512, M512cpu
            )

    def _paste_from_gpu_crops(
        self,
        frame_bgr: np.ndarray,
        crop_bgr,
        fake_bgr,
        M: np.ndarray,
    ) -> np.ndarray:
        """Diff-paste InsightFace на CPU (кропы уже на GPU). Совместимо с любым размером кадра."""
        aimg = (
            crop_bgr.clamp(0, 255)
            .squeeze(0)
            .permute(1, 2, 0)
            .byte()
            .cpu()
            .numpy()
        )
        bgr_fake = (
            fake_bgr.clamp(0, 255)
            .squeeze(0)
            .permute(1, 2, 0)
            .byte()
            .cpu()
            .numpy()
        )
        return self._paste_back_insightface(frame_bgr, bgr_fake, aimg, M)

    def _paste_gpu_insightface(
        self,
        frame_t,
        fake_bgr,
        M: np.ndarray,
        hf: int,
        wf: int,
    ):
        """InsightFace paste на GPU: без cv2.warpAffine на полном кадре (как Rope)."""
        import torch.nn.functional as F

        torch = self._torch
        s = self.input_size
        self._ensure_white_crop()

        theta_paste = self._theta(M, s, s, wf, hf)
        grid_paste = F.affine_grid(theta_paste, (1, 3, hf, wf), align_corners=True)

        warped_fake = F.grid_sample(
            fake_bgr, grid_paste, mode="bilinear", padding_mode="zeros", align_corners=True
        )
        warped_white = F.grid_sample(
            self._white_crop.expand(1, 3, s, s),
            grid_paste,
            mode="bilinear",
            padding_mode="zeros",
            align_corners=True,
        )
        alpha = warped_white[:, :1, :, :]
        alpha = torch.where(alpha > 20.0, torch.ones_like(alpha), alpha / 255.0)

        # erosion + blur (аналог cv2.erode + GaussianBlur в insightface paste)
        k = 11
        pad = k // 2
        alpha = 1.0 - F.max_pool2d(1.0 - alpha, kernel_size=k, stride=1, padding=pad)
        alpha = F.avg_pool2d(alpha, kernel_size=11, stride=1, padding=5)

        out = warped_fake * alpha + frame_t * (1.0 - alpha)
        return out.clamp(0, 255).squeeze(0).permute(1, 2, 0).to(torch.uint8).cpu().numpy()

    def _frame_tensor(self, frame_bgr: np.ndarray):
        """Реиспользуем GPU-буфер кадра при том же разрешении."""
        torch = self._torch
        hf, wf = frame_bgr.shape[:2]
        if self._frame_hw == (hf, wf) and self._frame_buf is not None:
            self._frame_buf.copy_(
                torch.from_numpy(frame_bgr)
                .to(self.device_id)
                .permute(2, 0, 1)
                .unsqueeze(0)
                .float()
            )
            return self._frame_buf
        self._frame_hw = (hf, wf)
        self._frame_buf = (
            torch.from_numpy(frame_bgr)
            .to(self.device_id)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .float()
        )
        return self._frame_buf

    def _swap_gpu(
        self,
        frame_bgr: np.ndarray,
        M: np.ndarray,
        latent: np.ndarray,
        kps: np.ndarray | None = None,
    ) -> np.ndarray:
        import torch.nn.functional as F

        torch = self._torch
        s = self.input_size
        hf, wf = frame_bgr.shape[:2]

        self._set_latent(latent)
        self._bind_io()

        frame_t = self._frame_tensor(frame_bgr)

        Minv = cv2.invertAffineTransform(M)
        theta_crop = self._theta(Minv, wf, hf, s, s)
        grid_crop = F.affine_grid(theta_crop, (1, 3, s, s), align_corners=True)
        crop_bgr = F.grid_sample(
            frame_t, grid_crop, mode="bilinear", padding_mode="border", align_corners=True
        )

        model_dtype = torch.float16 if self._fp16 else torch.float32
        img_rgb = (crop_bgr[:, [2, 1, 0], :, :] / 255.0).to(model_dtype)
        self._img_buf.copy_(img_rgb)

        self._sess.run_with_iobinding(self._io)

        fake_bgr = (self._out_buf.float()[:, [2, 1, 0], :, :]).clamp(0, 1) * 255.0

        from app.config import settings

        pipeline = (getattr(settings, "ref_video_pipeline", "legacy") or "legacy").strip().lower()
        if pipeline == "rope_v1" and kps is not None:
            return self._swap_gpu_rope_v1(
                frame_t,
                frame_bgr,
                crop_bgr,
                fake_bgr,
                M,
                kps,
                hf,
                wf,
                getattr(self, "_rope_gfpgan", None),
                float(getattr(self, "_rope_restore_weight", 0.5)),
            )

        if getattr(settings, "ref_video_gpu_paste", False):
            return self._paste_gpu_insightface(frame_t, fake_bgr, M, hf, wf)

        # Качество: diff-маска InsightFace на CPU (только кроп 128×128 с GPU, без квадрата).
        aimg = crop_bgr.clamp(0, 255).squeeze(0).permute(1, 2, 0).byte().cpu().numpy()
        bgr_fake = fake_bgr.squeeze(0).permute(1, 2, 0).byte().cpu().numpy()
        return self._paste_back_insightface(frame_bgr, bgr_fake, aimg, M)

    # --- CPU-fallback инференс -------------------------------------------------

    def _run_cpu(self, blob: np.ndarray, latent: np.ndarray) -> np.ndarray:
        feed_dtype = self._np_dtype()
        pred = self._sess.run(
            [self._out_name],
            {self._img_name: blob.astype(feed_dtype), self._lat_name: latent.astype(feed_dtype)},
        )[0]
        return np.asarray(pred, dtype=np.float32)

    def _swap_cpu(self, frame_bgr: np.ndarray, M: np.ndarray, aimg: np.ndarray,
                  latent: np.ndarray) -> np.ndarray:
        blob = cv2.dnn.blobFromImage(
            aimg, 1.0 / self.input_std, (self.input_size, self.input_size),
            (self.input_mean,) * 3, swapRB=True,
        )
        pred = self._run_cpu(blob, latent)[0]
        img_fake = np.transpose(pred, (1, 2, 0))
        img_fake = np.clip(img_fake * 255.0, 0, 255).astype(np.uint8)
        bgr_fake = cv2.cvtColor(img_fake, cv2.COLOR_RGB2BGR)
        return self._paste_back_insightface(frame_bgr, bgr_fake, aimg, M)

    # --- публичный swap --------------------------------------------------------

    def swap(
        self,
        frame_bgr: np.ndarray,
        kps: np.ndarray,
        latent: np.ndarray,
        *,
        gfpgan=None,
        restore_weight: float = 0.5,
        parser=None,
    ) -> np.ndarray:
        from insightface.utils import face_align

        self._rope_gfpgan = gfpgan
        self._rope_restore_weight = restore_weight
        self._rope_parser = parser

        if self.gpu_pipeline:
            M = face_align.estimate_norm(kps, self.input_size)
            return self._swap_gpu(frame_bgr, M, latent, kps=kps)

        aimg, M = face_align.norm_crop2(frame_bgr, kps, self.input_size)
        return self._swap_cpu(frame_bgr, M, aimg, latent)

    def swap_cpu_ref(self, frame_bgr: np.ndarray, kps: np.ndarray, latent: np.ndarray) -> np.ndarray:
        """CPU-путь явно (эталон для A/B-проверки корректности GPU-конвейера)."""
        from insightface.utils import face_align

        aimg, M = face_align.norm_crop2(frame_bgr, kps, self.input_size)
        return self._swap_cpu(frame_bgr, M, aimg, latent)

    @staticmethod
    def _paste_back_insightface(
        frame_bgr: np.ndarray,
        bgr_fake: np.ndarray,
        aimg: np.ndarray,
        M: np.ndarray,
    ) -> np.ndarray:
        """Вклейка как в insightface.model_zoo.inswapper (diff-маска, без квадрата/овала)."""
        h, w = frame_bgr.shape[:2]
        crop_size = aimg.shape[0]

        fake_diff = np.abs(bgr_fake.astype(np.float32) - aimg.astype(np.float32)).mean(axis=2)
        fake_diff[:2, :] = 0
        fake_diff[-2:, :] = 0
        fake_diff[:, :2] = 0
        fake_diff[:, -2:] = 0

        inv = cv2.invertAffineTransform(M)
        warped_fake = cv2.warpAffine(bgr_fake, inv, (w, h), borderValue=0.0)
        img_white = np.full((crop_size, crop_size), 255, dtype=np.float32)
        warped_white = cv2.warpAffine(img_white, inv, (w, h), borderValue=0.0)
        warped_diff = cv2.warpAffine(fake_diff, inv, (w, h), borderValue=0.0)

        warped_white[warped_white > 20] = 255
        fthresh = 10
        warped_diff[warped_diff < fthresh] = 0
        warped_diff[warped_diff >= fthresh] = 255
        img_mask = warped_white

        mask_h_inds, mask_w_inds = np.where(img_mask == 255)
        if len(mask_h_inds) > 0 and len(mask_w_inds) > 0:
            mask_h = int(np.max(mask_h_inds) - np.min(mask_h_inds))
            mask_w = int(np.max(mask_w_inds) - np.min(mask_w_inds))
            mask_size = int(np.sqrt(max(mask_h * mask_w, 1)))
            k = max(mask_size // 10, 10)
            kernel = np.ones((k, k), np.uint8)
            img_mask = cv2.erode(img_mask, kernel, iterations=1)
            kernel = np.ones((2, 2), np.uint8)
            warped_diff = cv2.dilate(warped_diff, kernel, iterations=1)
            k = max(mask_size // 20, 5)
            blur_size = (2 * k + 1, 2 * k + 1)
            img_mask = cv2.GaussianBlur(img_mask, blur_size, 0)
            k = 5
            blur_size = (2 * k + 1, 2 * k + 1)
            warped_diff = cv2.GaussianBlur(warped_diff, blur_size, 0)

        img_mask = (img_mask / 255.0)[..., np.newaxis]
        out = img_mask * warped_fake.astype(np.float32) + (1.0 - img_mask) * frame_bgr.astype(
            np.float32
        )
        return np.clip(out, 0, 255).astype(np.uint8)

    @staticmethod
    def _paste_back(
        frame_bgr: np.ndarray,
        swapped_crop: np.ndarray,
        M: np.ndarray,
        aimg: np.ndarray | None = None,
    ) -> np.ndarray:
        """Совместимость: swapped_crop + исходный aimg → diff-paste InsightFace."""
        src = aimg if aimg is not None else swapped_crop
        return InswapperEngine._paste_back_insightface(frame_bgr, swapped_crop, src, M)
