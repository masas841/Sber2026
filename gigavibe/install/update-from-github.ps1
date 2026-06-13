param(
    [string]$RepoArchiveUrl = "",
    [string]$ManifestUrl = "",
    [string]$RawBaseUrl = "",
    [string]$Subdir = "gigavibe",
    [switch]$DryRun,
    [switch]$FullArchive,
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

function ConvertTo-UrlPath {
    param([string]$Path)
    return ($Path -split "/" | ForEach-Object { [uri]::EscapeDataString($_) }) -join "/"
}

function Get-FileSha256 {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return "" }
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    return Get-Content -Path $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Resolve-GitHubCommitSha {
    param(
        [string]$Ref,
        [hashtable]$Headers
    )
    $apiUrl = "https://api.github.com/repos/masas841/Sber2026/commits/$([uri]::EscapeDataString($Ref))"
    try {
        $response = Invoke-RestMethod -Uri $apiUrl -UseBasicParsing -Headers $Headers
        if ($response.sha) { return [string]$response.sha }
    } catch {
        Write-Host "[GIGAvibe] WARN: could not resolve GitHub ref '$Ref'; using raw URL as configured." -ForegroundColor Yellow
    }
    return ""
}

function Use-GitHubRawRef {
    param(
        [string]$Url,
        [string]$Ref,
        [string]$Sha
    )
    if (-not $Sha) { return $Url }
    $needle = "/masas841/Sber2026/$Ref/"
    $replacement = "/masas841/Sber2026/$Sha/"
    return $Url.Replace($needle, $replacement)
}

function Test-ProtectedUpdatePath {
    param([string]$Path)
    $normalized = $Path.Replace("\", "/").TrimStart("/")
    if ($normalized -eq ".env") { return $true }
    $protectedPrefixes = @(
        ".venv/",
        ".venv-liveportrait/",
        ".aigo123/",
        "backups/",
        "certs/",
        "data/",
        "dist/",
        "gfpgan/",
        "install/wheels/",
        "models/",
        "runtime/",
        "tools/",
        "vendor/"
    )
    foreach ($prefix in $protectedPrefixes) {
        if ($normalized.StartsWith($prefix)) { return $true }
    }
    return $false
}

function Add-GigaEnvDefault {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value,
        [string]$Comment = ""
    )

    $existing = Read-DotEnvValue -Path $Path -Name $Name
    if ($null -ne $existing) { return $false }
    if ($Comment) {
        Add-Content -Path $Path -Value $Comment -Encoding UTF8
    }
    Add-Content -Path $Path -Value "$Name=$Value" -Encoding UTF8
    return $true
}

function Update-GigaEnvDefaults {
    param([string]$Root)

    $envFile = Join-Path $Root ".env"
    $example = Join-Path $Root "install\.env.kiosk.example"
    if (-not (Test-Path $envFile)) {
        if (Test-Path $example) {
            Copy-Item $example $envFile
            Write-Host "[GIGAvibe] Created .env from install\.env.kiosk.example" -ForegroundColor Yellow
        } else {
            New-Item -ItemType File -Path $envFile -Force | Out-Null
            Write-Host "[GIGAvibe] Created empty .env" -ForegroundColor Yellow
        }
    }

    $added = 0
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_ENABLED" -Value "true" -Comment "# Realtime diagnostics: send kiosk logs to photo_receiver.")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_URL" -Value "" -Comment "# Diagnostics: upload kiosk logs to photo_receiver. Empty URL reuses OUTPUT_UPLOAD_URL.")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_API_KEY" -Value "")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_AUTH" -Value "bearer")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_KIOSK_ID" -Value $env:COMPUTERNAME)
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_INTERVAL_SEC" -Value "60")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_PATHS" -Value "data/srv_out.log;data/srv_err.log;server.log")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_MAX_BYTES" -Value "524288")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_INITIAL_TAIL_BYTES" -Value "262144")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "OUTPUT_DISPATCH_FAIL_OPEN" -Value "true" -Comment "# Do not stop kiosk session if upload or print fails.")

    if ($added -gt 0) {
        Write-Host "[GIGAvibe] .env migration: added $added setting(s)." -ForegroundColor Green
    } else {
        Write-Host "[GIGAvibe] .env migration: no changes."
    }
}

$envPath = Join-Path $Root ".env"
if (-not $ManifestUrl) {
    $ManifestUrl = Read-DotEnvValue -Path $envPath -Name "UPDATE_MANIFEST_URL"
}
if (-not $ManifestUrl) {
    $ManifestUrl = "https://raw.githubusercontent.com/masas841/Sber2026/main/gigavibe/install/update-manifest.json"
}
if (-not $RawBaseUrl) {
    $RawBaseUrl = Read-DotEnvValue -Path $envPath -Name "UPDATE_RAW_BASE_URL"
}
if (-not $RawBaseUrl) {
    $RawBaseUrl = "https://raw.githubusercontent.com/masas841/Sber2026/main/gigavibe"
}
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
$remoteManifestPath = Join-Path $tempRoot "update-manifest.json"
$localManifestPath = Join-Path $Root "install\update-manifest.json"

