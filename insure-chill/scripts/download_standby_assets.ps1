$ErrorActionPreference = "Stop"

# Standby screen assets — Figma node 55:62 (figma-implement-design workflow)
# Refresh after get_design_context: download asset URLs from MCP response.

$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $root "static\assets\figma\standby"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$assets = @(
    @{ Name = "export-2x.png"; Url = "https://www.figma.com/api/mcp/asset/ea6159cb-f81a-4439-88fb-332f630e1f55"; Role = "reference" },
    @{ Name = "title-star-standby.svg"; Url = "https://www.figma.com/api/mcp/asset/92a38fdb-7c81-472b-a86d-05b7f05ab9be"; Role = "decor" },
    @{ Name = "logo-sberinsurance-standby.svg"; Url = "https://www.figma.com/api/mcp/asset/7b32c9d7-cccb-4b49-a43c-ca3c631f5b1a"; Role = "brand" },
    @{ Name = "blob-1.svg"; Url = "https://www.figma.com/api/mcp/asset/fe0e3663-7439-4eb4-8494-e438ab903e9b"; Role = "decor" },
    @{ Name = "blob-2.svg"; Url = "https://www.figma.com/api/mcp/asset/2742c337-5460-4571-9709-bd0175892cc4"; Role = "decor" },
    @{ Name = "blob-3.svg"; Url = "https://www.figma.com/api/mcp/asset/14692035-581c-4dfa-862e-fa319e06229d"; Role = "decor" },
    @{ Name = "grass-standby.png"; Url = "https://www.figma.com/api/mcp/asset/33af820f-e27f-43b1-870d-c074cbfee5a5"; Role = "background" }
)

$manifest = [ordered]@{
    figmaNode = "55:62"
    fileKey = "AnXkfv1tOAPkBLcjzexhaG"
    workflow = "figma-implement-design"
    stage = 672
    assets = @()
}

foreach ($asset in $assets) {
    $dest = Join-Path $out $asset.Name
    Write-Host "GET $($asset.Name)"
    Invoke-WebRequest -Uri $asset.Url -OutFile $dest -UseBasicParsing
    $item = Get-Item $dest
    $manifest.assets += [ordered]@{
        name = $asset.Name
        role = $asset.Role
        source = $asset.Url
        bytes = $item.Length
    }
}

$manifestPath = Join-Path $out "manifest.json"
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $manifestPath
Write-Host "Saved $($assets.Count) assets to $out"
