"""Dedupe, classify (Gemini free tier, keyword fallback), rank -> data/news.json."""
import json, os, re
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests, yaml
from rapidfuzz import fuzz

TOP_N = 25
BATCH = 20
MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
SUBTOPICS = ["OEM", "EV", "auto components", "transformers", "switchgear", "BESS",
             "cables/conductors", "smart meters", "motors/compressors",
             "power electronics", "semiconductors", "policy", "other"]
PROMPT = """You are an industry analyst. For each numbered news item (title | snippet) return a JSON array,
one object per item, in order:
{"id": <number>, "industry": "auto" | "electrical_electronics" | "irrelevant",
 "region": "india" | "global",
 "subtopic": one of %s,
 "why_it_matters": "<=20 words"}
"auto" = automobiles, EVs, auto components/suppliers. "electrical_electronics" = transformers, switchgear, BESS,
conductors, cables, smart meters, motors, compressors, power electronics, semiconductors, grid equipment.
"irrelevant" = stock-tip spam, ETF/fund performance, real estate, market-research report promos, board/HR appointments
at non-industrial firms, crime/accident reports, listicles, or anything where the industry is only incidental.
Keep only stories about companies, products, capacity, orders, technology, supply chain or policy in these industries. region=india if the story is primarily about India.
Return ONLY the JSON array.

Items:
%s"""


def load_env():
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def canon(url):
    p = urlparse(url or "")
    return p.netloc + p.path.rstrip("/")


def dedupe(items):
    items.sort(key=lambda x: x["published"], reverse=True)
    kept, seen = [], set()
    for it in items:
        c = canon(it["url"])
        if c in seen:
            continue
        if any(fuzz.token_set_ratio(it["title"], k["title"]) >= 85 for k in kept):
            continue
        seen.add(c)
        kept.append(it)
    return kept


def kw_hits(text, words):
    t = text.lower()
    return sum(1 for w in words if re.search(r"\b" + re.escape(w.lower()) + r"\b", t))


def keyword_classify(it, kw):
    text = f"{it['title']} {it['summary']}"
    a, e = kw_hits(text, kw["auto"]), kw_hits(text, kw["elec"])
    if max(a, e) == 0:
        return None
    if a == e:
        industry = "auto" if it["bucket"].startswith("auto") else "electrical_electronics"
    else:
        industry = "auto" if a > e else "electrical_electronics"
    india = kw_hits(text, kw["india"]) or it["bucket"].endswith("india")
    return {"industry": industry, "region": "india" if india else "global",
            "subtopic": "other", "why_it_matters": ""}


def gemini_classify(batch, key):
    listing = "\n".join(f"{i}. {b['title']} | {b['summary'][:200]}" for i, b in enumerate(batch))
    body = {"contents": [{"parts": [{"text": PROMPT % (json.dumps(SUBTOPICS), listing)}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                      headers={"x-goog-api-key": key}, json=body, timeout=90)
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return {o["id"]: o for o in json.loads(text)}


def main():
    load_env()
    kw = yaml.safe_load(open("keywords.yaml", encoding="utf-8"))
    items = dedupe(json.load(open("data/raw.json", encoding="utf-8")))
    print(f"{len(items)} after dedupe")
    labelled = []
    for i in items:  # cheap prefilter saves Gemini quota
        lab = keyword_classify(i, kw)
        if lab:
            i.update(lab)
            labelled.append(i)
    items = labelled
    print(f"{len(items)} after keyword prefilter")
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        for s in range(0, len(items), BATCH):
            batch = items[s:s + BATCH]
            try:
                res = gemini_classify(batch, key)
            except Exception as ex:
                print(f"  Gemini batch {s} failed ({ex}); keeping keyword labels")
                continue
            for idx, it in enumerate(batch):
                o = res.get(idx)
                if o and o.get("industry") in ("auto", "electrical_electronics", "irrelevant"):
                    for k in ("industry", "region", "subtopic", "why_it_matters"):
                        if o.get(k):
                            it[k] = o[k]
    else:
        print("No GEMINI_API_KEY: using keyword classification only")
    items = [i for i in items if i["industry"] != "irrelevant"]
    out = {}
    for ind in ("auto", "electrical_electronics"):
        for reg in ("india", "global"):
            out[f"{ind}_{reg}"] = [i for i in items if i["industry"] == ind and i["region"] == reg][:TOP_N]
    out["_meta"] = {"generated": datetime.now(timezone.utc).isoformat(), "llm": bool(key), "model": MODEL}
    json.dump(out, open("data/news.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print({k: len(v) for k, v in out.items() if k != "_meta"})


if __name__ == "__main__":
    main()
