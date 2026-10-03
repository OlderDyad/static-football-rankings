"""
auto_triage_ghostteam_wrongname.py  (v3 - adds autoclose for already-resolved)
=============================================================================
Semi-automated triage for mapping_conflict_audit.py's largest open cluster:
ConflictType='GhostTeam', Priority='High - same game, wrong opponent name'.

v3 CHANGES:
  - The "ALREADY_RESOLVED" / missing_row case (one or both linked HS_Scores
    rows no longer exist) now also emits a `close --status Fixed` command
    into a SEPARATE output file (ghostteam_wrongname_autoclose.ps1). This
    makes no data change -- it only closes a stale investigation tracking
    row -- so it's kept apart from the real `delete` commands in
    ghostteam_wrongname_autofix.ps1 for a clean, separate review pass.

v2 CHANGES (after spot-checking the v1 50-row sample found real problems):
  - DROPPED H3 (canonical-name-exists match) entirely. Proven wrong on
    investigation 118 (North Little Rock Jones (AR) vs Nash Jones Academy
    (OK)) -- the WRONG name ("North Little Rock Jones (AR)") was already
    sitting in a canonical table, so "exists in URL_ProperName_Mapping" is
    not evidence of correctness. Bad data can already be canonical.
  - STATE-MATCH GUARD, checked before anything else: if the two candidates'
    state suffixes differ, ALWAYS manual review, never auto-resolve. v1's
    H1 stripped state suffix before comparing, so "Clinton (OK)" vs
    "Clinton (AR)" would have been wrongly treated as "identical". This
    exact AR/OK (and similar) confusion is already a known recurring
    problem in this dataset (see the AliasReclassification queue: Altus,
    Clinton, Helena, Wilson, Fairview all have AR/OK confusion clusters).
  - H2 (substring) NARROWED: only fires when every "extra" word in the
    longer name is in a curated SAFE_FILLER set (geographic/institutional
    descriptors like "indian", "school", "boarding" -- seen in the Chilocco/
    Fort Sill Indian School style cases). If any extra word is a RISKY
    qualifier (central, academy, north/northeast/etc., mission, ...) that
    has, in this dataset, turned out to name a genuinely DIFFERENT real
    school (Tulsa vs Tulsa Central; Marlow vs Marlow Central; Fort Smith vs
    Fort Smith St. Anne's Academy; OKC Northeast vs OKC Northeast Academy),
    it's forced to MANUAL_REVIEW instead.

This script is READ-ONLY -- it never writes to the database. It produces:
  1. ghostteam_wrongname_triage.csv     -- every investigation triaged
  2. ghostteam_wrongname_autofix.ps1    -- ONLY the high-confidence AUTO
     `delete` commands (real data changes -- a duplicate row removed).
  3. ghostteam_wrongname_autoclose.ps1  -- ONLY `close --status Fixed`
     commands for investigations whose linked HS_Scores rows are already
     gone (no data change, just closes a stale tracking record).
  Review the CSV; nothing here has been run.

Usage:
    python auto_triage_ghostteam_wrongname.py --state "(OK)" --limit 50
    python auto_triage_ghostteam_wrongname.py --state "(OK)"
"""

import argparse
import csv
import re
import logging
from sqlalchemy import create_engine, text

# === CONFIGURATION (matches other scripts in this repo) ===
SERVER = 'McKnights-PC\\SQLEXPRESS01'
DATABASE = 'hs_football_database'
DRIVER = 'ODBC Driver 17 for SQL Server'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STATE_SUFFIX_RE = re.compile(r'\s*\(([A-Za-z]{2})\)\s*$')
PUNCT_RE = re.compile(r'[^a-z0-9\s]')
WS_RE = re.compile(r'\s+')

# Words that, when they're the ONLY difference between two candidate names,
# have proven in this dataset to indicate a genuinely DIFFERENT real school
# -- never auto-resolve across one of these, always flag for a human.
RISKY_WORDS = {
    "central", "academy", "north", "northeast", "northwest", "south",
    "southeast", "southwest", "east", "west", "high", "junior", "senior",
    "mission", "county", "consolidated", "public", "township", "prep",
    "christian", "community",
}

# Words that are safe to treat as non-identity-bearing filler when they're
# the only extra words in the longer name (geographic/institutional
# descriptors, not alternate-identity qualifiers).
SAFE_FILLER = {
    "indian", "school", "boarding", "agricultural", "institute",
}


def strip_state(name):
    """Return (base_name_without_suffix, state_code_or_None)."""
    if name is None:
        return "", None
    m = STATE_SUFFIX_RE.search(name)
    state = m.group(1).upper() if m else None
    base = STATE_SUFFIX_RE.sub('', name)
    return base, state


def normalize_base(base):
    """Lowercase, strip punctuation, collapse whitespace (state already stripped)."""
    n = base.lower()
    n = PUNCT_RE.sub(' ', n)
    n = WS_RE.sub(' ', n).strip()
    return n


