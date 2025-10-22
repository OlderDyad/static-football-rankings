@echo off
ECHO Starting MaxPreps Scraper...
CD /D "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import"
CALL "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\.venv\Scripts\activate.bat"
python maxpreps_scraper_db.py
ECHO Scraper finished. Exit code: %ERRORLEVEL%
REM PAUSE