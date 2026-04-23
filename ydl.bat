@echo off
REM ydl.bat — shim so `ydl <url>` works from cmd.exe and File Explorer shortcuts.
REM Forwards everything to ydl.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ydl.ps1" %*
