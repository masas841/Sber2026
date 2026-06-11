# setup-openssh-server.ps1
# Install and configure OpenSSH Server on Windows 11 (ASCII, PS 5.1+)

[CmdletBinding()]
param(
    [string]$LogDir = "$env:ProgramData\ssh-setup-logs",
    [switch]$ForceDism
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

function Get-CapabilityState {
    $cap = Get-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0" -ErrorAction SilentlyContinue
    if (-not $cap) { return "Unknown" }
    return $cap.State
}

function Install-OpenSshServer {
    param([switch]$UseDismOnly)

    $state = Get-CapabilityState
    Write-Log "OpenSSH.Server capability state: $state"

    if ($state -eq "Installed") {
        Write-Log "OpenSSH.Server already installed."
        return
    }

    if (-not $UseDismOnly) {
        Write-Log "Trying Add-WindowsCapability..."
        $ok = $false
        try {
            Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0" | Out-Null
            $ok = $true
        } catch {
            Write-Log "Add-WindowsCapability failed: $($_.Exception.Message)" "WARN"
        }
        if (-not $ok) {
            Write-Log "Add-WindowsCapability did not complete cleanly." "WARN"
        }
    }

    $state = Get-CapabilityState
    if ($state -ne "Installed") {
        Write-Log "Trying DISM fallback..."
        $dismArgs = @("/online", "/Add-Capability", "/CapabilityName:OpenSSH.Server~~~~0.0.1.0")
        $p = Start-Process -FilePath "dism.exe" -ArgumentList $dismArgs -Wait -NoNewWindow -PassThru
        if ($p.ExitCode -ne 0) {
            throw "DISM exit code $($p.ExitCode). OpenSSH.Server install failed."
        }
    }

    $state = Get-CapabilityState
    if ($state -ne "Installed") {
        throw "OpenSSH.Server is not installed (state=$state)."
    }

    Write-Log "OpenSSH.Server installed successfully."
}

function Ensure-SshdService {
    $svc = Get-Service -Name "sshd" -ErrorAction SilentlyContinue
    if (-not $svc) {
        throw "Service sshd not found after OpenSSH.Server install."
    }

    if ($svc.StartType -ne "Automatic") {
        Set-Service -Name "sshd" -StartupType Automatic
        Write-Log "sshd StartupType set to Automatic."
    }

    if ($svc.Status -ne "Running") {
        Start-Service -Name "sshd"
        Write-Log "sshd service started."
    } else {
        Write-Log "sshd service already running."
    }
}

function Ensure-FirewallRule {
    $ruleName = "OpenSSH-Server-In-TCP"
    $rule = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue

    if (-not $rule) {
        New-NetFirewallRule -Name $ruleName -DisplayName "OpenSSH Server (sshd)" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
        Write-Log "Firewall rule created: $ruleName (TCP/22)."
    } else {
        Set-NetFirewallRule -Name $ruleName -Enabled True | Out-Null
        Write-Log "Firewall rule already exists: $ruleName."
    }
}

function Test-SshLocal {
    $t = Test-NetConnection -ComputerName localhost -Port 22 -WarningAction SilentlyContinue
    if (-not $t.TcpTestSucceeded) {
        throw "localhost:22 test failed."
    }
    Write-Log "localhost:22 test OK."
}

function Print-Summary {
    $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "169.254.*" -and $_.InterfaceOperationalStatus -eq "Up" } |
        Select-Object -First 1 -ExpandProperty IPAddress

    $svc = Get-Service sshd
    Write-Log "RESULT: sshd Status=$($svc.Status), StartType=$($svc.StartType)"
    if ($ip) {
        Write-Log "Connect from another PC: ssh USERNAME@$ip"
    } else {
        Write-Log "Could not detect IPv4 automatically." "WARN"
    }
    Write-Log "Log file: $script:LogFile"
}

# --- main ---
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$script:LogFile = Join-Path $LogDir ("ssh-setup-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

try {
    Assert-Admin
    Write-Log "Starting OpenSSH Server setup..."
    Install-OpenSshServer -UseDismOnly:$ForceDism
    Ensure-SshdService
    Ensure-FirewallRule
    Test-SshLocal
    Print-Summary
    Write-Log "Done."
    exit 0
} catch {
    Write-Log "ERROR: $($_.Exception.Message)" "ERROR"
    if ($script:LogFile) {
        Write-Log "See log: $script:LogFile" "ERROR"
    }
    exit 1
}
