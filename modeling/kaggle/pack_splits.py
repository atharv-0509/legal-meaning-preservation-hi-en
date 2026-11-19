"""Pack data/splits/ into a base64 tar.gz on stdout (embedded into the Kaggle experiment kernel).

    python modeling/kaggle/pack_splits.py [root] > splits.b64     # root defaults to the repo
"""
import base64
import io
import sys
import tarfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
splits = ROOT / "data" / "splits"
if not splits.exists():
    sys.exit("data/splits does not exist: run src/split.py first")
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tar:
    for p in sorted(splits.rglob("*.jsonl")):
        tar.add(p, arcname=str(p.relative_to(ROOT)).replace("\\", "/"))
sys.stdout.write(base64.b64encode(buf.getvalue()).decode())
