"""Step 3: LLM simplifications (`normal` and `aggressive` variants, EN + HI). Resumable.

    LLM_API_KEY=... [LLM_BASE_URL=https://api.openai.com/v1] python src/simplify.py --model <exact-model-id>
    python src/simplify.py --model <id> --limit 10      # trial on the first 10 clauses
    python src/simplify.py --model <id> --dry-run       # print prompts, call nothing

Any OpenAI-compatible /chat/completions endpoint works (OpenAI, Together, Groq, vLLM, Ollama's
/v1, OpenRouter...). Standard library only. Every output row records model, prompt_id,
temperature, top_p, max_tokens, finish_reason and a UTC timestamp (provenance, CLAUDE.md §7).

Generation settings follow JUDGEBERT (temperature 1.0, top_p 0.9). The paper capped output at
100 new tokens; our clauses go up to 90 words and Devanagari costs more tokens, so the defaults
are 200 (EN) / 500 (HI). Rows that hit the cap have finish_reason == "length" and are reported.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import append_jsonl, data_paths, read_jsonl  # noqa: E402
from select_clauses import load_final_clauses  # noqa: E402

# `normal`: the zero-shot simplification prompt of Kew et al. (2023, "BLESS"), which JUDGEBERT
# translated into French. TODO(team): diff this wording against the BLESS paper / JUDGEBERT
# repo before the main run and record any change in the prompt id.
# The Hindi versions are our translations — have a Hindi-speaking team member check them.
PROMPTS = {
    ("en", "normal"): ("bless_en_v1",
        "Please rewrite the following complex sentence in order to make it easier to understand by "
        "non-native speakers of English. You can do so by replacing complex words with simpler synonyms "
        "(i.e. paraphrasing), deleting unimportant information (i.e. compression), and/or splitting a long "
        "complex sentence into several simpler ones. The final simplified sentence needs to be grammatical, "
        "fluent, and retain the main ideas of its original counterpart without altering its meaning.\n\n"
        "Complex: {text}\nSimple:"),
    ("hi", "normal"): ("bless_hi_v1",
        "कृपया निम्नलिखित जटिल वाक्य को इस प्रकार दोबारा लिखिए कि उन लोगों के लिए समझना आसान हो जाए जिनकी "
        "मातृभाषा हिंदी नहीं है। आप कठिन शब्दों को सरल समानार्थी शब्दों से बदल सकते हैं (अर्थात् पुनर्कथन), "
        "कम महत्वपूर्ण जानकारी हटा सकते हैं (अर्थात् संक्षेपण), और/या एक लंबे जटिल वाक्य को कई सरल वाक्यों में "
        "बाँट सकते हैं। अंतिम सरलीकृत वाक्य व्याकरण की दृष्टि से सही और सहज होना चाहिए, और उसे अपने मूल वाक्य "
        "के मुख्य विचारों को उसका अर्थ बदले बिना बनाए रखना चाहिए। उत्तर केवल हिंदी में दीजिए।\n\n"
        "जटिल: {text}\nसरल:"),
    ("en", "aggressive"): ("kid12_en_v1",
        "Explain the following legal text to a 12-year-old in at most 2 sentences. "
        "Write only the explanation.\n\nText: {text}\nExplanation:"),
    ("hi", "aggressive"): ("kid12_hi_v1",
        "निम्नलिखित कानूनी पाठ को 12 साल के बच्चे को अधिकतम 2 वाक्यों में समझाइए। "
        "केवल व्याख्या लिखिए, और उत्तर हिंदी में दीजिए।\n\nपाठ: {text}\nव्याख्या:"),
}
VARIANTS = ("normal", "aggressive")


def sim_id(clause_id: str, lang: str, variant: str) -> str:
    return f"{clause_id}|{lang}|{variant}"


def clean_output(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^(?:simple|simplified(?: text| sentence| version)?|explanation|सरल|सरलीकृत(?: पाठ)?|व्याख्या)\s*:\s*",
               "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 1 and t[0] == t[-1] and t[0] in "\"'":
        t = t[1:-1].strip()
    return t


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 120, max_retries: int = 6):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.key, self.model, self.timeout, self.max_retries = api_key, model, timeout, max_retries

    def chat(self, prompt: str, temperature: float, top_p: float, max_tokens: int, seed: int | None = None) -> dict:
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature, "top_p": top_p, "max_tokens": max_tokens}
        if seed is not None:
            body["seed"] = seed
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        delay = 2.0
        for attempt in range(self.max_retries):
            req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    resp = json.loads(r.read().decode("utf-8"))
                choice = resp["choices"][0]
                return {"text": choice["message"]["content"], "finish_reason": choice.get("finish_reason"),
                        "usage": resp.get("usage"), "served_model": resp.get("model")}
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", errors="replace")[:300]
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries - 1:
                    print(f"  HTTP {e.code}, retrying in {delay:.0f}s")
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise RuntimeError(f"HTTP {e.code}: {msg}") from None
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < self.max_retries - 1:
                    print(f"  network error {e}, retrying in {delay:.0f}s")
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
        raise RuntimeError("unreachable")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="exact model id; it is recorded in every row")
    ap.add_argument("--langs", nargs="+", default=["en", "hi"])
    ap.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=VARIANTS)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--max-tokens-en", type=int, default=200)
    ap.add_argument("--max-tokens-hi", type=int, default=500)
    ap.add_argument("--seed", type=int, default=None, help="passed to the API if it supports it")
    ap.add_argument("--limit", type=int, default=None, help="only the first N clauses")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between calls (rate limits)")
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args(argv)

    paths = data_paths(args.data_dir)
    clauses = load_final_clauses(paths)[: args.limit]
    done = {r["sim_id"] for r in read_jsonl(paths.simplifications) if r.get("simplification")}
    todo = [(c, lang, v) for c in clauses for lang in args.langs for v in args.variants
            if sim_id(c["clause_id"], lang, v) not in done]
    print(f"{len(clauses)} clauses, {len(done)} already done, {len(todo)} to generate")

    if args.dry_run:
        for c, lang, v in todo[:6]:
            pid, tmpl = PROMPTS[(lang, v)]
            print(f"--- {sim_id(c['clause_id'], lang, v)} [{pid}]\n{tmpl.format(text=c['text_' + lang])}\n")
        return

    key = os.environ.get("LLM_API_KEY", "")
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    if not key and "localhost" not in base and "127.0.0.1" not in base:
        sys.exit("set LLM_API_KEY (and LLM_BASE_URL for non-OpenAI endpoints)")
    client = LLMClient(base, key, args.model)
    n_len = 0
    for i, (c, lang, v) in enumerate(todo, 1):
        pid, tmpl = PROMPTS[(lang, v)]
        original = c["text_" + lang]
        if not original:
            continue
        max_tokens = args.max_tokens_en if lang == "en" else args.max_tokens_hi
        out = client.chat(tmpl.format(text=original), args.temperature, args.top_p, max_tokens, args.seed)
        row = {
            "sim_id": sim_id(c["clause_id"], lang, v), "clause_id": c["clause_id"], "act_id": c["act_id"],
            "lang": lang, "variant": v, "original": original, "simplification": clean_output(out["text"]),
            "raw_output": out["text"], "model": args.model, "served_model": out.get("served_model"),
            "prompt_id": pid, "temperature": args.temperature, "top_p": args.top_p, "max_tokens": max_tokens,
            "seed": args.seed, "finish_reason": out.get("finish_reason"), "usage": out.get("usage"),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if row["finish_reason"] == "length":
            n_len += 1
        append_jsonl(paths.simplifications, row)
        print(f"[{i}/{len(todo)}] {row['sim_id']}: {row['simplification'][:80]}")
        if args.sleep:
            time.sleep(args.sleep)
    if n_len:
        print(f"WARNING: {n_len} outputs hit max_tokens (finish_reason=length). Raise the cap and delete those rows"
              " from simplifications.jsonl to regenerate them.")


if __name__ == "__main__":
    main()
