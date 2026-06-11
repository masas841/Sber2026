from app.config import settings
from app.generators.ref_video import RefVideoGenerator
from app.face_restore import warmup_model, is_available

RefVideoGenerator._load_models()
print("swap", settings.ref_video_swap_device_id, "onnx", RefVideoGenerator.last_onnx_provider)
if is_available():
    warmup_model()
    print("gfpgan restore_dev", settings.ref_video_restore_device_id)
else:
    print("gfpgan missing")
