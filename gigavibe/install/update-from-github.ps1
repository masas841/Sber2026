param(
    [string]$RepoArchiveUrl = "",
    [string]$Subdir = "gigavibe",
    [switch]$DryRun,
    [switch]$KeepTemp
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

function Read-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name
    )

    if (-not (Test-Path $Path)) { return $null }
    $pattern = "^\s*$([regex]::Escape($Name))\s*=\s*(.*)\s*$"
    foreach ($line in Get-Content -Path $Path) {
        if ($line -match "^\s*#") { continue }
        if ($line -match $pattern) {
            return $matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Invoke-RobocopySafe {
    param(
        [string]$Source,
        [string]$Destination,
        [string[]]$ExcludeDirs,
        [string[]]$ExcludeFiles
    )

    $args = @(
        $Source,
        $Destination,
        "/E",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NC",
        "/NS",
        "/NP"
    )
    if ($ExcludeDirs.Count -gt 0) {
        $args += "/XD"
        $args += $ExcludeDirs
    }
    if ($ExcludeFiles.Count -gt 0) {
        $args += "/XF"
        $args += $ExcludeFiles
    }

    & robocopy @args | Out-Null
    $code = $LASTEXITCODE
    if ($code -ge 8) {
        throw "robocopy failed with exit code $code"
    }
}

$envPath = Join-Path $Root ".env"
if (-not $RepoArchiveUrl) {
    $RepoArchiveUrl = Read-DotEnvValue -Path $envPath -Name "UPDATE_REPO_ARCHIVE_URL"
}
if (-not $RepoArchiveUrl) {
    $RepoArchiveUrl = "https://github.com/masas841/Sber2026/archive/refs/heads/main.zip"
}
$githubToken = Read-DotEnvValue -Path $envPath -Name "UPDATE_GITHUB_TOKEN"
if (-not $githubToken) { $githubToken = $env:UPDATE_GITHUB_TOKEN }
if (-not $githubToken) { $githubToken = $env:GITHUB_TOKEN }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tempRoot = Join-Path $env:TEMP "gigavibe-update-$stamp"
$zipPath = Join-Path $tempRoot "repo.zip"
$extractPath = Join-Path $tempRoot "repo"

Write-Host "[GIGAvibe] Update source: $RepoArchiveUrl" -ForegroundColor Cyan
Write-Host "[GIGAvibe] Install root: $Root"

try {
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $headers = @{
        "User-Agent" = "GIGAvibe-Updater"
    }
    if ($githubToken) {
        $headers["Authorization"] = "Bearer $githubToken"
        Write-Host "[GIGAvibe] GitHub token configured." -ForegroundColor DarkGray
    }
    $requestArgs = @{
        Uri = $RepoArchiveUrl
        OutFile = $zipPath
        UseBasicParsing = $true
        Headers = $headers
    }
    try {
        Invoke-WebRequest @requestArgs
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 404 -and -not $githubToken) {
            Write-Host "[GIGAvibe] GitHub archive is not available anonymously." -ForegroundColor Yellow
            Write-Host "[GIGAvibe] If the repo is private, set UPDATE_GITHUB_TOKEN in .env." -ForegroundColor Yellow
        }
        throw
    }
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

    $sourceRoot = Get-ChildItem -Path $extractPath -Directory |
        ForEach-Object { Join-Path $_.FullName $Subdir } |
        Where-Object { Test-Path $_ } |
        Select-Object -First 1

    if (-not $sourceRoot) {
        throw "Subdir '$Subdir' was not found in downloaded archive"
    }

    $excludeDirs = @(
        ".git",
        ".venv",
        ".venv-liveportrait",
        ".aigo123",
        "runtime",
        "models",
        "vendor",
        "tools",
        "gfpgan",
        "dist",
        "backups",
        "certs",
        "wheels",
        "__pycache__",
        "outputs",
        "uploads",
        "jobs"
    )
    $excludeFiles = @(
        ".env",
        "*.pyc",
        "*.pyo",
        "*.log",
        "*.onnx",
        "*.pth",
        "*.safetensors",
        "*.whl",
        "*.mp4",
        "*.MP4"
    )

    if ($DryRun) {
        Write-Host "[GIGAvibe] Dry run: files were downloaded but not copied." -ForegroundColor Yellow
    } else {
        Invoke-RobocopySafe -Source $sourceRoot -Destination $Root -ExcludeDirs $excludeDirs -ExcludeFiles $excludeFiles
        $marker = Join-Path $Root "install\last-update.txt"
        @(
            "UpdatedAt=$((Get-Date).ToString("s"))",
            "Source=$RepoArchiveUrl"
        ) | Set-Content -Path $marker -Encoding UTF8
        Write-Host "[GIGAvibe] Update complete." -ForegroundColor Green
    }
} finally {
    if (-not $KeepTemp -and (Test-Path $tempRoot)) {
        Remove-Item $tempRoot -Recurse -Force
    }
}
