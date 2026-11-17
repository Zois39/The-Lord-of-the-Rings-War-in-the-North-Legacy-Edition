#!/usr/bin/env python3
# Качает изображения предметов/героев с witn.fandom.com (весь список allimages,
# нормализация имён, суффиксы переводов отрезаются). Ранится в GitHub Actions.
import json, os, re, sys, time, urllib.request, urllib.parse

API = "https://witn.fandom.com/api.php"

def api(params, retries=4):
    p = {"format": "json", "formatversion": "2", **params}
    url = API + "?" + urllib.parse.urlencode(p)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WITN-Builder-Images/2.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print(f"  retry {i+1}: {e}", file=sys.stderr); time.sleep(3)
    return {}

def norm(s):
    s = s.lower()
    s = re.sub(r"\.[a-z0-9]{2,5}$", "", s)          # расширение
    s = s.replace("_", " ").replace("´", "'").replace("`", "'").replace("-", " ").replace("-", " ")
    s = re.sub(r"\s+-\s+.*$", "", s)                 # суффикс перевода "- Cuchilla de..."
    s = re.sub(r"\s+", " ", s).strip()
    return s

def safe(s): return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")

# 1. полный список изображений вики
images, cont = [], {}
while True:
    r = api({"action": "query", "list": "allimages", "ailimit": "max", **cont})
    batch = r.get("query", {}).get("allimages", [])
    images += batch
    if "continue" not in r or not batch: break
    cont = r["continue"]
print("total images on wiki:", len(images))

by_norm = {}
for im in images:
    key = norm(im["name"])
    if key and key not in by_norm:
        by_norm[key] = im["url"]
print("normalized unique:", len(by_norm))

def find_url(name):
    n = norm(name)
    if n in by_norm: return by_norm[n]
    n2 = n.replace("'", "")
    for k, u in by_norm.items():
        if k.replace("'", "") == n2: return u
    for k, u in by_norm.items():
        if k.startswith(n + " ") or k == n: return u
    return None

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "WITN-Builder-Images/2.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())

got = 0
def attach(sec, fn, data, rec, name):
    global got
    url = find_url(name)
    if not url: return False
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or ".png"
    os.makedirs(f"assets/images/{sec}", exist_ok=True)
    out = f"assets/images/{sec}/{safe(name)}{ext}"
    try: download(url, out)
    except Exception as e:
        print("  dl fail", name, e, file=sys.stderr); return False
    rec["local_image"] = out
    got += 1
    print("  image:", name, "->", out)
    return True

# предметы
for sec, fn in [("best", "data/raw/items/best_gear.json"),
                ("weapons", "data/raw/items/weapons.json"),
                ("armor", "data/raw/items/armor.json"),
                ("potions", "data/raw/items/potions.json"),
                ("sets", "data/raw/items/sets.json")]:
    data = json.load(open(fn, encoding="utf-8"))
    changed = False
    for rec in data:
        name = rec.get("set") or rec.get("name")
        if name and attach(sec, fn, data, rec, name): changed = True
    if changed:
        json.dump(data, open(fn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# герои
for hero in ["eradan", "andriel", "farin"]:
    fn = f"data/raw/skills/{hero}.json"
    data = json.load(open(fn, encoding="utf-8"))
    if attach("heroes", fn, data, data, hero.capitalize()):
        json.dump(data, open(fn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("images downloaded:", got)
