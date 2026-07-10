# master_scores_importer.py (v4 - Queue Integration)

# === IMPORTS ===
import os
import argparse
import pandas as pd
import re
import unicodedata
from sqlalchemy import create_engine, text
import logging
import uuid
from datetime import datetime
from fuzzywuzzy import process as fuzzy_process
from collections import defaultdict
import csv
import subprocess

# === CONFIGURATION ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"
GLOBAL_ALIAS_REGION = "*Global*"
# Sentinel standardized name committed by apply_corrections.py --final for
# Rule_Type='Ignore' rows. A team resolving to this value is intentionally
# excluded from import (not treated as unrecognized, not written to HS_Scores).
IGNORE_SENTINEL = "[IGNORED]"

# === Boilerplate Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

# === HELPER FUNCTIONS ===

# OCR occasionally misreads Latin letters as visually-identical Cyrillic/Greek
# characters (e.g. Cyrillic 'р' instead of Latin 'p' in "Shakoрее"). Since these
# aren't in [a-zA-Z0-9...], the old sanitizer stripped them outright -- which
# could reduce an entire name to nothing (triggering the [EMPTY/NULL...]
# placeholder) or leave a mangled fragment (e.g. "Εlv" -> "lv"). This map
# swaps the lookalikes back to Latin BEFORE that stripping regex runs.
HOMOGLYPH_MAP = {
    # Cyrillic lowercase -> Latin
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
    'і': 'i', 'ѕ': 's', 'ј': 'j', 'ԁ': 'd', 'ԛ': 'q', 'ѡ': 'w',
    'к': 'k', 'г': 'r', 'п': 'n', 'л': 'n',
    # Cyrillic uppercase -> Latin
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O',
    'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X', 'Ѕ': 'S', 'І': 'I', 'Ј': 'J',
    'Ү': 'Y', 'Ζ': 'Z', 'Г': 'R', 'П': 'N', 'Л': 'N',
    # Greek lowercase -> Latin
    'α': 'a', 'β': 'b', 'ε': 'e', 'ι': 'i', 'κ': 'k', 'ο': 'o', 'ρ': 'p',
    'τ': 't', 'υ': 'u', 'χ': 'x', 'ν': 'v',
    # Greek uppercase -> Latin
    'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Ι': 'I', 'Κ': 'K',
    'Μ': 'M', 'Ν': 'N', 'Ο': 'O', 'Ρ': 'P', 'Τ': 'T', 'Υ': 'Y', 'Χ': 'X',
    # Empirically observed project-specific OCR substitutions
    'ł': 't', 'Ł': 'T', 'ì': 'l',
}


def normalize_homoglyphs(text_input):
    """
    Recovers OCR'd names that were corrupted by homoglyph substitution
    (Cyrillic/Greek lookalikes for Latin letters) before sanitize_raw_team_name's
    aggressive non-ASCII-stripping regex would otherwise delete them entirely.
    Also folds standard accented Latin characters (u-umlaut, o-umlaut, etc.)
    down to their plain-ASCII base letter via NFKD decomposition.
    """
    if not text_input:
        return text_input
    out = ''.join(HOMOGLYPH_MAP.get(ch, ch) for ch in text_input)
    out = unicodedata.normalize('NFKD', out)
    out = ''.join(ch for ch in out if not unicodedata.combining(ch))
    return out


