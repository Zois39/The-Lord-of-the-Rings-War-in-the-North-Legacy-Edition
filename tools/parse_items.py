#!/usr/bin/env python3
# Парсит data/wikitext/*.txt в data/raw/items/*.json. Без внешних зависимостей.
import json, os, re, sys

WT = "data/wikitext"; OUT = "data/raw/items"
os.makedirs(OUT, exist_ok=True)

TOKEN = re.compile(r"^[a-zA-Z-]+=(?:\"[^\"]*\"|'[^']*'|[^\s|]+)\s*")

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\{\{[^}]*\}\}", " ", s)
    s = re.sub(r"\[\[([^|\]]*)\|([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = s.replace(chr(39)*3, "").replace(chr(39)*2, "")
    s = re.sub(r"_+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for _ in range(6):
        m = TOKEN.match(s)
        if not m: break
        s = s[m.end():]
    return s.lstrip("| ").strip()

def split_row(r):
    cells = re.split(r"!!|\|\||\n\s*[|!]", r)
    return [c for c in (clean(x) for x in cells) if c != ""]

def tables(text):
    out = []
    for m in re.finditer(r"\{\|(.*?)\n\|\}", text, re.S):
        t = m.group(1)
        chunks = re.split(r"\n\s*\|-", t)
        pre = chunks[0]
        pre_is_hdr = any(l.lstrip().startswith("!") for l in pre.splitlines())
        headers = split_row(pre) if pre_is_hdr else []
        grid = []
        start = 1
        if not headers and len(chunks) > 1 and chunks[1].strip() and all(
                l.lstrip().startswith("!") for l in chunks[1].strip().splitlines()):
            headers = split_row(chunks[1]); start = 2
        for r in chunks[start:]:
            cells = split_row(r)
            if cells: grid.append(cells)
        if not grid: continue
        headers = [h for h in headers if not ('=' in h and '"' in h)]
        out.append({"headers": headers, "rows": grid})
    return out

def sections(text):
    parts = re.split(r"\n==\s*([^=]+?)\s*==\s*\n", text)
    out = []
    for i in range(1, len(parts) - 1, 2):
        out.append((clean(parts[i]), parts[i + 1]))
    return out

def norm_num(s):
    s = s.replace(",", "").strip()
    if re.fullmatch(r"-?\d+", s): return int(s)
    return s

def rows_to_dicts(headers, rows):
    res = []
    for r in rows:
        if headers and len(r) == len(headers) + 1:
            r = [r[0]] + r[1:]
        if headers and len(r) < len(headers):
            r = r + [""] * (len(headers) - len(r))
        res.append({h.lower().replace(" ", "_").replace(".", ""): r[i] for i, h in enumerate(headers)})
    return res

def load(p): return open(os.path.join(WT, p), encoding="utf-8").read()

MAPW = {"value":"value","damage":"damage","effect":"effect","elf_stone_slots":"slots",
 "durability":"durability","level_req":"level_req","strength_req":"str_req","will_req":"wil_req",
 "dexterity_req":"dex_req","stamina_req":"sta_req","origin":"origin","critical":"crit","speed":"speed"}

def parse_weapons(fname):
    page = load(fname)
    out = []
    for sec, body in sections(page):
        for t in tables(body):
            hdrs = list(t["headers"])
            if not hdrs or "damage" not in " ".join(hdrs).lower(): continue
            if "name" not in hdrs[0].lower():
                hdrs = ["Name"] + hdrs
            sec_clean = re.sub(r"Nothing\s*$", "", sec).strip() or sec
            for d in rows_to_dicts(hdrs, t["rows"]):
                item = {"name": clean(str(d.get("name", ""))), "type": sec_clean}
                for k, v in d.items():
                    if k == "name": continue
                    item[MAPW.get(k, k)] = norm_num(str(v))
                if item["name"]: out.append(item)
    return out

MAPE = {"value":"value","armor":"armor","effects":"effect","elf_stone_slots":"slots",
 "durability":"durability","set":"set","characters":"characters","requirements":"reqs","origin":"origin"}

def parse_equipment():
    page = load("Equipment.txt")
    out = []
    for sec, body in sections(page):
        for sub, body2 in (sections(body) or [("", body)]):
            for t in tables(body2):
                hdrs = t["headers"]
                if not hdrs or "name" not in hdrs[0].lower(): continue
                for d in rows_to_dicts(hdrs, t["rows"]):
                    item = {"name": clean(str(d.get("name", ""))), "slot": sec, "quality": sub}
                    for k, v in d.items():
                        if k == "name": continue
                        item[MAPE.get(k, k)] = norm_num(str(v))
                    if item["name"]: out.append(item)
    return out

def parse_sets():
    page = load("Armor_sets.txt")
    out = []
    for sec, body in sections(page):
        if sec.lower().startswith(("notes", "in the list")): continue
        bonuses = {n: clean(e) for n, e in re.findall(r"^\s*(\d)\s*[:.]\s*(.+)$", body, re.M)}
        m = re.search(r"\(([^)]*)\)", body)
        classes = clean(m.group(1)) if m else ""
        if bonuses:
            out.append({"set": sec, "classes": classes, "pieces": sorted(bonuses, key=int),
                        "bonuses": bonuses})
    return out

def parse_items():
    page = load("Items.txt")
    potions, ingredients = [], []
    for t in tables(page):
        hdrs = t["headers"]
        if len(hdrs) >= 2 and "name" in hdrs[0].lower():
            tgt = potions if any("description" in h.lower() for h in hdrs) else ingredients
            for d in rows_to_dicts(hdrs, t["rows"]):
                rec = {"name": clean(str(d.get("name", ""))),
                       "value": norm_num(str(d.get("value", "")))}
                if tgt is potions:
                    rec["description"] = clean(str(d.get("description", "")))
                tgt.append(rec)
    return potions, ingredients

def parse_boss_loot():
    page = load("Boss_Loot_Tables.txt")
    page = re.sub(r"\n'''([^''\n]+)'''\s*\n", r"\n==\1==\n", page)
    out = []
    for sec, body in sections(page):
        for t in tables(body):
            hdrs = list(t["headers"])
            if not hdrs:
                if t["rows"] and len(t["rows"][0]) == 9:
                    hdrs = ["Name","Value","Damage","Effect","Slots","Durability","Level","Str","Origin"]
                else: continue
            if not hdrs: continue
            fixed = ["Name"] + hdrs[1:] if "name" not in hdrs[0].lower() else hdrs
            for d in rows_to_dicts(fixed, t["rows"]):
                d = {("name" if "name" in k else k): v for k, v in d.items()}
                d["boss"] = sec
                out.append({k: norm_num(str(v)) for k, v in d.items()})
    return out


def parse_elf_stones():
    page = load("Elf_Stones.txt")
    out = []
    GRADES = ["normal", "glowing", "shining", "radiant", "legendary"]
    GW = ["EFFECT", "NORMAL", "GLOWING", "SHINING", "RADIANT", "LEGENDARY", "USABILITY"]
    for sec, body in sections3(page):
        for t in tables(body):
            rows = t["rows"]
            if not rows: continue
            hdr = rows[0]
            if not hdr or hdr[0].upper() not in GW: continue
            n_grades = max(1, len(hdr) - 2)      # EFFECT + USABILITY по краям
            grades = GRADES[:n_grades]
            for r in rows[1:]:
                if len(r) < 2 + n_grades + 1: continue
                name, effect = r[0], r[1]
                vals = [norm_num(x.replace("+", "")) for x in r[2:2 + n_grades]]
                use = r[2 + n_grades]
                if not any(v not in ("", "-") for v in vals): continue
                out.append({"group": sec, "name": name, "effect": effect,
                            "values": dict(zip(grades, vals)), "usability": use})
    return out

def sections3(text):
    parts = re.split(r"\n===\s*([^=]+?)\s*===\s*\n", text)
    out = []
    for i in range(1, len(parts) - 1, 2):
        out.append((clean(parts[i]), parts[i + 1]))
    return out

def parse_quest_rewards():
    page = load("Side-Quests.txt")
    out = []
    for t in tables(page):
        hdrs = list(t["headers"])
        if not hdrs: continue
        joined = " ".join(hdrs).lower()
        if "damage" not in joined and "armor" not in joined and "effects" not in joined: continue
        if "name" not in hdrs[0].lower(): hdrs = ["Name"] + hdrs
        for d in rows_to_dicts(hdrs, t["rows"]):
            item = {"name": clean(str(d.get("name", ""))), "source": "Side-Quest reward"}
            for k, v in d.items():
                if k == "name": continue
                item[MAPW.get(k, MAPE.get(k, k))] = norm_num(str(v))
            if item["name"]: out.append(item)
    return out


def parse_best_gear():
    page = load("Best_Gear.txt")
    out = []
    slot = ""
    for m in re.finditer(r"\n(==|===)\s*([^=\n]+?)\s*==+\s*\n", page):
        lvl, name = len(m.group(1)), clean(m.group(2))
        end = page.find("\n==", m.end())
        end = len(page) if end < 0 else end
        body = page[m.end():end]
        if lvl == 2:
            slot = re.sub(r"\s+-(\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+){1,3}.*$", "", name).strip()
            continue
        item_name = re.sub(r"\s+-\s+.*$", "", name).strip()
        rec = {"name": item_name, "slot": slot}
        for line in body.splitlines():
            line = clean(line).lstrip("* ").strip()
            if not line: continue
            if line.lower().startswith("value:"):
                rec["value"] = norm_num(re.sub(r"^[^0-9]*", "", line.split("/")[0]))
            elif "elfstone slots" in line.lower() or "elf-stone" in line.lower():
                mm = re.search(r"\+?\d", line)
                if mm: rec["slots"] = int(mm.group())
            elif re.match(r"^[+\-]?\d", line) or line.startswith("+"):
                rec.setdefault("bonuses", []).append(line.split("/")[0].strip())
            elif "mithril" in line.lower():
                rec["mithril"] = line
            elif len(line) > 60:
                rec["source"] = line[:300]
        if rec.get("name"): out.append(rec)
    return out

best = parse_best_gear()

elf = parse_elf_stones()
qr  = parse_quest_rewards()

weapons = parse_weapons("Weapons.txt") + parse_weapons("Ranged_Weapons.txt")
armor   = parse_equipment()
sets    = parse_sets()
potions, ingredients = parse_items()
loot    = parse_boss_loot()

for fn, data in [("weapons.json", weapons), ("armor.json", armor), ("sets.json", sets),
                 ("potions.json", potions), ("ingredients.json", ingredients),
                 ("boss_loot.json", loot), ("elf_stones.json", elf), ("best_gear.json", best)]:
    json.dump(data, open(os.path.join(OUT, fn), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(fn + ":", len(data), "records")
