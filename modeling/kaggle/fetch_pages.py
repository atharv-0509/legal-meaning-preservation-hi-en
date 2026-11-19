"""Kaggle helper: download a public PDF and print its pages as grayscale JPEGs (base64 tar.gz) in the log.

Used for the Hindi OCR spot-check, because the DoPT server resets connections from the cloud machine.

    python modeling/kaggle/kaggle_client.py push --user atharvarora05 --slug lmp-fetch-pages \
        --title "LMP fetch pages" --script modeling/kaggle/fetch_pages.py --cpu \
        --set __URL__=<pdf url> --set __DPI__=100
    python modeling/kaggle/kaggle_client.py log ... --out pages.log      # then decode PAGES_TGZ_B64
"""
import base64
import hashlib
import io
import subprocess
import tarfile
import urllib.request

URL = "__URL__"
DPI = int("__DPI__")
subprocess.run("pip install -q pymupdf", shell=True, check=True)
import fitz  # noqa: E402

data = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "lmp-research"}), timeout=120).read()
print(f"downloaded {len(data)} bytes sha256={hashlib.sha256(data).hexdigest()}")
doc = fitz.open(stream=data, filetype="pdf")
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tar:
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
        jpg = pix.tobytes("jpg", jpg_quality=60)
        info = tarfile.TarInfo(f"page-{i:03d}.jpg")
        info.size = len(jpg)
        tar.addfile(info, io.BytesIO(jpg))
b64 = base64.b64encode(buf.getvalue()).decode()
print(f"pages {len(doc)}; PAGES_TGZ_B64_BEGIN {len(b64)}")
for i in range(0, len(b64), 10000):
    print(b64[i:i + 10000])
print("PAGES_TGZ_B64_END")
