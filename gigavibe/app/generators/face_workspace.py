"""GPU-вклейка свопнутого кропа в кадр (diff-paste InsightFace / Rope).

Используется при REF_VIDEO_PIPELINE=rope_v1 вместо CPU warpAffine на полном кадре.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import torch
import torch.nn.functional as F

from app.generators.face_masks import (
    apply_fake_diff,
    refine_fullframe_mask,
    warp_crop_channel,
    zero_crop_border,
)

if TYPE_CHECKING:
    pass


def paste_crop_diff_gpu(
    frame_t: torch.Tensor,
    crop_bgr: torch.Tensor,
    fake_bgr: torch.Tensor,
    grid_paste: torch.Tensor,
    *,
    diff_amount: float = 10.0,
    diff_thresh: float = 10.0,
) -> torch.Tensor:
    """InsightFace-style diff-paste на GPU.

    frame_t: (1,3,H,W) float 0..255 BGR.
    crop_bgr, fake_bgr: (1,3,S,S) float 0..255 BGR.
    grid_paste: affine_grid для вставки кропа S→(H,W).
    """
    hf, wf = frame_t.shape[2], frame_t.shape[3]
    s = crop_bgr.shape[2]

    orig = crop_bgr[0]
    fake = fake_bgr[0]

    fake_diff = torch.abs(fake - orig).mean(dim=0, keepdim=True)
    fake_diff = zero_crop_border(fake_diff, border=2)

    warped_fake = F.grid_sample(
        fake_bgr,
        grid_paste,
        mode="bilinear",
        padding_mode="zeros",
        align_corners=True,
    )

    white = torch.full((1, 1, s, s), 255.0, device=frame_t.device, dtype=frame_t.dtype)
    warped_white = warp_crop_channel(white, grid_paste, hf, wf)

    warped_diff = warp_crop_channel(
        fake_diff.unsqueeze(0).unsqueeze(0),
        grid_paste,
        hf,
        wf,
    )

    ww = warped_white[:, :1]
    ww = torch.where(ww > 20.0, torch.ones_like(ww), ww / 255.0)

    wd = warped_diff[:, :1]
    wd = torch.where(wd < diff_thresh, torch.zeros_like(wd), torch.ones_like(wd))

    # insightface: dilate warped_diff (2x2) — на промежуточном wd
    wd = F.max_pool2d(wd, kernel_size=2, stride=1, padding=0)
    k5 = 5
    wd = F.avg_pool2d(wd, kernel_size=2 * k5 + 1, stride=1, padding=k5)

    img_mask = refine_fullframe_mask(ww[:, 0], diff_thresh=diff_thresh)

    # Дополнительно: diff-маска Rope на кропе (смягчает жёсткие края 128)
    crop_mask = apply_fake_diff(fake, orig, diff_amount)
    warped_crop_mask = warp_crop_channel(
        crop_mask.unsqueeze(0),
        grid_paste,
        hf,
        wf,
    )
    img_mask = torch.maximum(img_mask, warped_crop_mask[:, :1] * 0.85)

    alpha = img_mask
    out = warped_fake * alpha + frame_t * (1.0 - alpha)
    return out.clamp(0, 255)


def numpy_from_frame_tensor(frame_t: torch.Tensor) -> np.ndarray:
    return (
        frame_t.squeeze(0)
        .permute(1, 2, 0)
        .clamp(0, 255)
        .byte()
        .cpu()
        .numpy()
    )
