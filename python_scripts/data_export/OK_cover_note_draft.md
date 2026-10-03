Hi Loren,

Oklahoma is ready. Three files in the Oklahoma folder:

- **OK-Scores-Full.csv** — every game on record, 1906–2025 (124,497 games)
- **OK-Team-Names.csv** — team metadata (city, mascot, colors, etc.) for 797 programs
- **OK-Investigation-Queue.csv** — every data-quality question we've flagged and worked through, in case your team wants to dig into anything (2,601 investigations total — 1,709 still open, the rest already reviewed and closed out)

Quick guide to the queue file:

**Status** — `New` means still open, worth a look. Anything else (`Fixed`, `Verified-FalsePos`, `Verified-Resolved`, `Spot-Checked`) means we already reviewed and closed it out — the Notes column says how.

**ConflictType** — what kind of issue got flagged:
- *GhostTeam* — a team appears to play two different games on/near the same date. Usually just a big program's freshman/JV/varsity doubleheader; occasionally a real name-mapping error.
- *AliasReclassification* — a team name that might actually be a misspelled or garbled version of another team's name.
- *TierMismatch* — a game against an opponent that looks out of place for its level (a college frosh/JV team, or a suspiciously close score against a weak/deaf-school opponent).
- *LevelMismatch* — an 8-man team apparently playing an 11-man team — usually a mapping gap, not a real crossover game.

One known gap worth knowing about: about 1,850 of the 124,497 score rows (under 2%) don't have a matched team ID in the names file — mostly older or smaller programs not yet in our team registry. Doesn't affect the game data itself, just that one join.

Happy to walk through any of it or pull more detail on specific cases whenever useful.

[Your name]
