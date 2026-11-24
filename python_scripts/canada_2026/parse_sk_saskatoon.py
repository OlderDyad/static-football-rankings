import json, re, html
from datetime import datetime
ABBR = {"HC": "Holy Cross", "STJ": "St. Joseph", "STM": "St. Thomas More", "BJM": "Bishop James Mahoney",
        "AB": "Aden Bowman", "BETH": "Bethlehem", "EH": "Evan Hardy", "CENT": "Centennial", "WM": "Walter Murray",
        "TD": "Tommy Douglas", "MG": "Marion Graham", "MR": "Mount Royal", "BR": "Bedford Road", "EDF": "E.D. Feehan"}
def name(cell):
    n = html.unescape(re.sub("<[^>]+>", "", cell))
    m = re.search(r"\((\d+)\)", n); score = int(m.group(1)) if m else None
    n = re.sub(r"\(\d+\)", "", n).strip()
    jv = "Jr. Football" in n
    if " - " in n:
        n = ABBR.get(n.split(" - ")[0].strip().upper(), n.split(" - ")[0].strip())
        n = "Saskatoon " + n
    return n, score, jv
def parse_saskatoon(path="sk_sssad_fall2026.json"):
    d = json.load(open(path, encoding="utf-8"))
    out, other = [], []
    for g in d["data"]:
        if "otball" not in g["3"] + g["4"]: continue
        h, hs, hj = name(g["3"]); a, as_, aj = name(g["4"])
        if hs is None or as_ is None: other.append((g["0"], h, a)); continue
        jv = hj or aj
        typ = re.sub(r"<[^>]+>|\[Summary\]", "", g["2"]).strip()
        out.append(dict(Prov="SK", Source="SSSAD_Saskatoon", Level="JV" if jv else "12-man", Division=typ,
                        Date=datetime.strptime(g["0"], "%a %b %d, %Y").strftime("%Y-%m-%d"),
                        Home=h + (" JV" if hj else ""), Visitor=a + (" JV" if aj else ""),
                        Home_Score=hs, Visitor_Score=as_, Neutral=0, Note=typ if typ != "Game" else ""))
    return out, other
if __name__ == "__main__":
    o, other = parse_saskatoon()
    from collections import Counter
    print(len(o), Counter(x["Level"] for x in o), "unscored", len(other), other[:4])
    print(sorted({x[k] for x in o for k in ("Home", "Visitor")}))
