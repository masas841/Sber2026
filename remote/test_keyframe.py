import sys
import time
from pathlib import Path

ROOT = Path(r"C:\Users\user\gigavibe")
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402

from app.generators.keyframe_instantid import KeyframeInstantIDGenerator  # noqa: E402

face = ROOT / "data" / "test_face.jpg"
if not face.exists():
    face.parent.mkdir(parents=True, exist_ok=True)
    src = ROOT / "assets" / "driving" / "IMG_9240.MP4"
    cap = cv2.VideoCapture(str(src))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, n // 2))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit(f"cannot read frame from {src}")
    cv2.imwrite(str(face), frame)
    print("extracted test face:", face, flush=True)

print("available:", KeyframeInstantIDGenerator.is_available(), flush=True)
t = time.time()
img = KeyframeInstantIDGenerator().generate_keyframe(face, 720, 1280)
out = ROOT / "data" / "outputs" / "keyframe_test.png"
out.parent.mkdir(parents=True, exist_ok=True)
img.save(out)
print("OK", out, round(time.time() - t, 1), "s", flush=True)
