#!/usr/bin/env python3
# Генерирует data/raw/skills/{hero}.json из data/wikitext. Сливает с существующими
# JSON: type/max_rank/cost сохраняются, описания обновляются из вики.
import json, os, re

WT = "data/wikitext"
TREES = {"Eradan": ["Evasion", "Ranger Strike", "Heavy Shot"],
         "Andriel": ["Sanctuary", "Word of Command", "Empower Staff"],
         "Farin": ["War-cry", "Sweeping Attack", "Crushing Blow"]}
ARCH = {"Eradan": ("Ranger", "Дунаданский рейнджер из Севора. Мастер скрытности, двойного владения и лука."),
        "Andriel": ("Loremaster", "Эльфийская хранительница знаний из Ривенделла. Мастер посоха, света и защиты отряда."),
        "Farin": ("Champion", "Гном-чемпион из Эребора. Неудержимый воин щитом, топором и арбалетом.")}

HDR = re.compile(r"\n(={3,6})[^\S\n]*([^=\n]+?)[^\S\n]*\1[^\S\n]*\n")

def clean(s):
    s = re.sub(r"\[https?://[^\s\]]+\s+([^\]]*?)\]", r"\1", s)
    s = re.sub(r"\[\[File:[^\]]*\]\]", " ", s)
    s = re.sub(r"\[\[Category:[^\]]*\]\]", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\[\[([^|\]]*)\|([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = s.replace(chr(39)*3, "").replace(chr(39)*2, "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*[-•]\s*", " • ", s)   # маркеры списков
    s = re.sub(r"\n{2,}", "\n", s).strip(" \n-")
    return s.strip()

def parse_text_hero(page, hero):
    marks = [(m.start(), m.end(), len(m.group(1)), m.group(2).strip().rstrip(":"))
             for m in HDR.finditer(page)]
    trees = []
    tree_lvl = None
    for i, (s0, e0, lvl, name) in enumerate(marks):
        end = marks[i+1][0] if i+1 < len(marks) else len(page)
        text = clean(page[e0:end])
        if "talent build tree" in name.lower():
            tree_lvl = lvl
            tname = TREES.get(hero, [])[len(trees)] if len(trees) < 3 else ""
            trees.append({"name": tname, "_lvl": lvl, "skills": []})
        elif tree_lvl and lvl == tree_lvl + 1 and trees:
            trees[-1]["skills"].append({"name": name, "description": text.replace("\n", " ")})
    for t in trees:
        t.pop("_lvl", None)
        if not t["name"] or t["name"].startswith("Tree"):
            t["name"] = t["skills"][0]["name"] if t["skills"] else t["name"]
    return trees

def parse_table_hero(page, hero):
    m = re.search(r"\{\|(.*?)\n\|\}", page, re.S)
    if not m: return []
    rows = re.split(r"\n\s*\|-", m.group(1))[1:]
    grid = []
    for r in rows:
        cells = re.split(r"\n\s*[|!]", r)
        cells = [clean(c).strip() for c in cells]
        cells = [re.sub(r"^[a-zA-Z-]+=(?:\"[^\"]*\"|'[^']*'|[^\s|]+)\s*", "", c) for c in cells]
        cells = [c.lstrip("| ").strip() for c in cells]
        cells = [c for c in cells if c]
        if cells: grid.append(cells)
    if not grid: return []
    trees = [{"name": n, "_w": w, "skills": []} for n, w in
             zip([re.sub(r"^.*\|", "", c) for c in grid[0]], [2, 3, 2])]
    for row in grid[1:]:
        i = 0
        for t in trees:
            for _ in range(t["_w"]):
                if i < len(row):
                    t["skills"].append({"name": row[i], "description": ""})
                i += 1
    for t in trees:
        t.pop("_w", None)
        for s in t["skills"]:
            fn = f"{WT}/{s['name'].replace(' ', '_')}.txt"
            if os.path.exists(fn):
                s["description"] = clean(open(fn, encoding="utf-8").read())[:600]
    return trees

def load_existing(hero):
    fn = f"data/raw/skills/{hero.lower()}.json"
    if os.path.exists(fn):
        d = json.load(open(fn, encoding="utf-8"))
        return {s["name"]: s for t in d.get("trees", []) for s in t.get("skills", [])}
    return {}

def parse_farin_preserve(page, hero):
    # таблица Фарина в вики потеряла rowspan/colspan при конвертации — структуру
    # деревьев берём из существующего JSON (ручная сверка), описания обновляем из вики-страниц навыков.
    fn = f"data/raw/skills/{hero.lower()}.json"
    data = json.load(open(fn, encoding="utf-8")) if os.path.exists(fn) else {"trees": []}
    for t in data.get("trees", []):
        for s in t.get("skills", []):
            pg = f"{WT}/{s['name'].replace(' ', '_')}.txt"
            if os.path.exists(pg):
                s["description"] = clean(open(pg, encoding="utf-8").read())[:600]
    return data.get("trees", [])

for hero in ["Eradan", "Andriel", "Farin"]:
    page = open(f"{WT}/{hero}.txt", encoding="utf-8").read()
    if hero == "Farin":
        trees = parse_farin_preserve(page, hero)
    else:
        trees = parse_text_hero(page, hero)
    existing = load_existing(hero)
    total = 0
    seen = set()
    TIERS = {"Eradan": 3, "Andriel": 3, "Farin": 3}
    for t in trees:
        if not t.get("name") and t["skills"]:
            t["name"] = t["skills"][0]["name"]
        for i, s in enumerate(t["skills"]):
            if "tier" not in s:
                s["tier"] = 1 if i == 0 else 2 + (i - 1) // TIERS[hero]
            total += 1
            seen.add(s["name"])
            old = existing.get(s["name"])
            if old:
                s["type"] = old.get("type")
                if old.get("max_rank"): s["max_rank"] = old["max_rank"]
                if old.get("cost"): s["cost"] = old["cost"]
                if not s["description"] and old.get("description"):
                    s["description"] = old["description"]
    # навыки из ручной сверки, отсутствующие в вики, — сохранить с пометкой
    old_fn = f"data/raw/skills/{hero.lower()}.json"
    if os.path.exists(old_fn):
        prev = json.load(open(old_fn, encoding="utf-8"))
        tree_by_name = {t["name"]: t for t in trees}
        for pt in prev.get("trees", []):
            tgt = tree_by_name.get(pt.get("name"))
            if not tgt: continue
            for ps in pt.get("skills", []):
                if ps["name"] not in seen:
                    ps = dict(ps); ps["note"] = "в вики не оформлено, из ручной сверки"
                    tgt["skills"].append(ps); seen.add(ps["name"]); total += 1
    for t in trees:  # пост-проход: гарантированно заполнить тиры по позиции
        for i, s in enumerate(t["skills"]):
            if s.get("tier") in (None, ""):
                s["tier"] = 1 if i == 0 else 2 + (i - 1) // 3
    out = {"hero": hero, "archetype": ARCH[hero][0],
           "source": f"https://witn.fandom.com/wiki/{hero}",
           "description": ARCH[hero][1], "trees": trees}
    json.dump(out, open(f"data/raw/skills/{hero.lower()}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{hero}: {len(trees)} trees, {total} skills")
