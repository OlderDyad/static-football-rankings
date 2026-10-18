"""
wolfe_weekly.py  -- run on Windows after Wolfe's Sunday update. Preview by default.

Reads wolferatings.com:
  scores.htm     played games, current season  -> dbo.College_Scores
  schedules.htm  full season schedule          -> dbo.College_Future_Games (unplayed only)

Fixed-width lines:
  scores:    27-Aug-26 Western New Mexico          62 Adams St                    45 [Location]
  schedules: 27-Aug-26 Rocky Mountain                Mary                          Glendive MT
             29-Aug-26 Lafayette                     Georgetown DC                 Cancelled WX
A location means a neutral or semi-neutral site -> Neutral = 1.

Scores are matched to games already in College_Scores (same season, same two teams in
either home/away order, dates within 3 days or the old date is the Aug-1 placeholder):
  NEW        not in the table               -> inserted (Source = 'Wolfe')
  SAME       same score                     -> nothing
  CHANGED    different score                -> listed only; fix by hand (or --update-scores)
Team names not in College_Team_Names are listed (new programs or spelling changes);
games with unknown names are still loaded unless --skip-unknown.

Outputs (python_scripts/college/wolfe_weekly/):
  scores_parsed.csv, schedule_parsed.csv, scores_actions.csv, unknown_names.csv

Usage:  python wolfe_weekly.py                    (download + preview)
        python wolfe_weekly.py --commit           (download + load)
        python wolfe_weekly.py --scores-file scores.htm --schedule-file schedules.htm
"""
import argparse, csv, html, os, re, sys
from collections import Counter
from datetime import datetime, timedelta

import pyodbc

CONN = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
        "DATABASE=hs_football_database;Trusted_Connection=yes;TrustServerCertificate=yes;")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "wolfe_weekly")
URLS = {"scores": "https://wolferatings.com/scores.htm",
        "schedule": "https://wolferatings.com/schedules.htm"}
HEADERS = {"User-Agent": "McKnightFootballRankings/1.0 (personal research)"}

DATE = r"(\d{1,2}-[A-Za-z]{3}-\d{2})"
SCORE_RE = re.compile(DATE + r" (.+?)\s+(\d{1,3}) (.+?)\s+(\d{1,3})(?:\s+(\S.*?))?\s*$")


