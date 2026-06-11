"""Маски лица для ref_video (приём Rope / VisoMaster).

apply_fake_diff — diff между свопом и оригиналом в пространстве кропа.
build_paste_mask — эрозия/размытие конверта (аналог insightface paste_back).
"""

from __future__ import annotations

import torch
import torch.nn.functional as F


def apply_fake_diff(
    swapped: torch.Tensor,
    original: torch.Tensor,
    diff_amount: float,
) -> torch.Tensor:
    """Бинарная маска (1, H, W), float 0..1. Как Rope VideoManager.apply_fake_diff.

    swapped, original: (C, H, W) float, BGR 0..255.
    diff_amount: 0..100 (Rope slider); порог = diff_amount * 2.55.
    """
    diff = torch.abs(swapped - original)
    fthresh = float(diff_amount) * 2.55
    diff = torch.where(diff >= fthresh, torch.ones_like(diff), torch.zeros_like(diff))
    diff = diff.sum(dim=0, keepdim=True)
    diff = torch.clamp(diff, 0.0, 1.0)
    return diff


def zero_crop_border(mask: torch.Tensor, border: int = 2) -> torch.Tensor:
    """Обнуляет рамку маски (insightface paste_back). mask: (1,H,W)."""
    if border <= 0:
        return mask
    m = mask.clone()
    b = int(border)
    m[..., :b, :] = 0
    m[..., -b:, :] = 0
    m[..., :, :b] = 0
    m[..., :, -b:] = 0
    return m


def refine_fullframe_mask(
    mask_2d: torch.Tensor,
    diff_thresh: float = 10.0,
) -> torch.Tensor:
    """Эрозия + blur конверта на полном кадре (1,1,H,W), как insightface paste_back.

    mask_2d: (1, H, W) float — warped white или warped diff.
    """
    m = mask_2d.unsqueeze(0) if mask_2d.dim() == 2 else mask_2d
    if m.dim() == 3:
        m = m.unsqueeze(0)

    h_inds = torch.where(m[0, 0] > 0.5)
    if h_inds[0].numel() == 0:
        return m.clamp(0, 1)

    h_min, h_max = h_inds[0].min(), h_inds[0].max()
    w_inds = torch.where(m[0, 0] > 0.5)
    w_min, w_max = w_inds[1].min(), w_inds[1].max()
    mask_h = int(h_max - h_min)
    mask_w = int(w_max - w_min)
    mask_size = int((max(mask_h * mask_w, 1)) ** 0.5)

    k = max(mask_size // 10, 10)
    pad = k // 2
    m = 1.0 - F.max_pool2d(1.0 - m, kernel_size=k, stride=1, padding=pad)

    k2 = 5
    pad2 = k2 // 2
    m = F.avg_pool2d(m, kernel_size=2 * k2 + 1, stride=1, padding=pad2)

    k3 = max(mask_size // 20, 5)
    pad3 = k3 // 2
    m = F.avg_pool2d(m, kernel_size=2 * k3 + 1, stride=1, padding=pad3)
    return m.clamp(0, 1)


def warp_crop_channel(
    crop_chw: torch.Tensor,
    grid_paste: torch.Tensor,
    hf: int,
    wf: int,
) -> torch.Tensor:
    """crop_chw: (1,1,S,S) или (1,C,S,S) → (1,C,hf,wf)."""
    if crop_chw.dim() == 3:
        crop_chw = crop_chw.unsqueeze(0)
    return F.grid_sample(
        crop_chw,
        grid_paste,
        mode="bilinear",
        padding_mode="zeros",
        align_corners=True,
    )
