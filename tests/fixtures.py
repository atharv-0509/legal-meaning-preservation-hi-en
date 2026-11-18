"""SYNTHETIC test fixtures. These sentences are invented for testing only and must never be
copied into data/ (CLAUDE.md §7). They imitate the *format* of Indian central acts, not their content.
"""
from __future__ import annotations

import json
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

NOUNS = [
    ("public authority", "लोक प्राधिकरण"), ("information officer", "सूचना अधिकारी"),
    ("appellate authority", "अपील प्राधिकारी"), ("consumer commission", "उपभोक्ता आयोग"),
    ("district registrar", "जिला रजिस्ट्रार"), ("product manufacturer", "उत्पाद विनिर्माता"),
    ("service provider", "सेवा प्रदाता"), ("electronic intermediary", "इलेक्ट्रॉनिक मध्यवर्ती"),
    ("regulatory directorate", "विनियामक निदेशालय"), ("municipal corporation", "नगर निगम"),
    ("insurance underwriter", "बीमा अभिगोपक"), ("educational institution", "शैक्षणिक संस्था"),
]

TEMPLATES = [
    ("Notwithstanding anything contained in any other enactment, the {a} shall, within {n} days of receipt of an "
     "application, either furnish the requested particulars or reject the application for reasons recorded in writing.",
     "किसी अन्य अधिनियमिति में किसी बात के होते हुए भी, {a} आवेदन की प्राप्ति के {n} दिन के भीतर या तो अनुरोधित विवरण "
     "देगा या लिखित में अभिलिखित कारणों से आवेदन को अस्वीकार करेगा।"),
    ("Where any {a} contravenes the provisions of this Chapter, the {b} may impose a penalty which may extend to "
     "{n} thousand rupees, after affording a reasonable opportunity of being heard.",
     "जहां कोई {a} इस अध्याय के उपबंधों का उल्लंघन करता है, वहां {b} सुनवाई का युक्तियुक्त अवसर देने के पश्चात् ऐसी "
     "शास्ति अधिरोपित कर सकेगा जो {n} हजार रुपए तक हो सकेगी।"),
    ("Every {a} shall maintain comprehensive documentation regarding its organisational functions, administrative "
     "expenditure and statutory obligations, and shall periodically publish such documentation electronically. "
     "Provided that confidential commercial particulars shall not be disclosed.",
     "प्रत्येक {a} अपने संगठनात्मक कृत्यों, प्रशासनिक व्यय और कानूनी बाध्यताओं के संबंध में व्यापक दस्तावेज रखेगा और ऐसे "
     "दस्तावेज को इलेक्ट्रॉनिक रूप से समय-समय पर प्रकाशित करेगा। परंतु गोपनीय वाणिज्यिक विवरण प्रकट नहीं किए जाएंगे।"),
    ("An aggrieved complainant may prefer an appeal against the determination of the {a} before the {b} within a "
     "period of {n} days, unless the {b} is satisfied that sufficient justification existed for the delay.",
     "कोई व्यथित परिवादी {a} के अवधारण के विरुद्ध {b} के समक्ष {n} दिन की अवधि के भीतर अपील कर सकेगा, जब तक कि {b} "
     "का यह समाधान न हो जाए कि विलंब के लिए पर्याप्त औचित्य विद्यमान था।"),
    ("Subject to the provisions of section {s}, no {a} shall be compelled to communicate intellectual property, "
     "cabinet deliberations or investigative materials whose disclosure would prejudicially affect sovereignty.",
     "धारा {s} के उपबंधों के अधीन रहते हुए, किसी {a} को बौद्धिक संपदा, मंत्रिमंडल के विचार-विमर्श या ऐसी अन्वेषण सामग्री "
     "संसूचित करने के लिए बाध्य नहीं किया जाएगा जिसके प्रकटन से संप्रभुता पर प्रतिकूल प्रभाव पड़ेगा।"),
    ("Manufacturers distributing hazardous merchandise must compensate affected purchasers for injuries resulting "
     "from manufacturing defects, deficient instructions or inadequate warnings, irrespective of contractual exclusions.",
     "खतरनाक माल का वितरण करने वाले विनिर्माताओं को विनिर्माण दोष, त्रुटिपूर्ण अनुदेशों या अपर्याप्त चेतावनियों से होने वाली "
     "क्षतियों के लिए प्रभावित क्रेताओं को प्रतिकर देना होगा।"),
    ("If the {a} fails to dispose of a complaint within {n} months, the complainant is entitled to approach the "
     "{b}, which shall adjudicate the controversy expeditiously.",
     "यदि {a} {n} मास के भीतर परिवाद का निपटारा करने में असफल रहता है, तो परिवादी {b} के पास जाने का हकदार होगा, जो "
     "विवाद का शीघ्रता से न्यायनिर्णयन करेगा।"),
    ("Remuneration, allowances and other conditions of service of the chairperson shall be such as may be "
     "prescribed by the Central Government by notification.",
     "अध्यक्ष के पारिश्रमिक, भत्ते और सेवा की अन्य शर्तें ऐसी होंगी जो केंद्रीय सरकार द्वारा अधिसूचना द्वारा विहित की जाएं।"),
]
HEADINGS = [("Disposal of applications", "आवेदनों का निपटारा"), ("Penalties", "शास्तियां"),
            ("Obligations of authorities", "प्राधिकरणों की बाध्यताएं"), ("Appeals", "अपील"),
            ("Exemption from disclosure", "प्रकटन से छूट"), ("Product liability", "उत्पाद दायित्व"),
            ("Remedies", "उपचार"), ("Conditions of service", "सेवा की शर्तें")]


