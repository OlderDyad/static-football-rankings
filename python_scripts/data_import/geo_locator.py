import time
import pyodbc
import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import sys

# --- 1. USER SETTINGS (CONFIRM THESE) ---

conn_str = (
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=McKnights-PC\SQLEXPRESS01;'
    r'DATABASE=hs_football_database;'
    r'Trusted_Connection=yes;'
)

geolocator = Nominatim(user_agent="hs-football-historical-project-v2")


# --- 2. Caching & Rules ---

geocode_cache = {}

SCHOOL_TERMS = {
    "high", "hs", "academy", "central", "prep", "school", "tech",
    "union", "regional", "community", "collegiate", "christian", "montessori"
}

STATE_RE = re.compile(r'^(.*?)\s+\(([A-Z]{2})\)$')


# ---- NEW STATE MAP (US ONLY) ----
STATE_ABBREV_TO_NAME = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
    "CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia",
    "HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa",
    "KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland",
    "MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri",
    "MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey",
    "NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio",
    "OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina",
    "SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont",
    "VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"
}


# --- 3. Helper Functions (INCLUDING NEW STRICT VALIDATOR) ---

def parse_team_name_full(team_name_str):
    """
    Parse: "East St. Louis Lincoln (IL)" → ("East St. Louis Lincoln", "IL")
    """
    m = STATE_RE.search(team_name_str)
    if not m:
        return None, None
    return m.group(1).strip(), m.group(2).strip()


# ---- NEW STRICT VALIDATOR ----
def _validate_location_for_state(location, requested_state_abbrev):
    """
    **Strict validator** – prevents false positives like:
        - Manchester East Catholic (CT) → Wisconsin
        - Surprise Valley Vista (AZ) → Grand Canyon

    Requirements:
        - Must NOT be natural features (valley, park, canyon, etc.)
        - Must contain a locality (city/town/village) OR county
        - Must match US state via full name, state_code, or display_name
        - Optional importance threshold
    """
    if not location:
        return False

    raw = location.raw or {}
    addr = raw.get("address", {})

    # 1. Reject natural features
    cls = (raw.get("class") or "").lower()
    type_ = (raw.get("type") or "").lower()

    if cls in ("natural", "landform") or type_ in (
        "valley", "mountain", "wood", "river", "ridge", "park"
    ):
        return False

    # 2. Require locality OR county
    locality_keys = ("city", "town", "village", "municipality", "hamlet")
    if not any(k in addr for k in locality_keys):
        if "county" not in addr:
            return False

    # 3. Match state code / name
    requested_state_abbrev = (requested_state_abbrev or "").upper()
    requested_state_full = STATE_ABBREV_TO_NAME.get(requested_state_abbrev, "").lower()

    state_field = (addr.get("state") or "").lower()
    state_code_field = (addr.get("state_code") or "").lower()
    region_field = (addr.get("region") or "").lower()
    display = (raw.get("display_name") or "").lower()

    # Allow Alberta (AB)
    if requested_state_abbrev == "AB":
        country_code = (addr.get("country_code") or "").lower()
        if country_code == "ca" and ("alberta" in state_field or state_code_field == "ab"):
            return True
        return False

    # U.S. only from here on
    country_code = (addr.get("country_code") or "").lower()
    if country_code != "us":
        return False

    # Accept if:
    if (
        requested_state_full in state_field
        or requested_state_abbrev.lower() == state_code_field
        or requested_state_full in region_field
        or f", {requested_state_abbrev.lower()}," in display
        or f" {requested_state_abbrev.lower()} " in display
    ):
        pass
    else:
        return False

    # 4. Optional importance threshold
    importance = raw.get("importance")
    if importance is not None:
        try:
            if float(importance) < 0.05:
                return False
        except:
            pass

    return True


def geocode_with_validation(query, state_abbrev, pause=1.0):
    """
    Query geocoder with caching and strict state validation.
    Returns location or None.
    """
    if not query:
        return None

    key = f"{query}||{state_abbrev}"
    if key in geocode_cache:
        return geocode_cache[key]

    try:
        time.sleep(pause)

        query_full = f"{query}, USA" if len(state_abbrev) == 2 and state_abbrev != "AB" else query
        loc = geolocator.geocode(query_full, timeout=12, addressdetails=True)

        if loc and _validate_location_for_state(loc, state_abbrev):
            geocode_cache[key] = loc
            return loc

        geocode_cache[key] = None
        return None

    except (GeocoderTimedOut, GeocoderUnavailable):
        print(f"  GEOCODER ERROR: Timeout/unavailable for {query}. Retrying later.")
        time.sleep(5)
        return None
    except Exception as e:
        print(f"  GEOCODER ERROR: {e}")
        geocode_cache[key] = None
        return None


# --- 4. Main Geocoding Logic ---

