Param(
    [Parameter(Mandatory=$true)]
    [string]$RepoUrl,
    [switch]$Push
)

# Usage:
#   .\clean_with_bfg.ps1 -RepoUrl "git@github.com:owner/repo.git"
#   .\clean_with_bfg.ps1 -RepoUrl "https://github.com/owner/repo.git" -Push

$ErrorActionPreference = 'Stop'
$mirror = "repo-mirror.git"
$bfgJar = "bfg.jar"
$bfgUrl = "https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar"

if (Test-Path $mirror) {
    Write-Error "Mirror folder '$mirror' already exists. Remove it first or choose a different working directory."; exit 1
}

Write-Output "Cloning bare mirror from $RepoUrl..."
git clone --mirror $RepoUrl $mirror

Set-Location $mirror

if (-not (Test-Path $bfgJar)) {
    Write-Output "Downloading BFG (bfg.jar)..."
    Invoke-WebRequest -Uri $bfgUrl -OutFile $bfgJar
}

Write-Output "Running BFG to delete .env and next_proxy/.env.local from history..."
# Delete files entirely from history
java -jar $bfgJar --delete-files .env --delete-files next_proxy/.env.local

Write-Output "Expiring reflog and garbage collecting..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

Write-Output "Created cleaned mirror at: $(Get-Location)"

if ($Push) {
    Write-Output "Pushing cleaned history to origin (FORCE PUSH)..."
    git push --force --all
    git push --force --tags
    Write-Output "Push complete. Notify collaborators to re-clone the repository." 
} else {
    Write-Output "Push not performed. Inspect the cleaned mirror locally before pushing."
    Write-Output "To push when ready: cd $mirror ; git push --force --all ; git push --force --tags"
}

Write-Output "Done. IMPORTANT: Rotate any exposed API keys/sessions immediately and inform collaborators to re-clone after force-push."