def sanitize_raw_team_name(text_input):
    """
    Cleans raw team names to handle common data entry issues before any processing.
    """
    if not isinstance(text_input, str):
        return ""
    text = text_input.replace(',', '')
    text = normalize_homoglyphs(text)
    text = re.sub(r'\.+$', '', text).strip()
    text = re.sub(r"[^a-zA-Z0-9\s\(\)&'\.-]", '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def sanitize_score(score_text):
    """
    Cleans the raw score string by removing any non-digit characters.
    This ensures values like "30," or '"21"' are correctly converted.
    """
    if not isinstance(score_text, str):
        return ""
    return re.sub(r'\D', '', score_text)

def sanitize_overtime(raw_value):
    """
    Converts raw OCR overtime text into a clean integer or None.

    Recognized patterns:
        OT, (OT), OT., ot               -> 1
        2OT, 2 OT, (2OT), (2 OT)        -> 2
        3OT, 3 OT, (3OT), (3 OT)        -> 3
        ... any N followed by OT         -> N
        (California Playoff), (Playoff)  -> 1  (any "playoff" mention = 1)
        Anything else                    -> None (field left blank)

    The field is non-critical — when in doubt, discard.
    """
    if not raw_value or not isinstance(raw_value, str):
        return None

    text = raw_value.strip()
    if not text:
        return None

    # Normalize: remove parentheses, lowercase, collapse whitespace
    normalized = text.lower()
    normalized = re.sub(r'[()]', '', normalized).strip()
    normalized = re.sub(r'\s+', ' ', normalized)

    # Pattern 1: explicit N OT  e.g. "2OT", "2 OT", "3 ot"
    m = re.match(r'^(\d+)\s*ot$', normalized)
    if m:
        return int(m.group(1))

    # Pattern 2: plain OT (no number) -> 1
    if normalized in ('ot', 'overtime', 'o.t.', 'o.t'):
        return 1

    # Pattern 3: any mention of "playoff" -> treat as single OT period
    if 'playoff' in normalized:
        return 1

    # Nothing recognized — discard silently
    return None

def clean_text_for_lookup(text_input):
    """
    Performs a simple normalization for dictionary lookups.
    """
    if not isinstance(text_input, str): return ""
    return text_input.lower().strip()

def load_all_aliases():
    logger.info("Loading alias and abbreviation rules from the database...")
    alias_query = text("SELECT Alias_Name, Standardized_Name, Newspaper_Region FROM dbo.HS_Team_Name_Alias")
    abbrev_query = text("SELECT Abbreviation, Standardized_Name, Newspaper_Region FROM dbo.HS_Team_Abbreviations")
    try:
        alias_df = pd.read_sql(alias_query, engine)
        alias_rules = defaultdict(dict)
        for _, row in alias_df.iterrows():
            alias_rules[str(row['Newspaper_Region']).strip()][clean_text_for_lookup(row['Alias_Name'])] = row['Standardized_Name']
        
        abbrev_df = pd.read_sql(abbrev_query, engine)
        abbrev_rules = defaultdict(dict)
        for _, row in abbrev_df.iterrows():
            abbrev_rules[str(row['Newspaper_Region']).strip()][clean_text_for_lookup(row['Abbreviation'])] = row['Standardized_Name']
            
        all_canonical_names = set(alias_df['Standardized_Name'].unique()) | set(abbrev_df['Standardized_Name'].unique())
        # Never suggest the Ignore sentinel as a fuzzy-match candidate for other names.
        all_canonical_names.discard(IGNORE_SENTINEL)
        return alias_rules, all_canonical_names, abbrev_rules
    except Exception as e:
        logger.exception("FATAL: Could not load rules from the database.")
        return None, None, None

def standardize_team_name(raw_name, source_region, alias_rules, abbrev_rules, all_canonical_names):
    if not isinstance(raw_name, str) or not raw_name.strip(): return None
    if raw_name in all_canonical_names: return raw_name
    
    normalized_raw_name = clean_text_for_lookup(raw_name)
    expanded_name = abbrev_rules.get(source_region, {}).get(normalized_raw_name, raw_name)
    if expanded_name == raw_name:
        expanded_name = abbrev_rules.get(GLOBAL_ALIAS_REGION, {}).get(normalized_raw_name, raw_name)
        
    name_to_check = clean_text_for_lookup(expanded_name)
    if name_to_check in alias_rules.get(source_region, {}):
        return alias_rules[source_region][name_to_check]
    if name_to_check in alias_rules.get(GLOBAL_ALIAS_REGION, {}):
        return alias_rules[GLOBAL_ALIAS_REGION][name_to_check]
        
    return None

def get_opponent_history_suggestions(opponents, all_canonical_names):
    if not opponents: return []
    escaped_opponents = ["'" + str(opp).replace("'", "''") + "'" for opp in opponents if opp]
    if not escaped_opponents: return []
    opponent_list_str = ", ".join(escaped_opponents)
    
    query = text(f"SELECT DISTINCT TeamName FROM (SELECT Home AS TeamName FROM HS_Scores WHERE Visitor IN ({opponent_list_str}) UNION SELECT Visitor AS TeamName FROM HS_Scores WHERE Home IN ({opponent_list_str})) AS OppsOfOpps;")
    try:
        df = pd.read_sql(query, engine)
        clean_candidates = [name for name in df['TeamName'].tolist() if name in all_canonical_names]
        return clean_candidates
    except Exception as e:
        logger.error(f"Could not get opponent history due to an error: {e}")
        return []

def generate_suggestions(unrecognized_name, opponents, all_canonical_names):
    logger.info(f"Generating suggestions for '{unrecognized_name}'...")
    opponent_candidates = get_opponent_history_suggestions(opponents, all_canonical_names)
    opponent_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, opponent_candidates, limit=3)]
    general_matches = [match[0] for match in fuzzy_process.extract(unrecognized_name, all_canonical_names, limit=3)]
    combined_suggestions = list(dict.fromkeys(opponent_matches + general_matches))
    return combined_suggestions[:3]

