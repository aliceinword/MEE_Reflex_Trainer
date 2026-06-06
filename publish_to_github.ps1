# Publishes code-only changes from this folder to the public GitHub repo.
# It copies ONLY source files (never PDFs, databases, or personal data)
# into the clean repo folder, commits, and pushes.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File publish_to_github.ps1 "your commit message"
# or just double-click publish_to_github.bat

param(
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

$src = "C:\Users\olesi\OneDrive\MEE_Reflex_Trainer"
$dst = "C:\Users\olesi\OneDrive\MEE_Reflex_Trainer_public"
$gh  = "C:\Program Files\GitHub CLI\gh.exe"

# Source code files that are safe to publish. Add new code files here.
$codeFiles = @(
    "app.py",
    "database.py",
    "text_cleanup.py",
    "import_attack_outline.py",
    "import_plug_play_templates.py",
    "import_studicata_bank.py",
    "import_master_rules.py",
    "import_questions_bank.py",
    "import_questions_docx.py",
    "import_plug_play_docx.py",
    "import_condensed_sample_answers.py",
    "import_flashcards2025.py",
    "populate_traps.py",
    "audit_sample_answers.py",
    "reset_studicata_import.py",
    "make_user.py",
    "mbe_trap_trainer.html",
    "requirements.txt",
    "run_app.bat",
    ".streamlit\config.toml",
    ".streamlit\secrets.toml.example"
)

if (-not (Test-Path $dst)) {
    Write-Host "Public repo folder not found: $dst" -ForegroundColor Red
    exit 1
}

Write-Host "Copying code files..." -ForegroundColor Cyan
foreach ($f in $codeFiles) {
    $from = Join-Path $src $f
    $to   = Join-Path $dst $f
    if (Test-Path $from) {
        $toDir = Split-Path $to -Parent
        if (-not (Test-Path $toDir)) { New-Item -ItemType Directory -Path $toDir -Force | Out-Null }
        Copy-Item $from $to -Force
        Write-Host "  $f"
    } else {
        Write-Host "  (skipped, missing) $f" -ForegroundColor Yellow
    }
}

Set-Location $dst

# Safety net: refuse to push if any copyrighted/data file ever got staged.
git add -A
$bad = git status --porcelain | Select-String -Pattern '\.(pdf|db|sqlite|sqlite3|csv)(\s|$)'
if ($bad) {
    Write-Host "ABORTING: data/copyrighted files detected in the publish folder:" -ForegroundColor Red
    $bad | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host "Remove them from $dst before publishing." -ForegroundColor Red
    exit 1
}

$changes = git status --porcelain
if (-not $changes) {
    Write-Host "Nothing to publish - the repo is already up to date." -ForegroundColor Green
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    $Message = "Update app code ($stamp)"
}

Write-Host "Committing and pushing..." -ForegroundColor Cyan
git -c core.autocrlf=true commit -q -m $Message
git push origin main

Write-Host ""
Write-Host "Published to https://github.com/aliceinword/MEE_Reflex_Trainer" -ForegroundColor Green
