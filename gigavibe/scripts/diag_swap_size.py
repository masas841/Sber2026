import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.config import settings
import onnx

p = Path(settings.inswapper_fast_model_path)
if not p.is_absolute():
    p = ROOT / p
for inp in onnx.load(str(p)).graph.input:
    print(inp.name, [d.dim_value or d.dim_param for d in inp.type.tensor_type.shape.dim])
