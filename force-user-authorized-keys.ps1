# force-user-authorized-keys.ps1
# Force OpenSSH on Windows to use user profile authorized_keys.
# Run as Administrator on target Windows machine.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$UserName,

    [Parameter(Mandatory = $true)]
    [string]$PublicKey,

    [string]$LogDir = "$env:ProgramData\ssh-setup-logs"
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts][$Level] $Message"
    Write-Host $line
    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value $line -Encoding UTF8
    }
}

function Assert-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $pr = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script as Administrator."
    }
}

function Normalize-Key {
    param([string]$Key)
    return ($Key -replace "`r", "" -replace "`n", "").Trim()
}

function Ensure-SshdService {
    $svc = Get-Service -Name "sshd" -ErrorAction SilentlyContinue
    if (-not $svc) {
        throw "Service sshd not found. Install OpenSSH Server first."
    }
    if ($svc.StartType -ne "Automatic") {
        Set-Service -Name "sshd" -StartupType Automatic
    }
    if ($svc.Status -ne "Running") {
        Start-Service -Name "sshd"
    }
}

function Update-SshdConfig {
    $config = "C:\ProgramData\ssh\sshd_config"
    if (-not (Test-Path $config)) {
        throw "sshd_config not found: $config"
    }

    $backup = "$config.bak-" + (Get-Date -Format "yyyyMMdd-HHmmss")
    Copy-Item $config $backup -Force
    Write-Log "Backup created: $backup"

    $content = Get-Content $config -Raw
    $content = $content -replace '(?m)^\s*Match Group administrators\s*$', '# Match Group administrators'
    $content = $content -replace '(?m)^\s*AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys\s*$', '# AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys'
    Set-Content -Path $config -Value $content -Encoding ascii
    Write-Log "sshd_config updated to use user authorized_keys."
}

function Set-UserAuthorizedKeys {
    param(
        [string]$UserName,
        [string]$PublicKey
    )

    $userHome = Join-Path "C:\Users" $UserName
    if (-not (Test-Path $userHome)) {
        throw "User profile path not found: $userHome"
    }

    $sshDir = Join-Path $userHome ".ssh"
    $auth = Join-Path $sshDir "authorized_keys"

    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    Set-Content -Path $auth -Value $PublicKey -Encoding ascii
    Write-Log "authorized_keys updated: $auth"

    & icacls $sshDir /inheritance:r | Out-Null
    & icacls $sshDir /grant:r "${UserName}:(OI)(CI)F" "SYSTEM:(OI)(CI)F" | Out-Null
    & icacls $auth /inheritance:r | Out-Null
    & icacls $auth /grant:r "${UserName}:F" "SYSTEM:F" | Out-Null
    Write-Log "ACL fixed for $sshDir and authorized_keys."
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$script:LogFile = Join-Path $LogDir ("ssh-force-user-auth-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

try {
    Assert-Admin
    $key = Normalize-Key -Key $PublicKey
    if (-not $key.StartsWith("ssh-")) {
        throw "PublicKey does not look like a valid OpenSSH public key."
    }

    Ensure-SshdService
    Update-SshdConfig
    Set-UserAuthorizedKeys -UserName $UserName -PublicKey $key
    Restart-Service sshd

    Write-Log "Done."
    Write-Log "Test from client: ssh $UserName@192.168.1.243 `"whoami`""
    Write-Log "Log file: $script:LogFile"
    exit 0
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)" "ERROR"
    if ($script:LogFile) {
        Write-Log "See log: $script:LogFile" "ERROR"
    }
    exit 1
}
