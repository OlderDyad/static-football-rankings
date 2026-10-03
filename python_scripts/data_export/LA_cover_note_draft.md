Hi Loren,

Louisiana is ready — first full-state delivery (you've had a couple of partial LA files before this; this replaces those with the complete history). Three files in the Louisiana folder:

- **LA-Scores-Full.csv** — every game on record, 1904–2025 (102,661 games)
- **LA-Team-Names.csv** — team metadata (city, mascot, colors, etc.) for 1,089 programs
- **LA-Investigation-Queue.csv** — every data-quality question we've flagged and worked through, in case your team wants to dig into anything (2,314 investigations total — 1,834 still open, the rest already reviewed and closed out)

Quick guide to the queue file:

**Status** — `New` means still open, worth a look. Anything else (`Fixed`, `Verified-FalsePos`, `Verified`, `Dismissed`) means we already reviewed and closed it out — the Notes column says how.

**ConflictType** — what kind of issue got flagged:
- *GhostTeam* — a team appears to play two different games on/near the same date. Usually a big program's freshman/JV/varsity doubleheader, or — this turned out to be common in Louisiana specifically — a real historical "jamboree" event, where one team plays short scrimmage quarters against 2–3 different opponents in one evening (mostly late August, big schools). Occasionally it's a real name-mapping error.
- *TierMismatch* — a game against an opponent that looks out of place for its level (a college frosh/JV team, or a suspiciously close score against a weak/deaf-school opponent).
- *AliasReclassification* — a team name that might actually be a misspelled or garbled version of another team's name.

One known gap worth knowing about: about 2,300 of the 102,661 score rows (under 2.5%) don't have a matched team ID in the names file — mostly older or smaller programs not yet in our team registry. Doesn't affect the game data itself, just that one join.

Happy to walk through any of it or pull more detail on specific cases whenever useful.

[Your name]
