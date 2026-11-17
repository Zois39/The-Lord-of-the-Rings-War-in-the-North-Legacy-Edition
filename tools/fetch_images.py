#!/usr/bin/env python3
# Ищет изображения предметов/навыков/героев на witn.fandom.com (allimages prefix)
# и качает их в assets/images/<section>/. Добавляет local_image в JSON. Ранится в Actions.
import json, os, re, sys, time, urllib.request, urllib.parse

API = "https://witn.fandom.com/api.php"

def api(params, retries=4):
    p = {"format": "json", "formatversion": "2", **params}
    url = API + "?" + urllib.parse.urlencode(p)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WITN-Builder-Images/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print(f"  retry {i+1}: {e}", file=sys.stderr); time.sleep(3)
    return {}

def safe(s): return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")

def find_image(title):
    r = api({"action": "query", "list": "allimages", "aiprefix": title, "ailimit": 5})
    ims = r.get("query", {}).get("allimages", [])
    for im in ims:
        if im.get("url"): return im["url"], im["name"]
    return None, None

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "WITN-Builder-Images/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())

jobs = []
for sec, fn in [("weapons", "data/raw/items/weapons.json"),
                ("armor", "data/raw/items/armor.json"),
                ("potions", "data/raw/items/potions.json"),
                ("sets", "data/raw/items/sets.json")]:
    data = json.load(open(fn, encoding="utf-8"))
    for rec in data:
        name = rec.get("set") or rec.get("name")
        if name: jobs.append((sec, fn, data, rec, name))
for hero in ["eradan", "andriel", "farin"]:
    fn = f"data/raw/skills/{hero}.json"
    data = json.load(open(fn, encoding="utf-8"))
    for t in data.get("trees", []):
        for s in t.get("skills", []):
            jobs.append(("skills", fn, data, s, s.get("name", "")))

seen = set(); got = 0
for sec, fn, data, rec, name in jobs:
    if not name or name in seen: continue
    seen.add(name)
    url, fname = find_image(name)
    if not url:
        continue
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or ".png"
    os.makedirs(f"assets/images/{sec}", exist_ok=True)
    out = f"assets/images/{sec}/{safe(name)}{ext}"
    try:
        download(url, out)
    except Exception as e:
        print("  dl fail", name, e, file=sys.stderr); continue
    rec["local_image"] = out
    json.dump(data, open(fn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    got += 1
    print("  image:", name, "->", out)
    time.sleep(0.2)
print("images downloaded:", got)
