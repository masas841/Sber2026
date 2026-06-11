# setup-ssh-key-auth.ps1
# Configure SSH key auth for a local Windows user.
# Run as Administrator on the target Windows machine.

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

function Get-UserHomePath {
    param([string]$Name)
    $profilePath = Join-Path "C:\Users" $Name
    if (-not (Test-Path $profilePath)) {
        throw "User profile path not found: $profilePath"
    }
    return $profilePath
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

function Set-KeyFilePermissions {
    param(
        [string]$SshDir,
        [string]$AuthFile,
        [string]$UserName
    )

    & icacls $SshDir /inheritance:r | Out-Null
    & icacls $SshDir /grant:r "${UserName}:(OI)(CI)F" "SYSTEM:(OI)(CI)F" | Out-Null

    & icacls $AuthFile /inheritance:r | Out-Null
    & icacls $AuthFile /grant:r "${UserName}:F" "SYSTEM:F" | Out-Null
}

function Set-AdminsAuthPermissions {
    param([string]$AuthFile)
    & icacls $AuthFile /inheritance:r | Out-Null
    & icacls $AuthFile /grant:r "Administrators:F" "SYSTEM:F" | Out-Null
}

function Ensure-KeyInFile {
    param(
        [string]$FilePath,
        [string]$Key,
        [string]$Label
    )
    if (-not (Test-Path $FilePath)) {
        New-Item -ItemType File -Path $FilePath -Force | Out-Null
    }
    $existing = Get-Content -Path $FilePath -ErrorAction SilentlyContinue
    if ($existing -contains $Key) {
        Write-Log "Key already exists in $Label."
    } else {
        Add-Content -Path $FilePath -Value $Key -Encoding ascii
        Write-Log "Public key added to $Label."
    }
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$script:LogFile = Join-Path $LogDir ("ssh-key-auth-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

try {
    Assert-Admin
    Ensure-SshdService

    $userHome = Get-UserHomePath -Name $UserName
    $sshDir = Join-Path $userHome ".ssh"
    $authFile = Join-Path $sshDir "authorized_keys"
    $key = Normalize-Key -Key $PublicKey

    if (-not $key.StartsWith("ssh-")) {
        throw "PublicKey does not look like a valid OpenSSH public key."
    }

    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    Ensure-KeyInFile -FilePath $authFile -Key $key -Label "authorized_keys (user profile)"

    Set-KeyFilePermissions -SshDir $sshDir -AuthFile $authFile -UserName $UserName

    # Always configure administrators_authorized_keys too.
    # This avoids auth ambiguity on Windows OpenSSH when account is in Administrators.
    $adminAuth = "C:\ProgramData\ssh\administrators_authorized_keys"
    try {
        Ensure-KeyInFile -FilePath $adminAuth -Key $key -Label "administrators_authorized_keys"
        Set-AdminsAuthPermissions -AuthFile $adminAuth
    } catch {
        Write-Log "Could not update administrators_authorized_keys: $($_.Exception.Message)" "WARN"
        Write-Log "Continue with user profile authorized_keys only." "WARN"
    }

    Restart-Service sshd

    Write-Log "Done. Test from client:"
    Write-Log "ssh $UserName@<SERVER_IP> `"whoami`""
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
