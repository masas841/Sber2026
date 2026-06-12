# SVG из Figma Desktop (localhost:3845) для интерактива «Улыбка».
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Out = Join-Path $Root "web\assets\figma"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

$assets = @{
  "master-gradient.svg"    = "147d773b63d7483a77fb0f5b167106c909903f78.svg"
  "mask-subtract.svg"      = "c388cb261360cd5fc2e73e5069b345b29795a959.svg"
  "sticker-sber.svg"       = "893d3e89d211c299b85f34d6a2234b81d5e3949e.svg"
  "sticker-smile.svg"      = "ba4b69a60c2d4cb6eaa9dbb4e734cee8262f18b0.svg"
  "sticker-smile-qr.svg"   = "93625fba47b6c4dccdcd7668a40d94defd825516.svg"
  "spring-scribble.svg"    = "fea6653d2712c2624c7100d16192548d253288a0.svg"
  "spring-scribble-qr.svg" = "3838156bdbdd5c1ad47206f8d50c64d37216b6bb.svg"
  "star-large.svg"         = "16bdbf70aa6093560c34ce612bb3e5c08e74cd10.svg"
  "star-small.svg"         = "794a00b89c33777cc98ecd46c9035197be11d480.svg"
  "star-tiny.svg"          = "0081b1eb59fb67f5f33e69073410f019bd0807f7.svg"
  "star-mid.svg"           = "ac7b3d17f8f7c8f3792f87f0988e53b36db248ca.svg"
  "star-big.svg"           = "d84254186b30768926ac51c6a5a1945267791a45.svg"
  "wave-curve.svg"         = "2f22a342a429929a905994c2929b7dc95cef3157.svg"
  "sticker-cluster-a.svg"  = "06b8dfc54be3084706a7bf101ae3e817556c77c3.svg"
  "sticker-cluster-b.svg"  = "9076b69de69745625fb956cae6835ac29ca3d477.svg"
  "sticker-cluster-c.svg"  = "222eea3063b3bd71e8e5c37d4936424e491c3b63.svg"
  "sticker-cluster-d.svg"  = "1355a140d8080949ba1efed96b75cf37cac9e5ce.svg"
  "sticker-cluster-e.svg"  = "a23bf7056b3e33ffccbba524d2f2139d0909afd2.svg"
  "sticker-cluster-f.svg"  = "cec6cefc1e0e719fa72066e78e1739ab7dc98920.svg"
  "sticker-cluster-g.svg"  = "505e454fb201d5a22f2bb995053d94f2db20cd8b.svg"
  "sticker-cluster-h.svg"  = "628f02a5b6e4c60329b86b85bd4ef07ae968856c.svg"
  "sticker-sber-lg.svg"    = "23f78884df05d58b744eddf6c0b251c781c6a712.svg"
  "qr-cluster-tr.svg"      = "22f23c2f5a2ee7cec4ca8ac6a86a99a58d5618b7.svg"
  "qr-cluster-tl.svg"      = "22f23c2f5a2ee7cec4ca8ac6a86a99a58d5618b7.svg"
  "hold-bg-sber.svg"       = "dc385b7935f62a7a5571a36404e357e743711b97.svg"
  "hold-bg-smile-left.svg" = "cc3dcc4936c834ee082e8fdb6d69d10a3bd6fd21.svg"
  "hold-bg-star-left.svg"  = "2e86a0ba3e9347e51329f69ce7325bfa216d4344.svg"
  "hold-bg-wave-right-low.svg" = "d7ffc1cef9a59e7908f3b98a05e483b472b42497.svg"
  "hold-bg-wave-left.svg"  = "ea14904cd0dc37b59e5f5fcf2eca3eff227f1149.svg"
  "hold-bg-wave-right-top.svg" = "2acee622c2059ce2998b0ba79464dafabc8af90e.svg"
  "hold-bg-smile-right.svg" = "fe6a100121d6d6c95342c4ae5b3819351a569eb1.svg"
  "hold-bg-star-blue-small.svg" = "64bba17c88a5c69d9fd6f9527c9320dde86b1a7c.svg"
  "hold-bg-star-pink-small.svg" = "316790140f448b058a2f5df2ffbdc2dd6fbc02d2.svg"
  "hold-bg-star-pink-right.svg" = "acc9e5acdb8969a23b3d2213786b85a687b891d4.svg"
}

# QR-код (node 137:115): SVG из MCP — только белый фон; полный код — PNG:
#   node scripts/figma_mcp_call.mjs shot 137:115 isolated
#   copy scripts/figma_out/shot_137-115.png web/assets/figma/qr-code.png

$ok = 0
$fail = 0
foreach ($entry in $assets.GetEnumerator()) {
  $dest = Join-Path $Out $entry.Key
  $url = "http://127.0.0.1:3845/assets/$($entry.Value)"
  Write-Host "GET $($entry.Key)"
  try {
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    $ok++
  } catch {
    Write-Warning "SKIP $($entry.Key): $($_.Exception.Message)"
    $fail++
  }
}

Write-Host "Done: $($assets.Count) files -> $Out"
