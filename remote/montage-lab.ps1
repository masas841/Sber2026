$ErrorActionPreference = "Stop"
$ff  = "C:\Users\user\ffmpeg\ffmpeg.exe"
$dir = "C:\Users\user\gigavibe\data\outputs\lab"
Get-ChildItem $dir -Filter "lab_*.mp4" | ForEach-Object {
    $name = $_.BaseName
    $out  = Join-Path $dir ("montage_" + $name + ".png")
    & $ff -hide_banner -loglevel error -y -i $_.FullName -vf "select='not(mod(n\,24))',scale=260:-1,tile=7x1" -frames:v 1 $out
    Write-Host ("MONTAGE " + $out)
}
