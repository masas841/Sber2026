from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image


class VideoGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        source_image: Path,
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: int,
        duration_sec: float,
    ) -> Path:
        """Создаёт MP4 из исходного фото."""

    @staticmethod
    def load_and_fit(image_path: Path, width: int, height: int) -> Image.Image:
        img = Image.open(image_path).convert("RGB")
        target_ratio = width / height
        src_ratio = img.width / img.height

        if src_ratio > target_ratio:
            new_w = int(img.height * target_ratio)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, img.height))
        else:
            new_h = int(img.width / target_ratio)
            top = (img.height - new_h) // 2
            img = img.crop((0, top, img.width, top + new_h))

        return img.resize((width, height), Image.Resampling.LANCZOS)
