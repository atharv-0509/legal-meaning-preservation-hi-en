"""Minimal Kaggle kernels client (standard library only): push a script kernel, poll its status, fetch its log.

    python modeling/kaggle/kaggle_client.py push --user <kaggle-user> --slug lmp-frjudge-repro \
        --script modeling/kaggle/frjudge_repro.py --set __COMMIT__=$(git rev-parse HEAD) --set __CONFIGS__=all
    python modeling/kaggle/kaggle_client.py status --user <kaggle-user> --slug lmp-frjudge-repro
    python modeling/kaggle/kaggle_client.py log --user <kaggle-user> --slug lmp-frjudge-repro --out log.txt
    python modeling/kaggle/kaggle_client.py unpack --log log.txt --dest modeling/       # -> modeling/runs/...

Authentication: HTTP basic auth with the Kaggle username and API key (kaggle.json). Set KAGGLE_USERNAME and
KAGGLE_KEY, or run where a proxy injects the credential for www.kaggle.com (then no variables are needed).
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.kaggle.com/api/v1"


def _env(name: str) -> str | None:
    """Environment variable, falling back to the Windows *user* environment (HKCU\\Environment), so a
    terminal opened before the variable was set still sees it."""
    v = os.environ.get(name)
    if v or sys.platform != "win32":
        return v
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0] or None
    except OSError:
        return None


def auth_header() -> str | None:
    """New-style Kaggle API tokens ("KGAT_...", or KAGGLE_API_TOKEN) use Bearer auth; legacy
    kaggle.json keys use HTTP basic auth with the username."""
    token = _env("KAGGLE_API_TOKEN")
    key = _env("KAGGLE_KEY")
    if token or (key and key.startswith("KGAT_")):
        return f"Bearer {token or key}"
    user = _env("KAGGLE_USERNAME")
    if user and key:
        return "Basic " + base64.b64encode(f"{user}:{key}".encode()).decode()
    return None


def call(method: str, path: str, body: dict | None = None, params: dict | None = None) -> dict:
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    hdr = auth_header()
    if hdr:
        req.add_header("Authorization", hdr)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {path}: {e.read().decode()[:500]}")


def push(args):
    text = open(args.script, encoding="utf-8").read()
    for kv in args.set or []:
        k, v = kv.split("=", 1)
        text = text.replace(k, v)
    for kv in args.set_file or []:          # large values (e.g. an embedded data bundle) come from a file
        k, path = kv.split("=", 1)
        text = text.replace(k, open(path, encoding="utf-8").read().strip())
    body = {
        "slug": f"{args.user}/{args.slug}", "newTitle": args.title or args.slug, "text": text,
        "language": "python", "kernelType": "script", "isPrivate": True,
        "enableGpu": not args.cpu, "enableTpu": False, "enableInternet": True,
        "datasetDataSources": [], "competitionDataSources": [], "kernelDataSources": list(args.kernel_source or []),
        "modelDataSources": [], "categoryIds": [],
    }
    if not args.cpu and args.machine:
        body["machineShape"] = args.machine
    print(json.dumps(call("POST", "/kernels/push", body), indent=1))


def status(args):
    print(json.dumps(call("GET", "/kernels/status", params={"userName": args.user, "kernelSlug": args.slug})))


def log(args):
    out = call("GET", "/kernels/output", params={"userName": args.user, "kernelSlug": args.slug})
    raw = out.get("log") or ""
    try:                                   # Kaggle returns the log as a JSON list of {stream_name, data}
        text = "".join(x.get("data", "") for x in json.loads(raw))
    except (json.JSONDecodeError, TypeError, AttributeError):
        text = raw
    files = [f.get("fileName") for f in out.get("files", [])]
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text)
        print(f"log: {len(text)} chars -> {args.out}; output files: {files}")
    else:
        print(text[-args.tail:] if args.tail else text)


def unpack(args):
    text = open(args.log, encoding="utf-8").read()
    m = re.search(r"===== RUNS_TGZ_B64_BEGIN \d+ =====\n(.*?)\n===== RUNS_TGZ_B64_END", text, re.S)
    if not m:
        sys.exit("no runs bundle in log")
    data = base64.b64decode("".join(m.group(1).split()))
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        members = [t for t in tar.getmembers() if t.isfile() and not t.name.startswith(("/", "..")) and ".." not in t.name]
        tar.extractall(args.dest, members=members)
    print(f"unpacked {len(members)} files into {args.dest}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("push")
    p.add_argument("--user", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--title")
    p.add_argument("--script", required=True)
    p.add_argument("--set", action="append", help="PLACEHOLDER=value substitutions in the script")
    p.add_argument("--set-file", action="append", help="PLACEHOLDER=path: substitute the file's contents")
    p.add_argument("--machine", default="NvidiaTeslaT4", help="Kaggle machine shape (GPU)")
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--kernel-source", action="append", help="<user>/<kernel-slug> whose output is mounted under /kaggle/input")
    p.set_defaults(fn=push)
    for name, fn in (("status", status), ("log", log)):
        q = sub.add_parser(name)
        q.add_argument("--user", required=True)
        q.add_argument("--slug", required=True)
        if name == "log":
            q.add_argument("--out")
            q.add_argument("--tail", type=int, default=3000)
        q.set_defaults(fn=fn)
    u = sub.add_parser("unpack")
    u.add_argument("--log", required=True)
    u.add_argument("--dest", default="modeling")
    u.set_defaults(fn=unpack)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
