# Upscale every photo in photos/raw 4x and save it to photos/clean.
# Uses realesrgan-ncnn-vulkan (the engine inside Upscayl), which runs on the AMD GPU via Vulkan.
# Run from anywhere:  powershell -File scripts\upscale-photos.ps1

$root = Split-Path $PSScriptRoot -Parent
$exe  = Join-Path $root "tools\realesrgan\realesrgan-ncnn-vulkan.exe"
$raw  = Join-Path $root "photos\raw"
$out  = Join-Path $root "photos\clean"

if (-not (Test-Path $exe)) {
    Write-Error "Upscaler missing. Download realesrgan-ncnn-vulkan-20220424-windows.zip from https://github.com/xinntao/Real-ESRGAN/releases and unzip it to tools\realesrgan"
    exit 1
}

New-Item -ItemType Directory -Force $out | Out-Null

Get-ChildItem $raw -Filter *.png | ForEach-Object {
    $dest = Join-Path $out ($_.BaseName + "-4x.png")
    Write-Host "Upscaling $($_.Name) -> $(Split-Path $dest -Leaf)"
    # realesrgan-x4plus = general photo model (the "anime" models are for drawings)
    & $exe -i $_.FullName -o $dest -n realesrgan-x4plus -s 4 -f png
}
