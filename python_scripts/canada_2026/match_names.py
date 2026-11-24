import csv, re
from collections import defaultdict
db = list(csv.DictReader(open("canada_db_names.csv", encoding="utf-8")))
byprov = defaultdict(list)
for r in db: byprov[r["Name"].strip()[-3:-1].upper()].append(r)
STOP = {"the", "of", "high", "school", "secondary", "collegiate", "institute", "regional", "catholic", "jv", "aa", "aaa", "jr", "sr"}
MASCOTS = set("""raiders lancers pirates clippers reivers marauders buckeyes sabres tigers celtics crusaders huskies hornets trojans vikings wolverines royals
broncos bulldogs plainsmen maroons eagles giants muskies gophers pipers kodiaks spartans""".split())
ABBR = {"mt": "mount", "st": "st", "saint": "st", "ft": "fort", "sask": "saskatchewan", "arch": "archbishop", "aca": "academy",
        "hgts": "heights", "cres": "crescent", "b": "bishop", "g": "george", "w": "william", "olr": "our lady rockies"}
def toks(s):
    s = re.sub(r"\((?:[A-Z]{2}|Alberta|Toronto|Jr\.|JV|RD|CAL|MH)\)", " ", s)
    out = []
    for t in re.findall(r"[a-z0-9']+", s.lower().replace(".", " ")):
        t = ABBR.get(t, t)
        for u in t.split():
            if u not in STOP and u not in MASCOTS: out.append(u.strip("'"))
    return out
def score(src, dbn):
    a, b = toks(src), set(toks(dbn))
    if not a: return 0
    hit = sum(1 for t in a if t in b or any(x.startswith(t) and len(t) >= 3 for x in b))
    return hit / len(a)
def best(src, prov, jv=False):
    cands = []
    for r in byprov.get(prov, []):
        n = r["Name"]; isjv = " JV" in n
        if isjv != jv: continue
        s = score(src, n)
        if s > 0: cands.append((s, int(r["LastSeason"]), int(r["Games"]), n))
    cands.sort(reverse=True)
    return cands[:3]
if __name__ == "__main__":
    src = [l.rstrip("\n").split("\t") for l in open("west_2026_team_names.txt", encoding="utf-8")]
    with open("west_match_review.tsv", "w", encoding="utf-8") as f:
        for p, n in src:
            m = re.search(r"\((SK|BC|AB|MB|ON|WY|Alberta|Toronto)\)$", n)
            prov = {"Alberta": "AB", "Toronto": "ON"}.get(m.group(1), m.group(1)) if m else p
            jv = bool(re.search(r"\bJV\b|\(JV\)|\(Jr\.\)", n))
            c = best(n, prov, jv)
            f.write("\t".join([p, n, prov, str(jv)] + [f"{s:.2f}|{ls}|{g}|{dn}" for s, ls, g, dn in c]) + "\n")