def page_text(path_or_url):
    if os.path.exists(path_or_url):
        raw = open(path_or_url, encoding="utf-8", errors="replace").read()
    else:
        import requests
        r = requests.get(path_or_url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        raw = r.text
    raw = re.sub(r"(?is)<(script|style).*?</\1>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    return html.unescape(re.sub(r"<[^>]+>", "", raw)).replace("\xa0", " ").replace("\r", "")


def clean_name(t):
    """strip stray characters Wolfe sometimes leaves at the end of a field (e.g. "Wofford   '")"""
    return re.sub(r"\s{2,}", " ", re.sub(r"[\s'\"`,;:]+$", "", t.strip())) if t else t


def clean_location(t):
    """a location must contain letters; a lone stray digit or quote is not a site"""
    t = (t or "").strip()
    return t if re.search(r"[A-Za-z]{2}", t) else ""


def game_date(s):
    return datetime.strptime(s, "%d-%b-%y").date()


def season_of(d):
    return d.year - 1 if d.month <= 6 else d.year          # January bowls belong to the fall


def parse_scores(text):
    games, bad = [], []
    for line in text.split("\n"):
        if not re.match(DATE + " ", line):
            continue
        m = SCORE_RE.match(line.rstrip())
        if not m:
            bad.append(line)
            continue
        d = game_date(m.group(1))
        games.append(dict(Date=d, Season=season_of(d), Visitor=clean_name(m.group(2)),
                          Visitor_Score=int(m.group(3)), Home=clean_name(m.group(4)),
                          Home_Score=int(m.group(5)), Location=clean_location(m.group(6))))
    return games, bad


def parse_schedule(text):
    games = []
    for line in text.split("\n"):
        if not re.match(DATE + " ", line):
            continue
        line = line.rstrip()
        vis, home, note = clean_name(line[10:40]), clean_name(line[40:70]), line[70:].strip()
        if not vis or not home:
            continue
        d = game_date(line[:9].strip())
        status = "Cancelled" if re.search(r"(?i)cancel|postpon", note) else "Scheduled"
        games.append(dict(Date=d, Season=season_of(d), Visitor=vis, Home=home,
                          Location="" if status == "Cancelled" else clean_location(note),
                          Status=status, Note=note if status == "Cancelled" else ""))
    return games


def write_csv(name, rows, cols):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores-file")
    ap.add_argument("--schedule-file")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--update-scores", action="store_true", help="overwrite CHANGED scores with Wolfe's")
    ap.add_argument("--skip-unknown", action="store_true")
    ap.add_argument("--parse-only", action="store_true", help="no database (parser test)")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    stext = page_text(a.scores_file or URLS["scores"])
    through = re.search(r"Scores through ([A-Za-z]+ \d{1,2}, \d{4})", stext)
    scores, bad = parse_scores(stext)
    sched = parse_schedule(page_text(a.schedule_file or URLS["schedule"]))
    print(f"Scores page: {len(scores):,} games" + (f" (through {through.group(1)})" if through else "")
          + (f"; {len(bad)} lines not understood" if bad else ""))
    for b in bad[:10]:
        print("   ?", b)
    played = {(g["Season"], g["Visitor"], g["Home"]) for g in scores}
    future = [g for g in sched if (g["Season"], g["Visitor"], g["Home"]) not in played]
    print(f"Schedule page: {len(sched):,} games; {len(future):,} not yet played "
          f"({sum(1 for g in future if g['Status'] == 'Cancelled')} cancelled)")
    write_csv("scores_parsed.csv", scores, ["Date", "Season", "Visitor", "Visitor_Score", "Home", "Home_Score", "Location"])
    write_csv("schedule_parsed.csv", future, ["Date", "Season", "Visitor", "Home", "Location", "Status", "Note"])
    if a.parse_only:
        return

    conn = pyodbc.connect(CONN)
    cur = conn.cursor()
    known = {r[0] for r in cur.execute("SELECT Team_Name FROM dbo.College_Team_Names")}
    unknown = Counter(t for g in scores + future for t in (g["Visitor"], g["Home"]) if t not in known)
    write_csv("unknown_names.csv", [{"Team": t, "Games": n} for t, n in unknown.most_common()], ["Team", "Games"])
    if unknown:
        print(f"{len(unknown)} team names not in College_Team_Names: "
              + ", ".join(f"{t} ({n})" for t, n in unknown.most_common(15)))

    seasons = sorted({g["Season"] for g in scores})
    existing = {}
    if seasons:
        ph = ",".join("?" * len(seasons))
        for aid, s, d, h, hs, v, vs in cur.execute(
                f"SELECT Access_ID, Season, Date, Home, Home_Score, Visitor, Visitor_Score "
                f"FROM dbo.College_Scores WHERE Season IN ({ph})", *seasons):
            existing.setdefault((s, frozenset((h, v))), []).append((aid, d, h, hs, v, vs))

    actions, used = [], set()
    for g in scores:
        cands = [e for e in existing.get((g["Season"], frozenset((g["Home"], g["Visitor"]))), [])
                 if e[0] not in used and (e[1] is None or (e[1].month == 8 and e[1].day == 1)
                                          or abs((e[1] - g["Date"]).days) <= 3)]
        if not cands:
            act, aid = "NEW", ""
        else:
            aid, d, h, hs, v, vs = cands[0]
            used.add(aid)
            mine = {h: hs, v: vs}
            act = "SAME" if (mine.get(g["Home"]), mine.get(g["Visitor"])) == (g["Home_Score"], g["Visitor_Score"]) \
                else "CHANGED"
        if act == "NEW" and a.skip_unknown and (g["Home"] not in known or g["Visitor"] not in known):
            act = "SKIPPED (unknown name)"
        actions.append(dict(g, Action=act, Access_ID=aid))
    c = Counter(x["Action"] for x in actions)
    print("Scores vs College_Scores: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
    write_csv("scores_actions.csv", actions, ["Action", "Access_ID", "Date", "Season", "Visitor", "Visitor_Score",
                                              "Home", "Home_Score", "Location"])
    for x in [x for x in actions if x["Action"] == "CHANGED"][:10]:
        print(f"   CHANGED {x['Date']} {x['Visitor']} {x['Visitor_Score']} @ {x['Home']} {x['Home_Score']} "
              f"(Access_ID {x['Access_ID']})")

    if not a.commit:
        print(f"\nPreview only -- files in {OUT}. Re-run with --commit to load.")
        return

    # College_Scores columns: fill what exists
    colinfo = {r[0]: r for r in cur.execute("""
        SELECT c.name, c.is_identity, c.is_computed, c.is_nullable, t.name, c.default_object_id
        FROM sys.columns c JOIN sys.types t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID('dbo.College_Scores')""")}
    # other required columns (e.g. ID) that have no identity/default: generate a value
    filled = {"Date", "Season", "Home", "Visitor", "Home_Score", "Visitor_Score", "Margin", "Neutral",
              "Location", "Source", "Future_Game", "Access_ID"}
    required = [c for c, r in colinfo.items() if c not in filled and not r[1] and not r[2]
                and not r[3] and not r[5]]
    counters = {}
    for c in required:
        if colinfo[c][4] in ("int", "bigint", "smallint"):
            counters[c] = (cur.execute(f"SELECT MAX([{c}]) FROM dbo.College_Scores").fetchone()[0] or 0) + 1
        elif colinfo[c][4] != "uniqueidentifier":
            print(f"Column {c} ({colinfo[c][4]}) is required and has no default -- cannot fill it.")
            return
    try:
        next_id = None
        if "Access_ID" in colinfo and not colinfo["Access_ID"][1]:
            next_id = (cur.execute("SELECT MAX(Access_ID) FROM dbo.College_Scores").fetchone()[0] or 0) + 1
            next_id = max(next_id, 900000000)             # keep scraper rows apart from Access IDs
        ins = upd = 0
        for x in actions:
            if x["Action"] == "NEW":
                vals = {"Date": x["Date"], "Season": x["Season"], "Home": x["Home"], "Visitor": x["Visitor"],
                        "Home_Score": x["Home_Score"], "Visitor_Score": x["Visitor_Score"],
                        "Margin": x["Home_Score"] - x["Visitor_Score"],
                        "Neutral": 1 if x["Location"] else 0, "Location": x["Location"] or None,
                        "Source": "Wolfe", "Future_Game": 0}
                if next_id is not None:
                    vals["Access_ID"] = next_id
                    next_id += 1
                for c in required:
                    if c in counters:
                        vals[c] = counters[c]
                        counters[c] += 1
                    else:
                        import uuid
                        vals[c] = str(uuid.uuid4())
                vals = {k: v for k, v in vals.items() if k in colinfo and not colinfo[k][1] and not colinfo[k][2]}
                cols = ", ".join(f"[{k}]" for k in vals)
                cur.execute(f"INSERT INTO dbo.College_Scores ({cols}) VALUES ({','.join('?' * len(vals))})",
                            *vals.values())
                ins += 1
            elif x["Action"] == "CHANGED" and a.update_scores:
                sets = "Home_Score = ?, Visitor_Score = ?" + (", Margin = ?" if "Margin" in colinfo
                                                             and not colinfo["Margin"][2] else "")
                args = [x["Home_Score"], x["Visitor_Score"]] + ([x["Home_Score"] - x["Visitor_Score"]]
                                                                if "Margin" in sets else [])
                # Wolfe's home/visitor order may differ from the stored row
                cur.execute(f"UPDATE dbo.College_Scores SET {sets} WHERE Access_ID = ? AND Home = ?",
                            *args, x["Access_ID"], x["Home"])
                if cur.rowcount == 0:
                    args = [x["Visitor_Score"], x["Home_Score"]] + ([x["Visitor_Score"] - x["Home_Score"]]
                                                                    if "Margin" in sets else [])
                    cur.execute(f"UPDATE dbo.College_Scores SET {sets} WHERE Access_ID = ?", *args, x["Access_ID"])
                upd += 1

        cur.execute("""IF OBJECT_ID('dbo.College_Future_Games','U') IS NULL
            CREATE TABLE dbo.College_Future_Games (
                ID INT IDENTITY(1,1) PRIMARY KEY, Season INT NOT NULL, Game_Date DATE NOT NULL,
                Visitor VARCHAR(111) NOT NULL, Home VARCHAR(111) NOT NULL, Location VARCHAR(111) NULL,
                Neutral BIT NOT NULL DEFAULT 0, Status VARCHAR(20) NOT NULL DEFAULT 'Scheduled',
                Note VARCHAR(255) NULL, Loaded_At DATETIME NOT NULL DEFAULT GETDATE())""")
        fseasons = sorted({g["Season"] for g in sched})
        for s in fseasons:
            cur.execute("DELETE FROM dbo.College_Future_Games WHERE Season = ?", s)
        for g in future:
            cur.execute("INSERT INTO dbo.College_Future_Games (Season, Game_Date, Visitor, Home, Location, Neutral, "
                        "Status, Note) VALUES (?,?,?,?,?,?,?,?)", g["Season"], g["Date"], g["Visitor"], g["Home"],
                        g["Location"] or None, 1 if g["Location"] else 0, g["Status"], g["Note"] or None)
        conn.commit()
        print(f"\nCommitted: {ins} new games inserted, {upd} scores updated; "
              f"College_Future_Games refreshed with {len(future)} unplayed games.")
    except Exception as e:
        conn.rollback()
        print(f"\nRolled back: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