def make_units(act_id: str, n_sections: int = 22, seed: int = 0) -> dict[str, list[dict]]:
    """Aligned EN/HI unit lists in the extract.py schema."""
    from common import count_sentences, count_words
    rng = random.Random(f"{act_id}|{seed}")
    out = {"en": [], "hi": []}
    for s in range(1, n_sections + 1):
        if s == 1:
            head = ("Short title and commencement", "संक्षिप्त नाम और प्रारंभ")
        elif s == 2:
            head = ("Definitions", "परिभाषाएं")
        elif s == n_sections:
            head = ("Power to make rules", "नियम बनाने की शक्ति")
        else:
            head = HEADINGS[s % len(HEADINGS)]
        for sub in range(1, rng.randint(1, 3) + 1):
            t_en, t_hi = TEMPLATES[rng.randrange(len(TEMPLATES))]
            i, j = rng.sample(range(len(NOUNS)), 2)
            kw = {"n": rng.choice([15, 30, 45, 60, 90]), "s": rng.randint(2, 20)}
            en = t_en.format(a=NOUNS[i][0], b=NOUNS[j][0], **kw)
            hi = t_hi.format(a=NOUNS[i][1], b=NOUNS[j][1], **kw)
            for lang, text, h in (("en", en, head[0]), ("hi", hi, head[1])):
                out[lang].append({"act_id": act_id, "lang": lang, "section": str(s), "subsection": str(sub),
                                  "key": f"s{s}_{sub}", "heading": h, "text": text,
                                  "n_words": count_words(text), "n_sents": count_sentences(text)})
    return out


