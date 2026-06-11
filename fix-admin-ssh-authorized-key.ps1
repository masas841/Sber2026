# fix-admin-ssh-authorized-key.ps1
# Force setup of C:\ProgramData\ssh\administrators_authorized_keys
# Run as Administrator on the target Windows machine.

[CmdletBinding()]
param(
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

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$script:LogFile = Join-Path $LogDir ("ssh-admin-auth-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

try {
    Assert-Admin
    Ensure-SshdService

    $key = Normalize-Key -Key $PublicKey
    if (-not $key.StartsWith("ssh-")) {
        throw "PublicKey does not look like a valid OpenSSH public key."
    }

    $authPath = "C:\ProgramData\ssh\administrators_authorized_keys"
    New-Item -ItemType File -Path $authPath -Force | Out-Null
    Set-Content -Path $authPath -Value $key -Encoding ascii
    Write-Log "administrators_authorized_keys updated."

    & icacls $authPath /inheritance:r | Out-Null
    & icacls $authPath /grant:r "Administrators:F" "SYSTEM:F" | Out-Null
    Write-Log "ACL fixed for administrators_authorized_keys."

    Restart-Service sshd
    Write-Log "sshd restarted."

    Write-Log "Done. Test:"
    Write-Log "ssh user@192.168.1.243 `"whoami`""
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
