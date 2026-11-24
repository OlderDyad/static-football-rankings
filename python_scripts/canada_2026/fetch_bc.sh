#!/bin/bash
# Fetch full 2026 BC schedules (AAA, AA/AAA hybrid, JV). The site needs a browser user-agent
# and a session cookie set by clear.cfm before each league's schedule page.
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
B="https://www.bchighschoolfootball.com/leagues"
rm -f bc_jar
for L in 6713 6714 22265; do
  curl -sL -m 60 -c bc_jar -b bc_jar -A "$UA" "$B/clear.cfm?clientid=652&leagueid=$L" -o /dev/null
  curl -sL -m 60 -c bc_jar -b bc_jar -A "$UA" -o "bc_2026_$L.html" -w "$L %{http_code} %{size_download}\n" \
    "$B/schedules.cfm?clientID=652&leagueID=$L&schedType=main&printPage=0&monthID=0&yearID=2026&selectedTeamID=0&selectedOfficialID=0&gameType=&hideHA="
done