Write-Host "[GIGAvibe] Manifest source: $ManifestUrl" -ForegroundColor Cyan
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

    if (-not $FullArchive) {
        $rawRef = Read-DotEnvValue -Path $envPath -Name "UPDATE_REPO_REF"
        if (-not $rawRef) { $rawRef = "main" }
        $rawSha = Resolve-GitHubCommitSha -Ref $rawRef -Headers $headers
        if ($rawSha) {
            $ManifestUrl = Use-GitHubRawRef -Url $ManifestUrl -Ref $rawRef -Sha $rawSha
            $RawBaseUrl = Use-GitHubRawRef -Url $RawBaseUrl -Ref $rawRef -Sha $rawSha
            Write-Host "[GIGAvibe] GitHub ref $rawRef -> $rawSha" -ForegroundColor DarkGray
        }
        $manifestArgs = @{
            Uri = $ManifestUrl
            OutFile = $remoteManifestPath
            UseBasicParsing = $true
            Headers = $headers
        }
        try {
            Invoke-WebRequest @manifestArgs
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.value__
            if ($statusCode -eq 404 -and -not $githubToken) {
                Write-Host "[GIGAvibe] GitHub manifest is not available anonymously." -ForegroundColor Yellow
                Write-Host "[GIGAvibe] If the repo is private, set UPDATE_GITHUB_TOKEN in .env." -ForegroundColor Yellow
            }
            throw
        }

        $remoteManifest = Read-JsonFile -Path $remoteManifestPath
        $localManifest = Read-JsonFile -Path $localManifestPath
        $remoteFiles = @($remoteManifest.files)
        $localFiles = if ($localManifest) { @($localManifest.files) } else { @() }
        $remoteByPath = @{}
        foreach ($file in $remoteFiles) { $remoteByPath[$file.path] = $file }
        $localByPath = @{}
        foreach ($file in $localFiles) { $localByPath[$file.path] = $file }

        $changed = @()
        foreach ($file in $remoteFiles) {
            $targetPath = Join-Path $Root ($file.path -replace "/", "\")
            $localHash = Get-FileSha256 -Path $targetPath
            if ($localHash -ne ([string]$file.sha256).ToLowerInvariant()) {
                $changed += $file
            }
        }

        $removed = @()
        if ($localFiles.Count -gt 0) {
            foreach ($file in $localFiles) {
                if (-not $remoteByPath.ContainsKey($file.path)) {
                    $removed += $file
                }
            }
        }

        Write-Host "[GIGAvibe] Changed files: $($changed.Count); removed files: $($removed.Count)"
        if ($DryRun) {
            $changed | Select-Object -First 30 | ForEach-Object { Write-Host "  update $($_.path)" }
            $removed | Select-Object -First 30 | ForEach-Object { Write-Host "  remove $($_.path)" }
            Write-Host "[GIGAvibe] Dry run: no files were changed." -ForegroundColor Yellow
            return
        }

        foreach ($file in $changed) {
            $rel = [string]$file.path
            $targetPath = Join-Path $Root ($rel -replace "/", "\")
            New-Item -ItemType Directory -Force -Path (Split-Path $targetPath -Parent) | Out-Null
            $fileUrl = ($RawBaseUrl.TrimEnd("/") + "/" + (ConvertTo-UrlPath -Path $rel))
            $tmpFile = Join-Path $tempRoot ("file-" + [guid]::NewGuid().ToString("N"))
            Invoke-WebRequest -Uri $fileUrl -OutFile $tmpFile -UseBasicParsing -Headers $headers
            $downloadHash = Get-FileSha256 -Path $tmpFile
            if ($downloadHash -ne ([string]$file.sha256).ToLowerInvariant()) {
                throw "sha256 mismatch for $rel"
            }
            Move-Item -Path $tmpFile -Destination $targetPath -Force
            Write-Host "[GIGAvibe] Updated $rel"
        }

        foreach ($file in $removed) {
            $rel = [string]$file.path
            if (Test-ProtectedUpdatePath -Path $rel) {
                Write-Host "[GIGAvibe] Preserved local $rel"
                continue
            }
            $targetPath = Join-Path $Root ($rel -replace "/", "\")
            if (Test-Path $targetPath) {
                Remove-Item $targetPath -Force
                Write-Host "[GIGAvibe] Removed $rel"
            }
        }

        Copy-Item $remoteManifestPath $localManifestPath -Force
        $marker = Join-Path $Root "install\last-update.txt"
        @(
            "UpdatedAt=$((Get-Date).ToString("s"))",
            "Source=$ManifestUrl",
            "Changed=$($changed.Count)",
            "Removed=$($removed.Count)"
        ) | Set-Content -Path $marker -Encoding UTF8
        Update-GigaEnvDefaults -Root $Root
        Write-Host "[GIGAvibe] Update complete." -ForegroundColor Green
        return
    }

    Write-Host "[GIGAvibe] Full archive fallback enabled." -ForegroundColor Yellow
    Write-Host "[GIGAvibe] Update source: $RepoArchiveUrl" -ForegroundColor Cyan
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
        Update-GigaEnvDefaults -Root $Root
        Write-Host "[GIGAvibe] Update complete." -ForegroundColor Green
    }
} finally {
    if (-not $KeepTemp -and (Test-Path $tempRoot)) {
        Remove-Item $tempRoot -Recurse -Force
    }
}
