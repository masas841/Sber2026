import os
from huggingface_hub import HfApi

os.environ.setdefault("HF_TOKEN", os.environ.get("HF_TOKEN", ""))
api = HfApi()
files = api.list_repo_files("Lightricks/LTX-Video", token=os.environ.get("HF_TOKEN") or None)

# Сгруппировать по верхнему уровню (папка или корневой файл)
from collections import defaultdict
groups = defaultdict(list)
for f in files:
    top = f.split("/")[0] if "/" in f else "(root)"
    groups[top].append(f)

for top in sorted(groups):
    print(f"== {top} ({len(groups[top])} files)")
    for f in sorted(groups[top])[:12]:
        print("   ", f)
