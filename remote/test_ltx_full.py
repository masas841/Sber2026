import sys
import time
from pathlib import Path

ROOT = Path(r"C:\Users\user\gigavibe")
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.generators.ltx import LtxGenerator  # noqa: E402

face = ROOT / "data" / "test_face.jpg"
out = ROOT / "data" / "outputs" / "ltx_full_test.mp4"
out.parent.mkdir(parents=True, exist_ok=True)

print("keyframe_mode:", settings.keyframe_mode, flush=True)
print("ltx_model_dir:", settings.ltx_model_dir, flush=True)
print("ltx num_frames:", settings.ltx_num_frames, "quality:", settings.ltx_quality, flush=True)

gen = LtxGenerator(
    model_id=settings.ltx_model_id,
    num_frames=settings.ltx_num_frames,
    num_inference_steps=settings.ltx_inference_steps,
    guidance_scale=settings.ltx_guidance_scale,
    distilled=False,
    gguf_repo_file=settings.ltx_gguf_repo_file,
)

t = time.time()
gen.generate(
    face,
    out,
    width=settings.video_width,
    height=settings.video_height,
    fps=settings.video_fps,
    duration_sec=settings.video_duration_sec,
)
print("OK", out, out.stat().st_size, round(time.time() - t, 1), "s", flush=True)
