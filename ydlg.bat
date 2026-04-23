@echo off
REM Launches the YouTube Downloader GUI without a lingering console window.
REM Uses pythonw.exe so no black cmd window stays behind the app.
cd /d "%~dp0"
start "" "C:\Users\Yoon\AppData\Local\Microsoft\WindowsApps\pythonw3.12.exe" -m src.gui