def extract_date_and_season(filename):
    match = re.search(r'_(\d{4})_(\d{2})_(\d{2})', filename)
    if match:
        year, month, day = map(int, match.groups())
        season = year if month >= 8 else year - 1
        return datetime(year, month, day).date(), season
    return None, None

def get_newspaper_region(filename):
    match = re.search(r'^(.+?)_\d{4}', filename)
    return match.group(1).replace('_', ' ').strip() if match else "Unknown"

def _safe_cell(value, default=''):
    """
    Convert a pandas cell to a clean string, treating NaN/missing as the
    given default instead of the literal text 'nan'.
    BUG FIX (was): str(row.get(col, '') or '') -- when a cell is genuinely
    blank, pandas represents it as float NaN. row.get() returns that NaN
    unchanged (the key exists, just with a NaN value, so the '' default
    never kicks in), and `nan or ''` evaluates to `nan` because NaN is
    truthy in Python. str(nan) then produces the literal text "nan", which
    got written into every blank Final_Proper_Name cell on regeneration.
    """
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    return s if s and s.lower() != 'nan' else default


def load_prior_annotations(correction_file_path):
    """
    Read any existing New_Alias_Suggestions.csv before it gets overwritten,
    and carry forward whatever the user already typed in (Final_Proper_Name,
    Rule_Type, Alias_Scope) for rows that are still unresolved. Without this,
    a manually-set 'Ignore' flag (or a Final_Proper_Name not yet applied)
    would be silently wiped every time this script regenerates the sheet.
    Keyed by (Unrecognized_Alias, Newspaper_Region).
    """
    if not os.path.exists(correction_file_path):
        return {}
    try:
        prior_df = pd.read_csv(correction_file_path, encoding='utf-8-sig')
    except Exception as e:
        logger.warning(f"Could not read prior correction sheet for annotation carry-forward: {e}")
        return {}

    annotations = {}
    for _, row in prior_df.iterrows():
        key = (_safe_cell(row.get('Unrecognized_Alias')), _safe_cell(row.get('Newspaper_Region')))
        annotations[key] = {
            'Final_Proper_Name': _safe_cell(row.get('Final_Proper_Name')),
            'Rule_Type': _safe_cell(row.get('Rule_Type'), default='Alias'),
            'Alias_Scope': _safe_cell(row.get('Alias_Scope'), default='Regional'),
            # Carried forward so gemini_alias_resolver.py's output survives a
            # master_scores_importer.py regeneration in between review passes.
            'AI_Suggested_Name': _safe_cell(row.get('AI_Suggested_Name')),
            'AI_Confidence': _safe_cell(row.get('AI_Confidence')),
            'AI_Reasoning': _safe_cell(row.get('AI_Reasoning')),
        }
    return annotations


