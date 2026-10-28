# wiki_season_batch.ps1 -- fetch Wikipedia season pages (by category) for the gap schools.
# Changes nothing in the database. Pages are cached in schedules\cache, so a rerun only fetches what is new.
# Run from python_scripts\college:   .\wiki_season_batch.ps1
$jobs = @(
  @("Slippery Rock",      "Slippery Rock The Rock football seasons"),
  @("California PA",      "California Vulcans football seasons"),
  @("Mansfield",          "Mansfield Mounties football seasons"),
  @("Lock Haven",         "Lock Haven Bald Eagles football seasons"),
  @("Edinboro",           "Edinboro Fighting Scots football seasons"),
  @("Clarion",            "Clarion Golden Eagles football seasons"),
  @("Upper Iowa",         "Upper Iowa Peacocks football seasons"),
  @("Luther",             "Luther Norse football seasons"),
  @("Wartburg",           "Wartburg Knights football seasons"),
  @("Buena Vista",        "Buena Vista Beavers football seasons"),
  @("Simpson",            "Simpson Storm football seasons"),
  @("Central IA",         "Central Dutch football seasons"),
  @("Coe",                "Coe Kohawks football seasons"),
  @("Dubuque",            "Dubuque Spartans football seasons"),
  @("Iowa Wesleyan",      "Iowa Wesleyan Tigers football seasons"),
  @("William Penn",       "William Penn Statesmen football seasons"),
  @("Nebraska-Kearney",   "Nebraska–Kearney Lopers football seasons"),
  @("Chadron St",         "Chadron State Eagles football seasons"),
  @("Peru St",            "Peru State Bobcats football seasons"),
  @("Doane",              "Doane Tigers football seasons"),
  @("Hastings",           "Hastings Broncos football seasons"),
  @("Midland",            "Midland Warriors football seasons"),
  @("Nebraska Wesleyan",  "Nebraska Wesleyan Prairie Wolves football seasons"),
  @("Wayne St NE",        "Wayne State Wildcats football seasons")
)
foreach ($j in $jobs) {
  Write-Host "=== $($j[0])"
  python fetch_season_schedules.py --team $j[0] --years 1880-1999 --category $j[1]
}
