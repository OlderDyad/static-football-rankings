"""
college_names.py -- match an outside school name to a College_Team_Names name.

Used by the coach loaders (Access tenures, Wikipedia current-coach lists,
carousel pages). Tries, in order: exact / alias, then normalized forms
("State" -> "St", "Saint" -> "St", dashes, "(TX)" -> " TX", dropping
"University"/"College", dropping a trailing mascot), restricted to teams that
played in the given season when one is passed.
"""
import csv, os, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())

MANUAL = {   # outside spelling -> Wolfe/Access name (checked against the team list at load)
    "ul-lafayette": "Louisiana-Lafayette", "ul-monroe": "Louisiana-Monroe", "ohio u": "Ohio",
    "davidison": "Davidson", "georgetown": "Georgetown DC", "fiu": "Florida Int'l",
    "saint john's mn": "St John's MN", "nc-pembroke": "UNC-Pembroke", "grambling": "Grambling St",
    "hawaii": "Hawai`i", "school": None,
}


def norm(s):
    s = s.lower().replace("–", "-").replace("—", "-").replace("’", "'").replace("&", " and ")
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bstate\b", "st", s)
    # Wolfe abbreviations
    s = re.sub(r"\bsoutheast(ern)?\b", "se", s)
    s = re.sub(r"\bsouthwest(ern)?\b", "sw", s)
    s = re.sub(r"\binternational\b", "intl", s)
    s = re.sub(r"\bint'l\b", "intl", s)
    s = re.sub(r"\bconnecticut\b", "conn", s)
    s = re.sub(r"\b(university|college|univ|the|of)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


class Matcher:
    def __init__(self):
        self.teams = {}
        for r in csv.DictReader(open(os.path.join(HERE, "name_fixes", "college_team_names.csv"), encoding="utf-8")):
            self.teams[r["Team_Name"]] = r
        self.alias = {r["Alias_Name"].lower(): r["Canonical_Name"]
                      for r in csv.DictReader(open(os.path.join(HERE, "name_fixes", "college_team_aliases.csv"), encoding="utf-8"))}
        self.lower = {t.lower(): t for t in self.teams}
        self.by_norm = defaultdict(list)
        for t in self.teams:
            self.by_norm[norm(t)].append(t)

    def _pick(self, cands, season, state):
        cands = list(dict.fromkeys(cands))
        if season:
            live = [c for c in cands if int(self.teams[c]["First_Season"] or 0) <= season <= int(self.teams[c]["Last_Season"] or 9999)]
            cands = live or cands
        if state and len(cands) > 1:
            st = [c for c in cands if self.teams[c]["State"] == state]
            cands = st or cands
        if len(cands) > 1:   # prefer real colleges with the most games
            cands.sort(key=lambda c: (self.teams[c]["Kind"] != "College", -int(self.teams[c]["Games"] or 0)))
        return cands

    def match(self, name, season=None, state=None, mascot=False):
        """Returns (team_name or None, how, alternatives)."""
        raw = re.sub(r"\s+", " ", (name or "").strip())
        if not raw:
            return None, "blank", []
        k = raw.lower()
        if k in MANUAL:
            t = MANUAL[k]
            return (t, "manual", []) if t and t in self.teams else (None, "manual-none", [])
        if k in self.lower:
            return self.lower[k], "exact", []
        if k in self.alias and self.alias[k] in self.teams:
            return self.alias[k], "alias", []
        m = re.match(r"^(.*?)\s*\(([A-Za-z]{2})\)$", raw)          # "Trinity (TX)"
        tries = []
        if m:
            st = m.group(2).upper()
            state = state or (st if st in STATES else None)
            tries += [f"{m.group(1)} {st}", m.group(1)]
        tries.append(raw)
        if mascot:                                                  # "Barton Bulldogs" -> "Barton"
            words = raw.split()
            for k2 in range(len(words) - 1, 0, -1):
                tries.append(" ".join(words[:k2]))
        for t in tries:
            if t.lower() in self.lower:
                return self.lower[t.lower()], "variant", []
            n = norm(t)
            c = self.by_norm.get(n)
            if not c:   # Wolfe adds " St" or a state code: "Central Conn" -> "Central Conn St", "Huntingdon" -> "Huntingdon AL"
                c = [x for suf in ["st"] + ([state.lower()] if state else [s.lower() for s in STATES])
                     for x in self.by_norm.get(n + suf, [])]
            if c:
                c = self._pick(c, season, state)
                return c[0], ("normalized" if len(c) == 1 else "normalized-ambiguous"), c[1:]
        return None, "no match", []
