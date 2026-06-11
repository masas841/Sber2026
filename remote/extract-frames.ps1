$ErrorActionPreference = "Stop"
$ff  = "C:\Users\user\ffmpeg\ffmpeg.exe"
$src = "C:\Users\user\gigavibe\data\outputs\ltx_full_test.mp4"
$out = "C:\Users\user\gigavibe\data\outputs\frames"
$step = 50
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force -Path $out | Out-Null
& $ff -hide_banner -loglevel error -i $src -vf "select=not(mod(n\,$step))" -vsync vfr -frame_pts 1 (Join-Path $out "frame_%05d.png")
Write-Host "FRAMES:"
Get-ChildItem $out -Filter *.png | ForEach-Object { Write-Host $_.Name }
