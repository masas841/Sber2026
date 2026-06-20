function Invoke-KioskGitHubUpdate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AppLabel,
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [string]$Subdir,
        [string]$RepoArchiveUrl = "",
        [string]$ManifestUrl = "",
        [string]$RawBaseUrl = "",
        [scriptblock]$PostUpdateHook,
        [switch]$DryRun,
        [switch]$FullArchive,
        [switch]$KeepTemp
    )

    $ErrorActionPreference = "Stop"

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
            Write-Host "[$AppLabel] WARN: could not resolve GitHub ref '$Ref'; using raw URL as configured." -ForegroundColor Yellow
        }
        return ""
    }

    function Use-GitHubCdnRef {
        param(
            [string]$Url,
            [string]$Ref,
            [string]$Sha
        )
        if (-not $Sha) { return $Url }
        $needle = "/masas841/Sber2026/$Ref/"
        $replacement = "/masas841/Sber2026/$Sha/"
        $nextUrl = $Url.Replace($needle, $replacement)
        $cdnNeedle = "@$Ref/"
        $cdnReplacement = "@$Sha/"
        return $nextUrl.Replace($cdnNeedle, $cdnReplacement)
    }

    function Convert-GitHubRawToCdnUrl {
        param([string]$Url)
        if (-not $Url) { return $Url }
        if ($Url -match "^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)(/.*)?$") {
            $owner = $matches[1]
            $repo = $matches[2]
            $ref = $matches[3]
            $path = $matches[4]
            return "https://cdn.jsdelivr.net/gh/$owner/$repo@$ref$path"
        }
        return $Url
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
            "install/wheels/",
            "runtime/"
        )
        foreach ($prefix in $protectedPrefixes) {
            if ($normalized.StartsWith($prefix)) { return $true }
        }
        return $false
    }

    $envPath = Join-Path $Root ".env"
    if (-not $ManifestUrl) {
        $ManifestUrl = Read-DotEnvValue -Path $envPath -Name "UPDATE_MANIFEST_URL"
    }
    if (-not $ManifestUrl) {
        $ManifestUrl = "https://cdn.jsdelivr.net/gh/masas841/Sber2026@main/$Subdir/install/update-manifest.json"
    }
    if (-not $RawBaseUrl) {
        $RawBaseUrl = Read-DotEnvValue -Path $envPath -Name "UPDATE_RAW_BASE_URL"
    }
    if (-not $RawBaseUrl) {
        $RawBaseUrl = "https://cdn.jsdelivr.net/gh/masas841/Sber2026@main/$Subdir"
    }
    $ManifestUrl = Convert-GitHubRawToCdnUrl -Url $ManifestUrl
    $RawBaseUrl = Convert-GitHubRawToCdnUrl -Url $RawBaseUrl
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
    $tempRoot = Join-Path $env:TEMP "$Subdir-update-$stamp"
    $zipPath = Join-Path $tempRoot "repo.zip"
    $extractPath = Join-Path $tempRoot "repo"
    $remoteManifestPath = Join-Path $tempRoot "update-manifest.json"
    $localManifestPath = Join-Path $Root "install\update-manifest.json"

    Write-Host "[$AppLabel] Manifest source: $ManifestUrl" -ForegroundColor Cyan
    Write-Host "[$AppLabel] Install root: $Root"

    try {
        New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $headers = @{
            "User-Agent" = "$AppLabel-Updater"
        }
        if ($githubToken) {
            $headers["Authorization"] = "Bearer $githubToken"
            Write-Host "[$AppLabel] GitHub token configured." -ForegroundColor DarkGray
        }

        if (-not $FullArchive) {
            $rawRef = Read-DotEnvValue -Path $envPath -Name "UPDATE_REPO_REF"
            if (-not $rawRef) { $rawRef = "main" }
            $rawSha = Resolve-GitHubCommitSha -Ref $rawRef -Headers $headers
            if ($rawSha) {
                $ManifestUrl = Use-GitHubCdnRef -Url $ManifestUrl -Ref $rawRef -Sha $rawSha
                $RawBaseUrl = Use-GitHubCdnRef -Url $RawBaseUrl -Ref $rawRef -Sha $rawSha
                Write-Host "[$AppLabel] GitHub ref $rawRef -> $rawSha" -ForegroundColor DarkGray
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
                    Write-Host "[$AppLabel] GitHub manifest is not available anonymously." -ForegroundColor Yellow
                    Write-Host "[$AppLabel] If the repo is private, set UPDATE_GITHUB_TOKEN in .env." -ForegroundColor Yellow
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

            Write-Host "[$AppLabel] Changed files: $($changed.Count); removed files: $($removed.Count)"
            if ($DryRun) {
                $changed | Select-Object -First 30 | ForEach-Object { Write-Host "  update $($_.path)" }
                $removed | Select-Object -First 30 | ForEach-Object { Write-Host "  remove $($_.path)" }
                Write-Host "[$AppLabel] Dry run: no files were changed." -ForegroundColor Yellow
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
                Write-Host "[$AppLabel] Updated $rel"
            }

            foreach ($file in $removed) {
                $rel = [string]$file.path
                if (Test-ProtectedUpdatePath -Path $rel) {
                    Write-Host "[$AppLabel] Preserved local $rel"
                    continue
                }
                $targetPath = Join-Path $Root ($rel -replace "/", "\")
                if (Test-Path $targetPath) {
                    Remove-Item $targetPath -Force
                    Write-Host "[$AppLabel] Removed $rel"
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
            if ($PostUpdateHook) {
                & $PostUpdateHook
            }
            Write-Host "[$AppLabel] Update complete." -ForegroundColor Green
            return
        }

        Write-Host "[$AppLabel] Full archive fallback enabled." -ForegroundColor Yellow
        Write-Host "[$AppLabel] Update source: $RepoArchiveUrl" -ForegroundColor Cyan
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
                Write-Host "[$AppLabel] GitHub archive is not available anonymously." -ForegroundColor Yellow
                Write-Host "[$AppLabel] If the repo is private, set UPDATE_GITHUB_TOKEN in .env." -ForegroundColor Yellow
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
            ".aigo123",
            "runtime",
            "dist",
            "backups",
            "certs",
            "wheels",
            "__pycache__"
        )
        $excludeFiles = @(
            ".env",
            "*.pyc",
            "*.pyo",
            "*.log",
            "*.whl"
        )

        if ($DryRun) {
            Write-Host "[$AppLabel] Dry run: files were downloaded but not copied." -ForegroundColor Yellow
        } else {
            Invoke-RobocopySafe -Source $sourceRoot -Destination $Root -ExcludeDirs $excludeDirs -ExcludeFiles $excludeFiles
            $marker = Join-Path $Root "install\last-update.txt"
            @(
                "UpdatedAt=$((Get-Date).ToString("s"))",
                "Source=$RepoArchiveUrl"
            ) | Set-Content -Path $marker -Encoding UTF8
            if ($PostUpdateHook) {
                & $PostUpdateHook
            }
            Write-Host "[$AppLabel] Update complete." -ForegroundColor Green
        }
    } finally {
        if (-not $KeepTemp -and (Test-Path $tempRoot)) {
            Remove-Item $tempRoot -Recurse -Force
        }
    }
}
