"""Parse WECSSAA viewScores.php text copied from the browser (Ctrl+A, Ctrl+C, paste to .txt).
Format: a date line ('Thursday, September 17, 2026'), then 'Visitor<TAB>Score<TAB>Score<TAB>Home',
then ' Team<TAB>vs<TAB>hs<TAB> Team', then optional notes and a 'Location: ... Notes: ...' line."""
import re, sys
from datetime import datetime
DATE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ([A-Z][a-z]+ \d{1,2}, \d{4})\s*$")
GAME = re.compile(r"^\s*(.+?)\t(\d+)\t(\d+)\t\s*(.+?)\s*$")
def parse_wecssaa(path, source="WECSSAA"):
    out, date, level, last = [], None, "Senior", None
    for line in open(path, encoding="utf-8-sig"):
        line = line.rstrip("\r\n")
        if re.search(r"Junior.*Football", line): level = "Junior"
        if re.search(r"Senior.*Football", line): level = "Senior"
        m = DATE.match(line)
        if m: date = datetime.strptime(m.group(2), "%B %d, %Y").strftime("%Y-%m-%d"); continue
        g = GAME.match(line)
        if g and date and not line.startswith("Visitor"):
            last = dict(Prov="ON", Source=source, Level=level, Division=source, Date=date,
                        Home=g.group(4).strip(), Visitor=g.group(1).strip(),
                        Home_Score=int(g.group(3)), Visitor_Score=int(g.group(2)), Neutral=0, Note="")
            out.append(last); continue
        if line.startswith("Location:") and last:
            n = re.search(r"Notes:\s*(.*?)\.?\s*$", line)
            last["Note"] = n.group(1).strip() if n else ""
            last["Neutral"] = 0 if "Regular" in last["Note"] else 1
            last = None
    return out
if __name__ == "__main__":
    o = parse_wecssaa(sys.argv[1] if len(sys.argv) > 1 else "wecssaa2026.txt")
    from collections import Counter
    print(len(o), Counter(x["Note"] for x in o), Counter(x["Level"] for x in o))
    print(min(x["Date"] for x in o), max(x["Date"] for x in o))
    print(sorted({x[k] for x in o for k in ("Home", "Visitor")}))
