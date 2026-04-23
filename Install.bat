@echo off
REM Install.bat — bypass execution policy and run Install.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1" %*
