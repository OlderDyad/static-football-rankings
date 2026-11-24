import re, html, glob
from datetime import datetime
LEAGUES = {"6713": "AAA Varsity", "6714": "AA Varsity", "22265": "JV"}
def txt(x): return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", x))).strip()
def team(td):
    m = re.search(r'<span class="d-sm-inline d-none">(.*?)</span>', td, flags=re.S)
    name = txt(m.group(1)) if m else txt(td.split('<span class="divName"')[0])
    return name
def parse_bc():
    out, other = [], []
    for lid, lvl in LEAGUES.items():
        s = open(f"bc_2026_{lid}.html", encoding="utf-8", errors="replace").read()
        s = s[s.find('id="schedGames"'):]
        parts = re.split(r'<h5 class="h5heading[^>]*><strong>(.*?)</strong></h5>', s)
        for k in range(1, len(parts), 2):
            date = datetime.strptime(parts[k].strip(), "%a %b %d, %Y").strftime("%Y-%m-%d")
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", parts[k + 1], flags=re.S):
                tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)
                if len(tds) < 5: continue
                status, away, ascore, home, hscore = txt(tds[0]), team(tds[1]), txt(tds[2]), team(tds[3]), txt(tds[4])
                if not (ascore.isdigit() and hscore.isdigit()) or not status.startswith("Final"):
                    other.append((date, lvl, status, away, home)); continue
                out.append(dict(Prov="BC", Source="BC_HS_Football", Level=lvl, Division=lvl, Date=date,
                                Home=home, Visitor=away, Home_Score=int(hscore), Visitor_Score=int(ascore),
                                Neutral=0, Note="OT" if "OT" in status else ""))
    # A cross-league game (AAA vs AA) appears on both league pages: keep one copy.
    seen, dedup = set(), []
    for r in out:
        key = (r["Date"], r["Home"], r["Visitor"])
        if key in seen: continue
        seen.add(key); dedup.append(r)
    return dedup, other
if __name__ == "__main__":
    o, other = parse_bc()
    from collections import Counter
    print(len(o), Counter(x["Level"] for x in o), "not final:", len(other), other[:5])
    print(sorted({x[k] for x in o if x["Level"] != "JV" for k in ("Home", "Visitor")}))