def is_one_off(source_files_str, opponents_str):
    """Matches the same one-off check used by apply_corrections.py --final:
    a genuine one-off has exactly one source clipping and one opponent."""
    return (',' not in source_files_str) and (',' not in opponents_str)


def add_to_batch_queue(batch_id, file_count, game_count, source_files):
    """Add batch to queue using the batch_queue_manager script."""
    try:
        source_files_str = ','.join(source_files)
        cmd = [
            'python', 
            'batch_queue_manager.py', 
            'add', 
            batch_id, 
            str(file_count), 
            str(game_count), 
            source_files_str
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            logger.info(f"✅ Batch {batch_id} added to processing queue")
            return True
        else:
            logger.error(f"Failed to add batch to queue: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error adding batch to queue: {e}")
        return False

# === MAIN EXECUTION FUNCTION ===
def main():
    parser = argparse.ArgumentParser(description="Stage newspaper CSVs into RawScores_Staging, or preview what a real run would do.")
    parser.add_argument('--dry-run', action='store_true',
                         help="Preview mode. Still connects to the DB READ-ONLY (needed to know which team names "
                              "already resolve), but makes zero writes: nothing inserted into RawScores_Staging, "
                              "no batch queue entry, and New_Alias_Suggestions.csv / Ignored_Games_Log.csv are "
                              "written to '*_DryRunPreview.csv' copies instead of overwriting your real working files.")
    args = parser.parse_args()

    logger.info("--- Starting Data Ingestion with Queue Integration (v4) ---")
    if args.dry_run:
        logger.info("=== DRY RUN: read-only DB access for name matching, but NO writes will be made ===")

    batch_id = str(uuid.uuid4())
    logger.info(f"Generated new BatchID for this run: {batch_id}")

    alias_rules, all_canonical_names, abbrev_rules = load_all_aliases()
    if alias_rules is None: return

    staged_files = [f for f in os.listdir(STAGING_DIRECTORY) if f.lower().endswith('.csv') and 'new_alias_suggestions' not in f.lower()]
    if not staged_files:
        logger.warning("No .csv files found in staging directory."); return

    all_raw_games = []
    for file_name in staged_files:
        logger.info(f"Processing file: {file_name}")
        game_date, season = extract_date_and_season(file_name)
        source_region = get_newspaper_region(file_name)
        if not all([game_date, season, source_region]): continue
            
        file_path = os.path.join(STAGING_DIRECTORY, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            for line_num, row in enumerate(reader, 1):
                if not row or len(row) < 7: continue
                
                home_team = sanitize_raw_team_name(row[0])
                visitor_team = sanitize_raw_team_name(row[2])
                home_score = sanitize_score(row[1])
                visitor_score = sanitize_score(row[3])
                overtime_val = sanitize_overtime(row[4] if len(row) > 4 else '')
                quality_status = row[5] if len(row) > 5 else ''
                notes = row[6] if len(row) > 6 else ''
                
                all_raw_games.append({
                    'BatchID': batch_id, 'SourceFile': file_name, 'SourceRegion': source_region,
                    'GameDate': game_date, 'Season': season, 
                    'HomeTeamRaw': home_team, 'VisitorTeamRaw': visitor_team, 
                    'HomeScore': home_score, 'VisitorScore': visitor_score, 'Overtime': overtime_val,
                    'quality_status': quality_status, 'processing_notes': notes,
                    'LineNumber': line_num, 'RawLine': ','.join(row)
                })

    if not all_raw_games: 
        logger.warning("No valid game lines were parsed.")
        return

    unrecognized_teams_with_opponents = defaultdict(lambda: defaultdict(lambda: {'opponents': set(), 'source_files': set()}))
    games_to_import = []
    games_ignored = []

    for game in all_raw_games:
        if game['quality_status'] == 'needs_review': continue

        # Check for NULL/empty team names BEFORE standardization
        if not game['HomeTeamRaw'] or game['HomeTeamRaw'].strip() == '':
            info = unrecognized_teams_with_opponents[game['SourceRegion']]['[EMPTY/NULL HOME TEAM]']
            info['opponents'].add(game['VisitorTeamRaw'])
            info['source_files'].add(game['SourceFile'])
            continue

        if not game['VisitorTeamRaw'] or game['VisitorTeamRaw'].strip() == '':
            info = unrecognized_teams_with_opponents[game['SourceRegion']]['[EMPTY/NULL VISITOR TEAM]']
            info['opponents'].add(game['HomeTeamRaw'])
            info['source_files'].add(game['SourceFile'])
            continue

        home_std = standardize_team_name(game['HomeTeamRaw'], game['SourceRegion'], alias_rules, abbrev_rules, all_canonical_names)
        visitor_std = standardize_team_name(game['VisitorTeamRaw'], game['SourceRegion'], alias_rules, abbrev_rules, all_canonical_names)

        # A team resolving to the Ignore sentinel was explicitly given up on via
        # apply_corrections.py --final. Drop just this game -- don't import a
        # garbage team name, and don't treat it as newly-unrecognized either.
        if home_std == IGNORE_SENTINEL or visitor_std == IGNORE_SENTINEL:
            games_ignored.append(game)
            continue

        if not home_std:
            info = unrecognized_teams_with_opponents[game['SourceRegion']][game['HomeTeamRaw']]
            info['opponents'].add(visitor_std or game['VisitorTeamRaw'])
            info['source_files'].add(game['SourceFile'])
        if not visitor_std:
            info = unrecognized_teams_with_opponents[game['SourceRegion']][game['VisitorTeamRaw']]
            info['opponents'].add(home_std or game['HomeTeamRaw'])
            info['source_files'].add(game['SourceFile'])

        if home_std and visitor_std:
            game['HomeTeamStd'] = home_std
            game['VisitorTeamStd'] = visitor_std
            games_to_import.append(game)

    if games_ignored:
        logger.info(f"⏭  {'[DRY RUN] Would skip' if args.dry_run else 'Skipping'} {len(games_ignored)} game(s) involving a team marked Ignore (Rule_Type=Ignore, committed via --final).")
        try:
            log_filename = 'Ignored_Games_Log_DryRunPreview.csv' if args.dry_run else 'Ignored_Games_Log.csv'
            ignored_log_path = os.path.join(STAGING_DIRECTORY, log_filename)
            log_exists = os.path.exists(ignored_log_path) and not args.dry_run
            mode = 'w' if args.dry_run else 'a'
            with open(ignored_log_path, mode, newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not log_exists:
                    writer.writerow(['BatchID', 'SourceFile', 'SourceRegion', 'GameDate', 'HomeTeamRaw', 'VisitorTeamRaw', 'HomeScore', 'VisitorScore', 'RawLine'])
                for g in games_ignored:
                    writer.writerow([g['BatchID'], g['SourceFile'], g['SourceRegion'], g['GameDate'], g['HomeTeamRaw'], g['VisitorTeamRaw'], g['HomeScore'], g['VisitorScore'], g['RawLine']])
            if args.dry_run:
                logger.info(f"   Preview written to {ignored_log_path} (real Ignored_Games_Log.csv untouched).")
            else:
                logger.info(f"   Logged to {ignored_log_path} for your records (original clipping data is untouched).")
        except Exception as e:
            logger.warning(f"Could not write Ignored games log: {e}")

    if unrecognized_teams_with_opponents:
        logger.error("PROCESS STOPPED: Unrecognized teams found. Generating correction sheet...")

        correction_file_path = os.path.join(STAGING_DIRECTORY, 'New_Alias_Suggestions.csv')
        # Carry forward anything you've already typed in (Final_Proper_Name,
        # Rule_Type=Ignore, Alias_Scope) so an interim run doesn't wipe your
        # in-progress review. Only rows not yet committed via apply_corrections.py
        # will still show up here at all -- once committed, standardize_team_name
        # resolves them and they drop out of this list entirely.
        # (In dry-run this still reads your real sheet for the preview, it just
        # never writes back to it.)
        prior_annotations = load_prior_annotations(correction_file_path)

        correction_list = []
        for region, teams in unrecognized_teams_with_opponents.items():
            for team_name, data in teams.items():
                suggestions = generate_suggestions(team_name, data['opponents'], all_canonical_names)
                source_files_str = ', '.join(sorted(list(data['source_files'])))
                opponents_str = ', '.join(sorted(list(o for o in data['opponents'] if o)))

                prior = prior_annotations.get((team_name, region), {})

                correction_list.append({
                    'Unrecognized_Alias': team_name,
                    'Newspaper_Region': region,
                    'Source_Files': source_files_str,
                    'Opponents_Played': opponents_str,
                    'Suggested_Proper_Name_1': suggestions[0] if len(suggestions) > 0 else "",
                    'Suggested_Proper_Name_2': suggestions[1] if len(suggestions) > 1 else "",
                    'Suggested_Proper_Name_3': suggestions[2] if len(suggestions) > 2 else "",
                    'Final_Proper_Name': prior.get('Final_Proper_Name', ''),
                    'Alias_Scope': prior.get('Alias_Scope', 'Regional'),
                    'Rule_Type': prior.get('Rule_Type', 'Alias'),
                    # Informational only -- apply_corrections.py --final re-checks this
                    # itself before committing an Ignore rule, this just surfaces it
                    # here so you know which rows are even eligible for Ignore.
                    'Is_One_Off': 'Yes' if is_one_off(source_files_str, opponents_str) else 'No',
                    # Carried forward from gemini_alias_resolver.py output, if any.
                    'AI_Suggested_Name': prior.get('AI_Suggested_Name', ''),
                    'AI_Confidence': prior.get('AI_Confidence', ''),
                    'AI_Reasoning': prior.get('AI_Reasoning', ''),
                })
        correction_df = pd.DataFrame(correction_list)
        correction_df = correction_df[['Unrecognized_Alias', 'Newspaper_Region', 'Source_Files', 'Opponents_Played', 'Suggested_Proper_Name_1', 'Suggested_Proper_Name_2', 'Suggested_Proper_Name_3', 'Final_Proper_Name', 'Alias_Scope', 'Rule_Type', 'Is_One_Off', 'AI_Suggested_Name', 'AI_Confidence', 'AI_Reasoning']]
        correction_df = correction_df.sort_values(by=['Newspaper_Region', 'Unrecognized_Alias'])

        current_keys = {(r['Unrecognized_Alias'], r['Newspaper_Region']) for r in correction_list}
        carried = sum(
            1 for k, v in prior_annotations.items()
            if k in current_keys and (v['Final_Proper_Name'] or v['Rule_Type'].lower() == 'ignore')
        )

        if args.dry_run:
            preview_path = os.path.join(STAGING_DIRECTORY, 'New_Alias_Suggestions_DryRunPreview.csv')
            correction_df.to_csv(preview_path, index=False, encoding='utf-8-sig')
            logger.info(f"[DRY RUN] Would regenerate 'New_Alias_Suggestions.csv' with {len(correction_list)} unresolved rows "
                        f"({carried} with prior annotations that would carry forward). Preview written to {preview_path} "
                        f"instead of overwriting your real sheet.")
        else:
            correction_df.to_csv(correction_file_path, index=False, encoding='utf-8-sig')
            logger.info(f"'New_Alias_Suggestions.csv' regenerated ({len(correction_list)} unresolved rows, {carried} with prior annotations carried forward).")
            logger.info("Fill in Final_Proper_Name (or set Rule_Type=Ignore for genuine one-offs), then run 'apply_corrections.py' (add --final to commit Ignore rows).")
        return

    if not games_to_import:
        # Every parsed game was either Ignored or already filtered out -- nothing left to stage.
        logger.warning("No games left to import after removing Ignored games. Nothing written to RawScores_Staging.")
        return

    try:
        games_df = pd.DataFrame(games_to_import)
        df_to_insert = pd.DataFrame({
            'BatchID': games_df['BatchID'],
            'SourceFile': games_df['SourceFile'],
            'SourceRegion': games_df['SourceRegion'],
            'GameDate': games_df['GameDate'],
            'Season': games_df['Season'],
            'HomeTeamRaw': games_df['HomeTeamStd'],
            'VisitorTeamRaw': games_df['VisitorTeamStd'],
            'HomeScore': pd.to_numeric(games_df['HomeScore'], errors='coerce').fillna(0).astype(int),
            'VisitorScore': pd.to_numeric(games_df['VisitorScore'], errors='coerce').fillna(0).astype(int),
            'Overtime': pd.array(games_df['Overtime'], dtype=pd.Int64Dtype()),
            'quality_status': games_df['quality_status'],
            'processing_notes': games_df['processing_notes'],
            'LineNumber': games_df['LineNumber'],
            'RawLine': games_df['RawLine']
        })

        # NOTE: source_files drives which CSVs get moved to Completed by
        # batch_queue_manager.py (via add_to_batch_queue below). It must include
        # files whose ONLY games were Ignored (Rule_Type=Ignore), not just files
        # that contributed rows to games_to_import -- otherwise a file that's
        # 100% Ignored games never appears in any batch's source_files and sits
        # in Staged forever, even though there's nothing left to resolve for it.
        # (Files containing ONLY needs_review rows are deliberately NOT included
        # here -- those still need a human look, so they're left in Staged.)
        imported_files = set(games_df['SourceFile'].tolist())
        ignored_files = set(g['SourceFile'] for g in games_ignored)
        source_files = list(imported_files | ignored_files)

        if args.dry_run:
            logger.info(f"[DRY RUN] Would write {len(df_to_insert)} standardized record(s) to [RawScores_Staging] "
                        f"across {len(source_files)} source file(s) -- no DB write performed.")
            preview_cols = ['SourceFile', 'GameDate', 'Season', 'HomeTeamRaw', 'VisitorTeamRaw', 'HomeScore', 'VisitorScore']
            print("\n" + "=" * 80)
            print("🔍 DRY RUN PREVIEW -- nothing written to the database")
            print("=" * 80)
            print(f"Would insert: {len(df_to_insert)} games")
            print(f"Source files: {len(source_files)}")
            print(f"Ignored (skipped) games this run: {len(games_ignored)}")
            print(f"\nFirst {min(10, len(df_to_insert))} row(s) that would be inserted:")
            print(df_to_insert[preview_cols].head(10).to_string(index=False))
            print("\nRe-run without --dry-run to actually write this batch.")
            print("=" * 80 + "\n")
            return

        logger.info(f"Writing {len(df_to_insert)} standardized records to staging table [RawScores_Staging]...")
        df_to_insert.to_sql('RawScores_Staging', con=engine, if_exists='append', index=False)

        # Add batch to queue
        add_to_batch_queue(batch_id, len(source_files), len(df_to_insert), source_files)

        logger.info("🎉 Stage 1 Ingestion Complete! 🎉")
        logger.info(f"Batch loaded into RawScores_Staging with BatchID: {batch_id}")
        logger.info(f"✅ Batch added to processing queue - you can continue loading more batches")

        print("\n" + "="*80)
        print("✅ BATCH QUEUED FOR PROCESSING")
        print("="*80)
        print(f"BatchID: {batch_id}")
        print(f"Games: {len(df_to_insert)}")
        print(f"Files: {len(source_files)}")
        print("\nThis batch is now in the queue. You can:")
        print("1. Continue running this script to add more batches")
        print("2. Run 'python batch_queue_manager.py' to view queue status")
        print("3. Process all queued batches when your rating calc is complete")
        print("="*80 + "\n")

    except Exception as e:
        logger.exception("FATAL: An error occurred during database load to staging table.")
    
# === SCRIPT ENTRY POINT ===
if __name__ == "__main__":
    main()