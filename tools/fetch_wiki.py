#!/usr/bin/env python3
"""Скачивает весь контент witn.fandom.com (MediaWiki API) в data/wikitext/.
Запускается локально или в GitHub Actions (раннеры имеют полный интернет)."""
import json, os, re, sys, time, urllib.request, urllib.parse

API = "https://witn.fandom.com/api.php"
OUT = "data/wikitext"
os.makedirs(OUT, exist_ok=True)

def api(params, retries=5):
    p = {"format": "json", "formatversion": "2", **params}
    url = API + "?" + urllib.parse.urlencode(p)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WITN-Builder-DataFetcher/1.0 (fan project)"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print(f"  retry {i+1}: {e}", file=sys.stderr)
            time.sleep(3 * (i + 1))
    raise RuntimeError("API failed: " + url)

def safe(title):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_")

# 1. список всех страниц основного пространства
titles, cont = [], {}
while True:
    r = api({"action": "query", "list": "allpages", "apnamespace": 0, "aplimit": "max", **cont})
    titles += [p["title"] for p in r["query"]["allpages"]]
    if "continue" not in r: break
    cont = r["continue"]
print(f"pages listed: {len(titles)}")

# 2. витекст пакетами по 50
manifest = []
for i in range(0, len(titles), 50):
    batch = titles[i:i+50]
    r = api({"action": "query", "prop": "revisions", "titles": "|".join(batch),
             "rvprop": "content", "rvslots": "main"})
    for p in r["query"]["pages"]:
        if "missing" in p: continue
        content = p["revisions"][0]["slots"]["main"]["content"]
        fn = safe(p["title"]) + ".txt"
        open(os.path.join(OUT, fn), "w", encoding="utf-8").write(content)
        manifest.append({"title": p["title"], "pageid": p["pageid"], "file": fn,
                         "url": "https://witn.fandom.com/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"))})
        print("  fetched:", p["title"])
    time.sleep(0.5)
manifest.sort(key=lambda m: m["title"])
json.dump(manifest, open("data/sources.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done:", len(manifest), "pages")
