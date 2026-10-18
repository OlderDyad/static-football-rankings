"""
access_inventory.py
===================
Read-only inventory of the MS Access college football database, as step 1 of
moving college data into hs_football_database (College_Scores, College_Rankings,
coaches).

For every table and saved query it lists: columns (name, type, size, nullable),
row count, min/max of season/year/date-like columns, and 3 sample rows.
Nothing in the Access file is changed (the connection is opened ReadOnly).

Output: printed AND written to access_inventory_output.txt next to this script.

Usage (Windows, from this folder):
    python access_inventory.py
    python access_inventory.py "G:\\My Drive\\Documents\\Football\\College\\CFB 2023_09_03.accdb"

Needs the "Microsoft Access Driver (*.mdb, *.accdb)" ODBC driver with the same
bitness as Python (64-bit Python -> 64-bit Access Database Engine).
"""

import glob
import os
import sys
from datetime import date, datetime

import pyodbc

DEFAULT_PATH = r"C:\Users\demck\Google Drive\Documents\Football\College\CFB 2023_09_03.accdb"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(SCRIPT_DIR, "access_inventory_output.txt")

RANGE_HINTS = ("season", "year", "date", "week")
SAMPLE_ROWS = 3

_out = []


def say(line=""):
    print(line)
    _out.append(str(line))


def find_db(path):
    if os.path.exists(path):
        return path
    folder = os.path.dirname(path)
    hits = sorted(glob.glob(os.path.join(folder, "*.accdb")) + glob.glob(os.path.join(folder, "*.mdb")))
    if hits:
        say(f"NOTE: {path} not found; candidates in that folder:")
        for h in hits:
            say(f"   {h}")
    else:
        say(f"ERROR: {path} not found (and no .accdb/.mdb in {folder}).")
        say("Google Drive for desktop often mounts as G:\\My Drive\\... -- pass the real path as an argument.")
    return None


def fmt(v):
    if v is None:
        return "NULL"
    if isinstance(v, (datetime, date)):
        return v.isoformat()[:10]
    s = str(v).replace("\r", " ").replace("\n", " ")
    return s if len(s) <= 40 else s[:37] + "..."


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    say("=" * 78)
    say("ACCESS INVENTORY")
    say(f"Run: {datetime.now():%Y-%m-%d %H:%M}")
    say(f"File: {path}")
    say("=" * 78)

    drivers = [d for d in pyodbc.drivers() if "Access" in d]
    if not drivers:
        say("ERROR: No Microsoft Access ODBC driver found.")
        say(f"Python is {'64' if sys.maxsize > 2**32 else '32'}-bit; install the matching")
        say("'Microsoft Access Database Engine 2016 Redistributable'.")
        say(f"ODBC drivers present: {pyodbc.drivers()}")
        return
    db = find_db(path)
    if not db:
        return
    say(f"Driver: {drivers[0]}")
    say(f"Size: {os.path.getsize(db) / 1_048_576:.1f} MB")

    conn = pyodbc.connect(f"DRIVER={{{drivers[0]}}};DBQ={db};ReadOnly=1;")
    cur = conn.cursor()

    objs = [(t.table_name, t.table_type) for t in cur.tables()
            if t.table_type in ("TABLE", "VIEW", "SYNONYM", "LINK")
            and not t.table_name.startswith(("MSys", "~"))]
    tables = [o for o in objs if o[1] != "VIEW"]
    queries = [o for o in objs if o[1] == "VIEW"]

    say("")
    say(f"Tables: {len(tables)}   Saved select queries: {len(queries)}")
    for name, kind in tables:
        say(f"   [{kind}] {name}")
    if queries:
        say("Saved queries (names only):")
        for name, _ in queries:
            say(f"   {name}")

    for name, kind in tables:
        say("")
        say("-" * 78)
        say(f"TABLE: {name}   ({kind})")
        try:
            cols = [(c.column_name, c.type_name, c.column_size, c.nullable)
                    for c in cur.columns(table=name)]
        except Exception as e:
            say(f"   could not read columns: {e}")
            continue
        try:
            n = cur.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
        except Exception as e:
            n = f"? ({e})"
        say(f"Rows: {n}")
        say(f"{'#':>3}  {'Column':<38} {'Type':<14} {'Size':>6}  Null")
        for i, (cn, tn, sz, nl) in enumerate(cols, 1):
            say(f"{i:>3}  {cn:<38} {tn:<14} {sz!s:>6}  {'Y' if nl else 'N'}")

        for cn, tn, _, _ in cols:
            if any(h in cn.lower() for h in RANGE_HINTS) and tn.upper() not in ("LONGCHAR", "LONGBINARY"):
                try:
                    lo, hi = cur.execute(f"SELECT MIN([{cn}]), MAX([{cn}]) FROM [{name}]").fetchone()
                    say(f"   range {cn}: {fmt(lo)} .. {fmt(hi)}")
                except Exception:
                    pass

        try:
            rows = cur.execute(f"SELECT TOP {SAMPLE_ROWS} * FROM [{name}]").fetchall()
            if rows:
                say("Sample rows:")
                for r in rows:
                    say("   " + " | ".join(fmt(v) for v in r))
        except Exception as e:
            say(f"   sample failed: {e}")

    conn.close()
    say("")
    say("Done.")


if __name__ == "__main__":
    try:
        main()
    finally:
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(_out) + "\n")
        print(f"\nWritten: {OUT_FILE}")
