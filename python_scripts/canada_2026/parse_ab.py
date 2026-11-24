import re, html
from datetime import datetime
PLACEHOLDER = re.compile(r"^(#\d+|\d?A? ?#\d+|.*Finalist|.*#\d+|Winner.*|TBD|Zone.*|3A Zone)$", re.I)
def clean(n):
    n = re.sub(r"\s+", " ", n.replace("\xa0", " ")).strip()
    if " - " in n or " -" in n:
        n = re.split(r" -\s?", n)[-1].strip()
    n = re.sub(r"^(\d?A\s)?#\d+\s*-?\s*", "", n).strip()
    return n
def parse_ab(path="ab_2026_schedule.html"):
    s = open(path, encoding="utf-8", errors="replace").read()
    out, skipped = [], []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", s, flags=re.S):
        tds = [html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", "", c))).strip()
               for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S)]
        if len(tds) < 6 or not re.match(r"\d{1,2}-[A-Za-z]{3}-\d\d", tds[0]):
            continue
        d, lg, h, hs, a, as_ = tds[:6]
        if not (hs.isdigit() and as_.isdigit()):
            continue
        h, a = clean(h), clean(a)
        if not h or not a or PLACEHOLDER.match(h) or PLACEHOLDER.match(a):
            skipped.append((d, lg, tds[2], tds[4])); continue
        lvl = "6-man" if "6-a-side" in lg or "6aside" in lg else "9-man" if "9" in lg else "12-man"
        out.append(dict(Prov="AB", Source="FootballAlberta", Level=lvl, Division=lg,
                        Date=datetime.strptime(d, "%d-%b-%y").strftime("%Y-%m-%d"),
                        Home=h, Visitor=a, Home_Score=int(hs), Visitor_Score=int(as_), Neutral=0, Note=""))
    return out, skipped
if __name__ == "__main__":
    o, sk = parse_ab()
    from collections import Counter
    print(len(o), Counter(x["Level"] for x in o)); print("skipped", sk)
    print(sorted({x[k] for x in o for k in ("Home", "Visitor")}))
