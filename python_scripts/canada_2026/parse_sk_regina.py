import re, html
from datetime import datetime
def parse_regina(path="sk_regina_2026.html"):
    s = open(path, encoding="utf-8", errors="replace").read()
    i = s.find("2026-2027 Schedule"); s = s[i:]
    j = s.find("2025-2026 Schedule"); s = s[:j] if j > 0 else s
    out, other = [], []
    # Playoff rows name teams by seed ("Schwann 3rd"); resolve from the final standings tables.
    seeds = {}
    full = open(path, encoding="utf-8", errors="replace").read()
    for conf in ("Schwann", "Stewart"):
        blk = full[full.find(">" + conf + "</p>"):]
        blk = blk[:blk.find("</tbody>")]
        teams = [html.unescape(t.strip()) for t in re.findall(r"<tr[^>]*>\s*<td>([^<]+)</td>", blk)]
        for n, t in enumerate(teams, 1):
            seeds[f"{conf} {n}{'st' if n==1 else 'nd' if n==2 else 'rd' if n==3 else 'th'}"] = t
    for r in re.findall(r"<tr>(.*?)</tr>", s, flags=re.S):
        tds = [html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", "", c))).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", r, flags=re.S)]
        if len(tds) < 3: continue
        mh = re.match(r"(.*?)\s*\((\d+)\s*FT\)", tds[0]); ma = re.match(r"(.*?)\s*\((\d+)\s*FT\)", tds[1])
        if not (mh and ma): other.append(tds[:3]); continue
        out.append(dict(Prov="SK", Source="RHSAA_Regina", Level="12-man", Division="RHSAA",
                        Date=datetime.strptime(tds[2], "%B %d %Y").strftime("%Y-%m-%d"),
                        Home=seeds.get(mh.group(1).strip(), mh.group(1).strip()), Visitor=seeds.get(ma.group(1).strip(), ma.group(1).strip()),
                        Home_Score=int(mh.group(2)), Visitor_Score=int(ma.group(2)), Neutral=0, Note=""))
    return out, other
if __name__ == "__main__":
    o, other = parse_regina()
    print(len(o), "unscored:", other[:10])
    print(sorted({x[k] for x in o for k in ("Home", "Visitor")}))
    print(o[-4:])
