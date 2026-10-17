# One-time setup for video-studio on Windows.
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
# Installs the pinned HyperFrames CLI and puppeteer-core (npm), makes sure HyperFrames has its headless Chrome,
# and puts an ffmpeg build with libx264 in tools\ (BtbN FFmpeg-Builds, GitHub release, checksum verified).
# The local speech engines (Kokoro on :8880, Whisper/speaches on :2022) are not installed here; any
# OpenAI-compatible pair works (Talkover's docker-compose.yml starts both).
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
Set-Location $Root
foreach ($t in 'node', 'npm', 'python') {
    if (-not (Get-Command $t -ErrorAction SilentlyContinue)) { throw "$t not found (winget install OpenJS.NodeJS.LTS / Python.Python.3.13)" }
}
Write-Host '==> npm packages' -ForegroundColor Cyan
npm install --no-audit --no-fund
$env:HYPERFRAMES_SKIP_SKILLS = '1'
npx hyperframes telemetry disable | Out-Null
npx hyperframes browser ensure

$have = Get-ChildItem (Join-Path $Root 'tools') -Directory -Filter 'ffmpeg-*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $have) {
    Write-Host '==> ffmpeg with libx264 (BtbN FFmpeg-Builds)' -ForegroundColor Cyan
    $asset = 'ffmpeg-n8.1-latest-win64-gpl-8.1.zip'
    $base = 'https://github.com/BtbN/FFmpeg-Builds/releases/latest/download'
    $dl = Join-Path $Root 'tools\dl'
    New-Item -ItemType Directory -Force $dl | Out-Null
    Invoke-WebRequest "$base/$asset" -OutFile (Join-Path $dl $asset)
    Invoke-WebRequest "$base/checksums.sha256" -OutFile (Join-Path $dl 'checksums.sha256')
    $want = ((Get-Content (Join-Path $dl 'checksums.sha256')) | Where-Object { $_ -match [regex]::Escape($asset) }) -split '\s+' | Select-Object -First 1
    $got = (Get-FileHash (Join-Path $dl $asset) -Algorithm SHA256).Hash.ToLower()
    if ($want -ne $got) { throw "checksum mismatch for $asset" }
    Expand-Archive (Join-Path $dl $asset) -DestinationPath (Join-Path $Root 'tools') -Force
}
Write-Host '==> health' -ForegroundColor Cyan
python -m studio health
