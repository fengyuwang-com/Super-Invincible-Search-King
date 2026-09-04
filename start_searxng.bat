@echo off
rem SearXNG standalone launcher (optional - scraper.py uses in-process by default).
rem Requires: SearXNG source at %USERPROFILE%\searxng-src or sibling dir.
chcp 65001 >nul
set SEARXNG_SETTINGS_PATH=%~dp0searxng\settings-win.yml
echo Starting SearXNG on http://127.0.0.1:8899
echo Close this window to stop.
python -m searx.webapp
