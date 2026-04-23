# ydl.ps1 — Quick-download helper.
# Usage:
#   .\ydl.ps1                       # downloads URL from clipboard with defaults (128k m4a)
#   .\ydl.ps1 "<url>"               # downloads given URL
#   .\ydl.ps1 "<url>" --quality 320 --format mp3
#
# Tip: add this folder to your PATH, then just run `ydl` from anywhere.
#      Or pin the .bat shim to taskbar / make a desktop shortcut for one-click downloads.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:/Users/Yoon/AppData/Local/Microsoft/WindowsApps/python3.12.exe"

# If first arg looks like a flag (or no args), pull URL from clipboard.
if ($args.Count -eq 0 -or $args[0].StartsWith("--")) {
    # Pass through directly (no clipboard) for help and batch mode.
    if ($args -contains "--help" -or $args -contains "-h" -or $args -contains "--batch") {
        Push-Location $scriptDir
        try { & $python -m src.cli @args; $exit = $LASTEXITCODE } finally { Pop-Location }
        exit $exit
    }
    $url = (Get-Clipboard -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($url)) {
        Write-Host "ERROR: No URL given and clipboard is empty." -ForegroundColor Red
        exit 1
    }
    if ($url -notmatch "^https?://") {
        Write-Host "ERROR: Clipboard does not contain a URL: $url" -ForegroundColor Red
        exit 1
    }
    Write-Host "Using clipboard URL: $url" -ForegroundColor Cyan
    $passthrough = @($args)
} else {
    $url = $args[0]
    if ($args.Count -gt 1) {
        $passthrough = @($args[1..($args.Count - 1)])
    } else {
        $passthrough = @()
    }
}

Push-Location $scriptDir
try {
    & $python -m src.cli $url @passthrough
    $exit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $exit
