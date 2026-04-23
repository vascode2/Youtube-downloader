@echo off
REM ydl.bat — shim so `ydl <url>` works from cmd.exe and PowerShell.
REM Forwards everything to _ydl.ps1 (underscore prefix prevents PowerShell from
REM resolving `ydl` directly to the .ps1, which would hit ExecutionPolicy block).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_ydl.ps1" %*