def write_sources(path: Path, data_dir: Path) -> None:
    acts = [{"act_id": a, "name_en": a, "name_hi": a, "domain": d, "url": "synthetic",
             "pdf": {"en": str(data_dir / "raw" / f"{a}_en.pdf"), "hi": str(data_dir / "raw" / f"{a}_hi.pdf")},
             "version_note": "synthetic test fixture"} for a, d in (("rti", "public_information"), ("cpa", "consumer_law"))]
    path.write_text(json.dumps({"acts": acts}, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------- page-layout fixtures for extract.py
EN_PAGES = [
    "THE SYNTHETIC ACT, 2005\nARRANGEMENT OF SECTIONS\n1. Short title and commencement.\n2. Definitions.\n"
    "3. Disposal of requests.\n4. Appeals.\n",
    "THE SYNTHETIC ACT, 2005\n1. Short title and commencement.—(1) This Act may be called the Synthetic Act, 2005.\n"
    "(2) It extends to the whole of India.\n2. Definitions.—In this Act, unless the context otherwise requires, "
    "\"authority\" means any body.\nCHAPTER II\nOBLIGATIONS OF AUTHORITIES\n3. Disposal of\nrequests.—(1) Subject to "
    "the provisions of sub-section (3) of section 8, the officer shall, within thirty days of the receipt of the request, "
    "provide the infor-\nmation.\n(2) Where the officer fails to decide within the period specified in sub-section (1), "
    "he shall be deemed to have refused the request.\n1[(3) The fee referred to in sub-section (2) shall be reasonable.]\n"
    "12\n1. Ins. by Act 5 of 2019, s. 2 (w.e.f. 1-1-2020).",
    "THE SYNTHETIC ACT, 2005\n4. Appeals.—Any person aggrieved by a decision under section 3 may prefer an appeal "
    "within ninety days. 2* * *\n13",
]
HI_PAGES = [
    "कृत्रिम अधिनियम, 2005\n3. अनुरोधों का निपटारा—(1) धारा 8 की उपधारा (3) के उपबंधों के अधीन रहते हुए, अधिकारी अनुरोध की "
    "प्राप्ति के तीस दिन के भीतर सूचना उपलब्ध करे गा ।\n(2) जहां अधिकारी उपधारा (1) में विनिर्दिष्ट अवधि के भीतर विनिश्चय करने में "
    "असफल रहता है, वहां यह समझा जाएगा कि उसने अनुरोध को अस्वीकार कर दिया है |\n(3) उपधारा (2) में निर्दिष्ट फीस युक्तियुक्त होगी।\n",
    "कृत्रिम अधिनियम, 2005\n4. अपील--कोई व्यक्ति जो धारा 3 के अधीन किसी विनिश्चय से व्यथित है, नब्बे दिन के भीतर अपील कर सकेगा।\n",
    "कृत्रिम अधिनियम, 2005\n5. निरसन—इस अधिनियम के प्रारंभ पर पूर्ववर्ती अध्यादेश निरसित हो जाएगा।\n",
]


# --------------------------------------------------------------------------- fake OpenAI-compatible server
def fake_judge(prompt: str) -> str:
    """Deterministic fake LLM judge: penalises length differences between original and simplification."""
    orig = prompt.split("Original:\n", 1)[1].split("\n\nSimplification:", 1)[0]
    simp = prompt.split("Simplification:\n", 1)[1].split("\n\nAnswer", 1)[0]
    gap = abs(len(orig.split()) - len(simp.split()))
    bracket = "Accurate (7-10)" if gap < 5 else "Imprecise (2-6)" if gap < 25 else "Off-track (1)"
    return "Sure:\n" + json.dumps({"bracket": bracket, "omissions": min(3, gap // 5), "hallucinations": 0,
                                   "inconsistencies": 0, "confusions": 0, "main_change": "omission",
                                   "explanation": "synthetic"})


def fake_simplify(prompt: str) -> str:
    if prompt.startswith("You are an expert in Indian law"):
        return fake_judge(prompt)
    text = prompt.split("\n\n", 1)[1]
    text = text.split(":", 1)[1].rsplit("\n", 1)[0].strip()
    hindi = any("ऀ" <= c <= "ॿ" for c in text)
    if "12" in prompt.split("\n\n")[0]:                      # aggressive: first clause only
        first = text.split("।" if hindi else ",")[0]
        return ("सरल: " if hindi else "Explanation: ") + first.strip() + ("।" if hindi else ".")
    if hindi:
        return "सरल: " + text.replace("उपबंधों", "नियमों")
    return "Simple: " + text.replace("furnish", "give").replace("contravenes", "breaks")


class _Handler(BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Handler.calls += 1
        content = fake_simplify(body["messages"][0]["content"])
        resp = {"model": body["model"] + "-served", "choices": [{"message": {"content": content},
                "finish_reason": "stop"}], "usage": {"total_tokens": 1}}
        data = json.dumps(resp, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def start_fake_llm() -> tuple[HTTPServer, str]:
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1"
