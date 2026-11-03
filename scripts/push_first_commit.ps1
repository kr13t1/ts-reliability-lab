# Run from the root of the extracted ts-reliability-lab directory.
# First create an EMPTY private repository named ts-reliability-lab on GitHub.
param([string]$Repo = "https://github.com/kr13t1/ts-reliability-lab.git")
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed. Install Git for Windows (https://git-scm.com/downloads/win)."
}
if (-not (Test-Path "./.git")) {
    git init -b main
    if ($LASTEXITCODE -ne 0) { throw "git init failed" }
}
$author = git config user.name
$email = git config user.email
if (-not $author -or -not $email) {
    throw "Configure your Git identity first: git config --global user.name 'Your Name'; git config --global user.email 'your-public-github-noreply-address'"
}
git add .
if ($LASTEXITCODE -ne 0) { throw "git add failed" }
$staged = git diff --cached --name-only
if ($staged) {
    git commit -m "chore: initialize audited reliability lab"
    if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
}
$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0 -or -not $existing) {
    git remote add origin $Repo
} elseif ($existing -ne $Repo) {
    throw "Existing origin is $existing, expected $Repo. Resolve manually; not overwriting."
}
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw "git push failed. Ensure GitHub repo exists and local Git authentication works." }
Write-Host "SUCCESS: $Repo"