def names_match_anchor(anchor, home, visitor):
    a = anchor.strip().lower()
    if home is not None and home.strip().lower() == a:
        return 'Home', visitor
    if visitor is not None and visitor.strip().lower() == a:
        return 'Visitor', home
    return None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', default='(OK)')
    parser.add_argument('--limit', type=int, default=None, help='Only process the first N investigations (for testing)')
    parser.add_argument('--csv-out', default='ghostteam_wrongname_triage.csv')
    parser.add_argument('--ps1-out', default='ghostteam_wrongname_autofix.ps1')
    parser.add_argument('--autoclose-out', default='ghostteam_wrongname_autoclose.ps1')
    args = parser.parse_args()

    conn_str = f"mssql+pyodbc://@{SERVER}/{DATABASE}?driver={DRIVER}&trusted_connection=yes"
    engine = create_engine(conn_str)

    with engine.connect() as conn:
        inv_query = text("""
            SELECT InvestigationID, AnchorTeam, State, Season
            FROM HS_Mapping_Investigations
            WHERE State = :state
              AND ConflictType = 'GhostTeam'
              AND Status = 'New'
              AND Priority = 'High - same game, wrong opponent name'
            ORDER BY InvestigationID
        """)
        investigations = conn.execute(inv_query, {"state": args.state}).fetchall()

        if args.limit:
            investigations = investigations[:args.limit]

        logger.info(f"Found {len(investigations)} open investigations to triage.")

        csv_rows = []
        auto_commands = []
        autoclose_commands = []
        auto_count = 0
        manual_count = 0

        for inv in investigations:
            inv_id = inv.InvestigationID
            anchor = inv.AnchorTeam
            season = inv.Season

            games = conn.execute(
                text("SELECT ScoresID FROM HS_Mapping_Investigation_Games WHERE InvestigationID = :iid"),
                {"iid": inv_id}
            ).fetchall()
            scores_ids = [g.ScoresID for g in games]

            if len(scores_ids) != 2:
                csv_rows.append({
                    "InvestigationID": inv_id, "AnchorTeam": anchor, "Season": season,
                    "Recommendation": "MANUAL_REVIEW", "Heuristic": f"cluster_size={len(scores_ids)}",
                    "Reasoning": "Investigation does not have exactly 2 linked games",
                })
                manual_count += 1
                continue

            rows = []
            for sid in scores_ids:
                r = conn.execute(
                    text("""SELECT ID, Date, Home, Visitor, Home_Score, Visitor_Score, Source
                             FROM HS_Scores WHERE ID = :sid"""),
                    {"sid": sid}
                ).fetchone()
                rows.append(r)

            if any(r is None for r in rows):
                csv_rows.append({
                    "InvestigationID": inv_id, "AnchorTeam": anchor, "Season": season,
                    "Recommendation": "ALREADY_RESOLVED", "Heuristic": "missing_row",
                    "Reasoning": "One or both HS_Scores rows no longer exist (already cleaned up) - just needs `close --status Fixed`",
                })
                auto_count += 1
                reason_text = (
                    "Auto-triage v3 (missing_row): one or both linked HS_Scores rows "
                    "no longer exist - investigation already resolved by a prior pass, "
                    "closing stale tracking record only (no data change)."
                )
                autoclose_commands.append(
                    f'python mapping_conflict_audit.py close --investigation {inv_id} '
                    f'--status Fixed --reason "{reason_text}"'
                )
                continue

            rowA, rowB = rows
            sideA, candA = names_match_anchor(anchor, rowA.Home, rowA.Visitor)
            sideB, candB = names_match_anchor(anchor, rowB.Home, rowB.Visitor)

            if sideA is None or sideB is None:
                csv_rows.append({
                    "InvestigationID": inv_id, "AnchorTeam": anchor, "Season": season,
                    "Row1_ID": rowA.ID, "Row1_Date": rowA.Date, "Row1_Home": rowA.Home, "Row1_Visitor": rowA.Visitor, "Row1_Source": rowA.Source,
                    "Row2_ID": rowB.ID, "Row2_Date": rowB.Date, "Row2_Home": rowB.Home, "Row2_Visitor": rowB.Visitor, "Row2_Source": rowB.Source,
                    "Recommendation": "MANUAL_REVIEW", "Heuristic": "anchor_name_no_exact_match",
                    "Reasoning": "AnchorTeam string didn't exactly match Home/Visitor on one or both rows",
                })
                manual_count += 1
                continue

            baseA, stateA = strip_state(candA)
            baseB, stateB = strip_state(candB)
            normA, normB = normalize_base(baseA), normalize_base(baseB)

            base_info = {
                "InvestigationID": inv_id, "AnchorTeam": anchor, "Season": season,
                "Row1_ID": rowA.ID, "Row1_Date": rowA.Date, "Row1_Candidate": candA, "Row1_Source": rowA.Source, "Row1_Side": sideA,
                "Row2_ID": rowB.ID, "Row2_Date": rowB.Date, "Row2_Candidate": candB, "Row2_Source": rowB.Source, "Row2_Side": sideB,
            }

            keep_row, delete_row, heuristic, reasoning = None, None, None, None

            # --- STATE-MATCH GUARD: never auto-resolve across differing states ---
            if stateA and stateB and stateA != stateB:
                heuristic = "STATE_MISMATCH"
                reasoning = f"'{candA}' ({stateA}) vs '{candB}' ({stateB}) -- different states, needs manual verification (known recurring confusion pattern in this dataset)"

            elif normA == normB:
                # identical base name, same (or unstated) state -- pure formatting difference
                keep_row, delete_row = rowA, rowB  # equivalent names, arbitrary which survives
                heuristic = "H1_IDENTICAL_AFTER_NORMALIZE"
                reasoning = f"'{candA}' and '{candB}' are the same name after normalization (same state)"

            elif normA and normB and (normA in normB or normB in normA):
                shorter, longer = (normA, normB) if len(normA) <= len(normB) else (normB, normA)
                extra_words = set(longer.split()) - set(shorter.split())
                if extra_words and extra_words.issubset(SAFE_FILLER):
                    if len(normA) <= len(normB):
                        keep_row, delete_row = rowA, rowB
                    else:
                        keep_row, delete_row = rowB, rowA
                    heuristic = "H2_SUBSTRING_SAFE"
                    reasoning = f"'{candA}' / '{candB}' -- extra word(s) {sorted(extra_words)} are non-identity-bearing filler"
                elif extra_words & RISKY_WORDS:
                    heuristic = "SUBSTRING_BUT_RISKY_QUALIFIER"
                    reasoning = f"'{candA}' / '{candB}' -- extra word(s) {sorted(extra_words & RISKY_WORDS)} have historically named a DIFFERENT real school in this dataset - needs manual verification"
                else:
                    heuristic = "SUBSTRING_UNKNOWN_QUALIFIER"
                    reasoning = f"'{candA}' / '{candB}' -- extra word(s) {sorted(extra_words)} not in the safe-filler or risky list - needs manual verification"

            else:
                heuristic = "NONE"
                reasoning = f"No heuristic resolved '{candA}' vs '{candB}'"

            if keep_row is not None:
                base_info["Recommendation"] = "AUTO"
                base_info["Heuristic"] = heuristic
                base_info["Reasoning"] = reasoning
                base_info["KeepID"] = keep_row.ID
                base_info["DeleteID"] = delete_row.ID
                csv_rows.append(base_info)
                auto_count += 1

                reason_text = f"Auto-triage v2 ({heuristic}): {reasoning}"
                auto_commands.append(
                    f'python mapping_conflict_audit.py delete --id {delete_row.ID} '
                    f'--investigation {inv_id} --reason "{reason_text}"'
                )
            else:
                base_info["Recommendation"] = "MANUAL_REVIEW"
                base_info["Heuristic"] = heuristic
                base_info["Reasoning"] = reasoning
                csv_rows.append(base_info)
                manual_count += 1

    fieldnames = [
        "InvestigationID", "AnchorTeam", "Season", "Recommendation", "Heuristic", "Reasoning",
        "KeepID", "DeleteID",
        "Row1_ID", "Row1_Date", "Row1_Candidate", "Row1_Side", "Row1_Source",
        "Row2_ID", "Row2_Date", "Row2_Candidate", "Row2_Side", "Row2_Source",
        "Row1_Home", "Row1_Visitor", "Row2_Home", "Row2_Visitor",
    ]
    with open(args.csv_out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    with open(args.ps1_out, 'w', encoding='utf-8') as f:
        f.write("# Auto-generated by auto_triage_ghostteam_wrongname.py (v3)\n")
        f.write("# REVIEW BEFORE RUNNING. These are real data changes (duplicate row deletes).\n")
        f.write(f"# Total auto-resolved deletes: {len(auto_commands)}\n\n")
        for cmd in auto_commands:
            f.write(cmd + "\n")

    with open(args.autoclose_out, 'w', encoding='utf-8') as f:
        f.write("# Auto-generated by auto_triage_ghostteam_wrongname.py (v3)\n")
        f.write("# REVIEW BEFORE RUNNING. No data change -- closes stale tracking rows only\n")
        f.write("# (linked HS_Scores rows already gone, resolved by a prior pass).\n")
        f.write(f"# Total auto-close: {len(autoclose_commands)}\n\n")
        for cmd in autoclose_commands:
            f.write(cmd + "\n")

    logger.info(f"Done. {auto_count} AUTO-resolved ({len(auto_commands)} delete + {len(autoclose_commands)} close), {manual_count} flagged MANUAL_REVIEW.")
    logger.info(f"CSV report: {args.csv_out}")
    logger.info(f"Delete commands ({len(auto_commands)} lines): {args.ps1_out}")
    logger.info(f"Close commands ({len(autoclose_commands)} lines): {args.autoclose_out}")


if __name__ == "__main__":
    main()
