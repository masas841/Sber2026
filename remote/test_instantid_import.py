import sys

sys.path.insert(0, r"C:\Users\user\gigavibe\vendor\instantid")

try:
    from pipeline_stable_diffusion_xl_instantid import (  # noqa
        StableDiffusionXLInstantIDPipeline,
        draw_kps,
    )
    print("IMPORT OK")
except Exception as exc:
    import traceback
    traceback.print_exc()
    print("IMPORT FAIL:", exc)
