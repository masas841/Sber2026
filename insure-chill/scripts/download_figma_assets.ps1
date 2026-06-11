$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $root "static\assets\figma"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$assets = @(
    @{ Name = "grass-1.png"; Url = "http://localhost:3845/assets/1563697d12155680b73c4d623f05f35318b669a6.png"; Role = "background" },
    @{ Name = "grass-2-a.png"; Url = "http://localhost:3845/assets/488b182ee2274bda0e42f0406d131ba5de756d0c.png"; Role = "background" },
    @{ Name = "grass-2-b.png"; Url = "http://localhost:3845/assets/199c5ba01a61e6cc478ed13de37575b68e5c4776.png"; Role = "background" },
    @{ Name = "threat-fist.png"; Url = "http://localhost:3845/assets/2c0e597ef34e1e25f22bece7f07f9071453c26c7.png"; Role = "threat" },
    @{ Name = "threat-nail-phone.png"; Url = "http://localhost:3845/assets/2d0eda5d923da2d8f70da9c747d3d14fcee4f987.png"; Role = "threat" },
    @{ Name = "threat-water-drop.png"; Url = "http://localhost:3845/assets/9f7d921244f8a87720fb41610a93ffa0de6d9559.png"; Role = "threat" },
    @{ Name = "threat-parts.png"; Url = "http://localhost:3845/assets/34a734bd52b929f7da6e261c6f5e9256c7a799a8.png"; Role = "threat" },
    @{ Name = "threat-soap-phone.png"; Url = "http://localhost:3845/assets/50dd6d488abd268621b18460892b1285006a37a8.png"; Role = "threat" },
    @{ Name = "threat-cat-paw.png"; Url = "http://localhost:3845/assets/758b324c82f48052d9537c8f4058eacfe56327c7.png"; Role = "threat" },
    @{ Name = "blob-top-left.svg"; Url = "http://localhost:3845/assets/12cec09e6c586bb572d84436f6d0695dbd8c6d1c.svg"; Role = "decor" },
    @{ Name = "blob-top-right.svg"; Url = "http://localhost:3845/assets/8ab12f0277593a970439e0803c032bd4488c67a4.svg"; Role = "decor" },
    @{ Name = "blob-left.svg"; Url = "http://localhost:3845/assets/b667af21d982a01fe7b4e5f39cc82d3848807de7.svg"; Role = "decor" },
    @{ Name = "blob-small.svg"; Url = "http://localhost:3845/assets/080a94aec2e2a62b3a353d62f167e146bb4933ce.svg"; Role = "decor" },
    @{ Name = "stage-ellipse.svg"; Url = "http://localhost:3845/assets/7fd94110479f9644b663d6bde60a3f15ebd66714.svg"; Role = "decor" },
    @{ Name = "title-star-start.svg"; Url = "http://localhost:3845/assets/931825d60dc345fd5f0aff519d1f8eadc067ebc9.svg"; Role = "decor" },
    @{ Name = "title-star-game.svg"; Url = "http://localhost:3845/assets/f071fa1e382de14cf86f4298b2b32ee96e6c38bc.svg"; Role = "decor" },
    @{ Name = "title-star-final.svg"; Url = "http://localhost:3845/assets/6e4c2ab84b30023c3434d1c8b453ed200f83a52c.svg"; Role = "decor" },
    @{ Name = "score-star-start.svg"; Url = "http://localhost:3845/assets/a9bade00bf0c766528db9181e133e1c59fd8ddc9.svg"; Role = "decor" },
    @{ Name = "score-star-small.svg"; Url = "http://localhost:3845/assets/d45d1cafaa111f93cd34ec790d0c9bb887125210.svg"; Role = "decor" },
    @{ Name = "score-star-final.svg"; Url = "http://localhost:3845/assets/4dc97da6ae84b4852e9832b50f96c797e11d1999.svg"; Role = "decor" },
    @{ Name = "timer-circle.svg"; Url = "http://localhost:3845/assets/98c21670ad7b77dabf7bf3a3afd29f508c91d438.svg"; Role = "ui" },
    @{ Name = "scribble-start.svg"; Url = "http://localhost:3845/assets/d9dda420edabe32fae808cfb1bfc057131ccfc3a.svg"; Role = "decor" },
    @{ Name = "scribble-final.svg"; Url = "http://localhost:3845/assets/9c118ff95c5f8128f2f5f1ebe6a393459cb44be5.svg"; Role = "decor" },
    @{ Name = "logo-sberinsurance-start.svg"; Url = "http://localhost:3845/assets/8d4a2d8e1f32b24070a64a555095fc33ac9c3ea5.svg"; Role = "brand" },
    @{ Name = "logo-sberinsurance-game.svg"; Url = "http://localhost:3845/assets/25e49fc23e3cc83c96710dfd67616cf3ad88f8a9.svg"; Role = "brand" },
    @{ Name = "mask-fist-label.svg"; Url = "http://localhost:3845/assets/1ae6cdf18e9c535fe0f243f61826e6f4fd4d174d.svg"; Role = "mask" },
    @{ Name = "mask-nail-phone.svg"; Url = "http://localhost:3845/assets/4963e15d33f05059c321754d7f025f0e4817dd7c.svg"; Role = "mask" },
    @{ Name = "mask-water-drop.svg"; Url = "http://localhost:3845/assets/c8b595d6e77852adca3f52ccd5bca68d12ef31a8.svg"; Role = "mask" },
    @{ Name = "mask-water-label.svg"; Url = "http://localhost:3845/assets/d06d4accc308cb7ebcabfc528df2d0bd25cdb9d5.svg"; Role = "mask" },
    @{ Name = "nail-parts-start.svg"; Url = "http://localhost:3845/assets/fbc898111c94ff99ef8676c919450a09070a31c3.svg"; Role = "threat" },
    @{ Name = "nail-parts-game.svg"; Url = "http://localhost:3845/assets/1d6c0007f5f785403836d29eb5cf16db946f689e.svg"; Role = "threat" },
    @{ Name = "small-decor-start.svg"; Url = "http://localhost:3845/assets/24927cf0c6936edd49d0873684f71c4290139ec3.svg"; Role = "decor" },
    @{ Name = "soap-phone-parts.svg"; Url = "http://localhost:3845/assets/933dfb8e71deca266d95868b52669e5cf43ffa8e.svg"; Role = "threat" },
    @{ Name = "soap-phone-vector.svg"; Url = "http://localhost:3845/assets/267fdc9b92564ae3e0a5c7ec75ce590fa4434083.svg"; Role = "threat" },
    @{ Name = "water-drop-mask-game.svg"; Url = "http://localhost:3845/assets/ff5ba7de925bdbe7531a83ff054eccda6cafabba.svg"; Role = "mask" },
    @{ Name = "water-drop-secondary-mask.svg"; Url = "http://localhost:3845/assets/b35f581dcea1bf2f5a963a868096b3c709d1fd62.svg"; Role = "mask" },
    @{ Name = "water-drop-eyes-start.svg"; Url = "http://localhost:3845/assets/8e60a1ba5aa948f9818a88e8b3db5b64ec7bc3fa.svg"; Role = "threat" },
    @{ Name = "ground-shadow-mask.png"; Url = "http://localhost:3845/assets/57dc28e138203a848aecbd237c363f781468c478.png"; Role = "shadow" },
    @{ Name = "ground-shadow.svg"; Url = "http://localhost:3845/assets/10d4938d8931cabe5ffe50c8e2e6c0ec70203e17.svg"; Role = "shadow" },
    @{ Name = "shadow-small-a.svg"; Url = "http://localhost:3845/assets/0edb4ce890e26f723ba9b449d17de6fda14892ed.svg"; Role = "shadow" },
    @{ Name = "shadow-small-b.svg"; Url = "http://localhost:3845/assets/d225e9dcef1277bc21ab574f0ecb2e2974d4cd8f.svg"; Role = "shadow" },
    @{ Name = "shadow-small-c.svg"; Url = "http://localhost:3845/assets/002d5e052d7fcd25b9f18e22994019a9ff27b7ab.svg"; Role = "shadow" },
    @{ Name = "shadow-wide-a.svg"; Url = "http://localhost:3845/assets/0efb4bda73fed2f9c847ffc1bd9922e7e4013d37.svg"; Role = "shadow" },
    @{ Name = "shadow-wide-b.svg"; Url = "http://localhost:3845/assets/959b43834e7ea4e0ea4e0dc7f562547c1ff7356e.svg"; Role = "shadow" },
    @{ Name = "shadow-wide-c.svg"; Url = "http://localhost:3845/assets/c4423ef102a37a8724eb0b81783f99612fafe697.svg"; Role = "shadow" },
    @{ Name = "shadow-phone-a.svg"; Url = "http://localhost:3845/assets/c55d0ff1c4ae9f358e2a6b776155699ec4b324cb.svg"; Role = "shadow" },
    @{ Name = "shadow-phone-b.svg"; Url = "http://localhost:3845/assets/a31e6ec6726d97ca4a1cb402e737e91f9b571ca3.svg"; Role = "shadow" },
    @{ Name = "shadow-phone-c.svg"; Url = "http://localhost:3845/assets/b6aadf8df2562a8b06f103b3d29b64058dc031de.svg"; Role = "shadow" },
    @{ Name = "final-shadow-a.svg"; Url = "http://localhost:3845/assets/47729c5f9ae6627161c6c11c6caf562c8f66194a.svg"; Role = "shadow" },
    @{ Name = "final-shadow-b.svg"; Url = "http://localhost:3845/assets/b452ae8e9004e0fe6770b14d9d1ffea0b18dafad.svg"; Role = "shadow" },
    @{ Name = "final-shadow-c.svg"; Url = "http://localhost:3845/assets/4efaf7c202fcab1fcd5b24b29a136afd2ccd01b2.svg"; Role = "shadow" },
    @{ Name = "rating-stars-0.svg"; Url = "http://localhost:3845/assets/184a2e059452c1427dc9c93d0be6a47a19fa659d.svg"; Role = "ui" },
    @{ Name = "rating-stars-1.svg"; Url = "http://localhost:3845/assets/4cc1fe84e228bca6149fc92179f1844886a07abd.svg"; Role = "ui" },
    @{ Name = "rating-stars-2.svg"; Url = "http://localhost:3845/assets/46b820384d2096ee7f011aae1ce2f10839a1d3cb.svg"; Role = "ui" },
    @{ Name = "rating-stars-3.svg"; Url = "http://localhost:3845/assets/fad501604c39be24e0a115f68455e6c563d59541.svg"; Role = "ui" }
)

$manifest = @()
foreach ($asset in $assets) {
    $dest = Join-Path $out $asset.Name
    Write-Host "GET $($asset.Name)"
    Invoke-WebRequest -Uri $asset.Url -OutFile $dest -UseBasicParsing
    $item = Get-Item $dest
    $manifest += [ordered]@{
        name = $asset.Name
        role = $asset.Role
        source = $asset.Url
        bytes = $item.Length
    }
}

$manifestPath = Join-Path $out "manifest.json"
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $manifestPath
Write-Host "Done: $out"
