import json, re, html
from datetime import datetime
def parse_mb(path="mb_whsfl_2026.json"):
    d = json.load(open(path, encoding="utf-8"))
    out, other = [], []
    def ts(cell):
        name = html.unescape(re.sub("<[^>]+>", "", cell.split("<span style")[0])).strip()
        m = re.search(r"\((\d+)\)\s*</span>\s*$", cell)
        return name, (int(m.group(1)) if m else None)
    for g in d["data"]:
        h, hs = ts(g["3"]); a, as_ = ts(g["4"])
        if hs is None or as_ is None: other.append((g["0"], h, a)); continue
        typ = re.sub("<[^>]+>|\[Summary\]", "", g["2"]).strip()
        jv = " JV" in h or " JV" in a
        out.append(dict(Prov="MB", Source="WHSFL_Manitoba", Level="JV" if jv else "Varsity", Division=typ,
                        Date=datetime.strptime(g["0"], "%a %b %d, %Y").strftime("%Y-%m-%d"),
                        Home=h, Visitor=a, Home_Score=hs, Visitor_Score=as_, Neutral=0, Note=typ if "Playoff" in typ or "Final" in typ else ""))
    return out, other
if __name__ == "__main__":
    o, other = parse_mb()
    from collections import Counter
    print(len(o), Counter(x["Level"] for x in o), "unscored", other[:5])
    print(sorted({x[k] for x in o if x["Level"]=="Varsity" for k in ("Home", "Visitor")}))
    print(min(x["Date"] for x in o), max(x["Date"] for x in o))
