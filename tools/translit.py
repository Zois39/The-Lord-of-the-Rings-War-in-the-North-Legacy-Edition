# Транслитератор собственных имён (латиница -> кириллица, правила передачи толкиновских имён)
DIGRAPHS = [('sch','ш'),('th','т'),('dh','д'),('sh','ш'),('ch','ч'),('ph','ф'),('gh','г'),('kh','х'),
('ng','нг'),('ck','к'),('qu','кв'),('ee','и'),('ea','и'),('ae','э'),('ai','э'),('oo','у'),
('ou','ау'),('au','ау'),('eo','э'),('ow','оу'),('ui','уи'),('sc','ск'),('wr','р'),('wh','в'),
('kn','н'),('gn','н'),('ps','пс'),('rh','р')]
SINGLE = {'a':'а','b':'б','d':'д','e':'э','f':'ф','g':'г','i':'и','j':'дж','k':'к','l':'л','m':'м',
'n':'н','o':'о','p':'п','r':'р','s':'с','t':'т','u':'у','v':'в','w':'в','x':'кс','y':'и','z':'з',
'c':'к','q':'к','h':'х'}

def translit(word):
    w = word.lower().replace("'","").replace("’","").replace("´","").replace("-","").replace("_","")
    out = []
    i = 0
    start = True
    while i < len(w):
        if w[i:i+3] == "sch":
            matched = "ш"; i += 3
        else:
            two = w[i:i+2]
            matched = None
            for dig, r in DIGRAPHS:
                if two == dig:
                    matched = r; i += 2; break
            if matched is None:
                ch = w[i]
                if ch in SINGLE:
                    matched = SINGLE[ch]; i += 1
                else:
                    i += 1; continue
                if ch == "e":
                    matched = "э" if start else "е"
        start = False
        out.append(matched)
    return ''.join(out).capitalize()