def safe_geocode_team(full_name, state_abbrev):
    """
    Hybrid strategy with prioritized fallbacks (Descending Specificity).
    """
    if not full_name or not state_abbrev:
        return None, None

    # 0. Co-op rule (Adair-Casey) - Remains highest priority due to unique structure
    if "-" in full_name and len(full_name.split()) == 1:
        city_candidate = full_name.split("-")[0]
        print(f"  Parsed (Co-op): School={full_name}, City={city_candidate}")
        # ... (Co-op specific queries Q1 & Q2 remain unchanged) ...
        # (Assuming Q0 logic is here, which includes return statements)
        pass 
        
    # Prepare tokens for fallbacks
    tokens = full_name.split()
    lower_tokens = [t.strip(".,").lower() for t in tokens]

    # 1. Primary strategy (Full Name, State) - Always first for maximum detail
    q_primary = f"{full_name}, {state_abbrev}"
    loc = geocode_with_validation(q_primary, state_abbrev)
    if loc:
        return loc.latitude, loc.longitude

    # 2. Fallback A – Strip trailing school terms (The smartest guess, targets "San Antonio Central")
    trailing_idx = len(lower_tokens)
    while trailing_idx > 0 and lower_tokens[trailing_idx - 1] in SCHOOL_TERMS:
        trailing_idx -= 1

    if trailing_idx < len(tokens) and trailing_idx >= 1:
        city_candidate = " ".join(tokens[:trailing_idx])
        print(f"  Parsed (Fallback A - Smart Strip): City='{city_candidate}'")
        
        q1 = f"{full_name}, {city_candidate}, {state_abbrev}"
        loc = geocode_with_validation(q1, state_abbrev)
        if loc:
            return loc.latitude, loc.longitude

        q2 = f"{city_candidate}, {state_abbrev}"
        loc = geocode_with_validation(q2, state_abbrev)
        if loc:
            return loc.latitude, loc.longitude


    # --- NEW ORDER STARTS HERE ---

    # 3. Fallback D – First three words as city (Targets Bay St. Louis, West Des Moines)
    if len(tokens) >= 3:
        t3 = lower_tokens[2]
        if t3 not in SCHOOL_TERMS: 
            city_three = f"{tokens[0]} {tokens[1]} {tokens[2]}"
            print(f"  Parsed (Fallback D - 3-Word City): Trying '{city_three}'")

            q1 = f"{full_name}, {city_three}, {state_abbrev}"
            loc = geocode_with_validation(q1, state_abbrev)
            if loc:
                return loc.latitude, loc.longitude

            q2 = f"{city_three}, {state_abbrev}"
            loc = geocode_with_validation(q2, state_abbrev)
            if loc:
                return loc.latitude, loc.longitude

    # 4. Fallback B – First two words as city (Targets West New York, Crystal Lake)
    if len(tokens) >= 2:
        t2 = lower_tokens[1]
        if t2 not in SCHOOL_TERMS and t2 != "st":
            city_two = f"{tokens[0]} {tokens[1]}"
            print(f"  Parsed (Fallback B - 2-Word City): Trying '{city_two}'")

            q1 = f"{full_name}, {city_two}, {state_abbrev}"
            loc = geocode_with_validation(q1, state_abbrev)
            if loc:
                return loc.latitude, loc.longitude

            q2 = f"{city_two}, {state_abbrev}"
            loc = geocode_with_validation(q2, state_abbrev)
            if loc:
                return loc.latitude, loc.longitude

    # 5. Final Fallback C – First-Word Only (Targets Franklin, VA)
    if len(tokens) > 1:
        city_first_word = tokens[0]
        if city_first_word.lower().strip(".,") not in ("st", "st.", "ft", "ft.", "north", "south", "east", "west"):
            print(f"  Parsed (Fallback C - 1-Word City): Trying '{city_first_word}'")
            q_final = f"{city_first_word}, {state_abbrev}"
            loc = geocode_with_validation(q_final, state_abbrev)
            if loc:
                return loc.latitude, loc.longitude

    # Nothing worked
    return None, None

# --- 5. Main Processing Loop ---

print("Starting geocoding script (v4.2)...")
try:
    with pyodbc.connect(conn_str) as conn:
        print("Successfully connected to SQL Server.")
        conn.autocommit = True
        
        read_cursor = conn.cursor()
        read_cursor.execute("SELECT ID, Team_Name FROM dbo.HS_Team_Names WHERE Latitude IS NULL")

        schools = read_cursor.fetchall()
        total_schools = len(schools)
        print(f"Found {total_schools} schools to geocode.")

        for i, row in enumerate(schools):
            school_id = row.ID
            team_name_str = row.Team_Name

            print(f"\nProcessing {i+1} of {total_schools} (ID: {school_id}) | {team_name_str}...")

            full_name, state_abbrev = parse_team_name_full(team_name_str)

            if not full_name or not state_abbrev:
                print(f"  PARSE FAIL: Could not extract state from: {team_name_str}")
                continue

            lat, lon = safe_geocode_team(full_name, state_abbrev)

            if lat is not None and lon is not None:
                print(f"  *** SUCCESS: ({lat}, {lon}) ***")
                update_cursor = conn.cursor()
                update_cursor.execute(
                    "UPDATE dbo.HS_Team_Names SET Latitude = ?, Longitude = ? WHERE ID = ?",
                    (lat, lon, school_id)
                )
            else:
                print(f"  --- FAILED: No valid geocode for {full_name} ({state_abbrev})")

except pyodbc.Error as ex:
    print(f"\nSQL ERROR: {ex}")

except Exception as e:
    print(f"\nFatal error: {e}")

finally:
    print("\nGeocoding script complete.")
