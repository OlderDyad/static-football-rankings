# wiki_conference_batch.ps1 -- fetch Wikipedia CONFERENCE season pages ("1961 Pennsylvania State College
# Conference football season"): every team's schedule on one page. Changes nothing in the database.
# Years without a page are just listed as "No page found". Pages are cached in schedules\cache.
# Run from python_scripts\college:   .\wiki_conference_batch.ps1
$jobs = @(
  @("{year} Pennsylvania State Teachers College Conference football season", "1925-1960"),
  @("{year} Pennsylvania State College Conference football season",          "1958-1965"),
  @("{year} Pennsylvania State Athletic Conference football season",         "1960-1999"),
  @("{year} Iowa Conference football season",                                "1922-1960"),
  @("{year} Iowa Intercollegiate Athletic Conference football season",       "1925-1999"),
  @("{year} Nebraska College Conference football season",                    "1926-1975"),
  @("{year} Nebraska Intercollegiate Athletic Conference football season",   "1920-1999"),
  @("{year} Oklahoma Collegiate Conference football season",                 "1929-1974"),
  @("{year} Central Intercollegiate Athletic Association football season",   "1912-1960"),
  @("{year} North Central Conference football season",                       "1922-1980"),
  @("{year} Northern Teachers Athletic Conference football season",          "1932-1960"),
  @("{year} Evergreen Conference football season",                           "1948-1984"),
  @("{year} Rocky Mountain Conference football season",                      "1909-1967")
)
foreach ($j in $jobs) {
  Write-Host "=== $($j[0])"
  python fetch_season_schedules.py --conference $j[0] --years $j[1]
}
