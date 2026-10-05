"""Fetch RSS + Google News RSS feeds into data/raw.json."""
import json, re, time, html
from calendar import timegm
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
import feedparser, requests, yaml

UA = {"User-Agent": "Mozilla/5.0 (compatible; AINewsBot/1.0)"}
MAX_AGE = timedelta(hours=36)


def gnews_url(query, region):
    loc = "hl=en-IN&gl=IN&ceid=IN:en" if region == "india" else "hl=en-US&gl=US&ceid=US:en"
    return f"https://news.google.com/rss/search?q={quote_plus(query + ' when:1d')}&{loc}"


def fetch(url, retries=2):
    for i in range(retries + 1):
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
            return feedparser.parse(r.content)
        except Exception as e:
            if i == retries:
                print(f"  SKIP {url[:80]} ({e})")
            time.sleep(1.5)


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def parse_entries(feed, source_default, bucket, cutoff, is_gnews):
    out = []
    for e in feed.entries:
        ts = e.get("published_parsed") or e.get("updated_parsed")
        if not ts:
            continue
        pub = datetime.fromtimestamp(timegm(ts), tz=timezone.utc)
        if pub < cutoff:
            continue
        title = clean(e.get("title"))
        source = source_default
        if is_gnews:
            source = (e.get("source") or {}).get("title") or source_default
            title = re.sub(rf"\s+-\s+{re.escape(source)}$", "", title)
        summary = "" if is_gnews else clean(e.get("summary"))[:400]
        out.append({"title": title, "url": e.get("link"), "source": source,
                    "published": pub.isoformat(), "summary": summary, "bucket": bucket})
    return out


def main():
    cfg = yaml.safe_load(open("sources.yaml", encoding="utf-8"))
    cutoff = datetime.now(timezone.utc) - MAX_AGE
    items = []
    for bucket, spec in cfg["buckets"].items():
        region = "india" if bucket.endswith("india") else "global"
        print(bucket)
        for f in spec.get("feeds", []):
            feed = fetch(f["url"])
            if feed:
                got = parse_entries(feed, f["name"], bucket, cutoff, False)
                print(f"  {f['name']}: {len(got)}")
                items += got
        for q in spec.get("queries", []):
            feed = fetch(gnews_url(q, region))
            if feed:
                got = parse_entries(feed, "Google News", bucket, cutoff, True)
                print(f"  GNews '{q[:40]}...': {len(got)}")
                items += got
    json.dump(items, open("data/raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Collected {len(items)} items")


if __name__ == "__main__":
    main()
