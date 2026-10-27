# PowerShell Packaging Script for Setu
# Produces a clean ZIP without node_modules, venvs, database files, .env, test-results, previous ZIPs, or .git.

$ErrorActionPreference = "Stop"
$rootDir = (Get-Item $PSScriptRoot).Parent.FullName
$zipPath = Join-Path $rootDir "Setu_Submission.zip"

Write-Host "Creating clean submission ZIP at: $zipPath"

# Remove existing ZIP if present
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

# Temporary staging directory
$stageDir = Join-Path $rootDir "scratch\package_staging\Setu"
if (Test-Path $stageDir) {
    Remove-Item -Recurse -Force $stageDir
}
New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

# List of regex exclusion patterns
$excludePatterns = @(
    "(^|[\\/])\.git([\\/]|$)",
    "(^|[\\/])\.pytest_cache([\\/]|$)",
    "(^|[\\/])node_modules([\\/]|$)",
    "(^|[\\/])dist([\\/]|$)",
    "(^|[\\/])test-results([\\/]|$)",
    "(^|[\\/])playwright-report([\\/]|$)",
    "(^|[\\/])scratch([\\/]|$)",
    "(^|[\\/])\.venv([\\/]|$)",
    "(^|[\\/])venv([\\/]|$)",
    "\.db$",
    "\.sqlite$",
    "\.sqlite3$",
    "(^|[\\/])\.env",
    "\.zip$",
    "__pycache__"
)

# Enumerate and copy matching files
$allFiles = Get-ChildItem -Path $rootDir -Recurse -File
$includedFiles = @()

foreach ($file in $allFiles) {
    $relPath = $file.FullName.Substring($rootDir.Length).TrimStart('\', '/')
    
    $skip = $false
    foreach ($pattern in $excludePatterns) {
        if ($relPath -match $pattern) {
            $skip = $true
            break
        }
    }
    
    if (-not $skip) {
        $destPath = Join-Path $stageDir $relPath
        $destParent = Split-Path -Parent $destPath
        if (-not (Test-Path $destParent)) {
            New-Item -ItemType Directory -Path $destParent -Force | Out-Null
        }
        Copy-Item -Path $file.FullName -Destination $destPath -Force
        $includedFiles += $relPath
    }
}

# Create ZIP
Compress-Archive -Path "$stageDir\*" -DestinationPath $zipPath -CompressionLevel Optimal

# Clean up staging
Remove-Item -Recurse -Force (Join-Path $rootDir "scratch\package_staging")

Write-Host "`n=== CLEAN PACKAGING COMPLETE ==="
Write-Host "Total files packaged: $($includedFiles.Count)"
Write-Host "ZIP Location: $zipPath"
Write-Host "ZIP Size: $((Get-Item $zipPath).Length / 1KB) KB"

Write-Host "`nPackaged Files Summary:"
$includedFiles | Sort-Object | ForEach-Object { Write-Host "  $_" }
