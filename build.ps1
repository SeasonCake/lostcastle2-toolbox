$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
$trainerPath = Join-Path $projectRoot 'third_party\LostCastle2SoulStoneTrainer v1.2.exe'
$trainerSha256 = '025FB6CD01E79F9F2D8018BA9BF4FF592DE43EF2A7EDFD2E7A22F3C1842DF645'
if (-not (Test-Path -LiteralPath $trainerPath -PathType Leaf)) {
    throw 'Missing bundled third-party trainer source.'
}
if ((Get-Item -LiteralPath $trainerPath).Length -ne 72428059) {
    throw 'Bundled third-party trainer size mismatch.'
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $trainerPath).Hash -ne $trainerSha256) {
    throw 'Bundled third-party trainer SHA-256 mismatch.'
}

py -3 .\generate_icon.py
py -3 -m unittest discover -s .\tests -v
py -3 .\keyview.py --self-test
py -3 -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name '失落城堡2工具箱' `
    --icon '.\assets\keyview.ico' `
    --version-file '.\version_info.txt' `
    --collect-data 'rfc3987_syntax' `
    --add-data '.\assets\combat_sources.json;assets' `
    --add-data '.\assets\game_locations.json;assets' `
    --add-data '.\assets\mod_catalog.json;assets' `
    --add-data '.\contracts\combat_event.schema.json;contracts' `
    --add-data "$trainerPath;third_party" `
    '.\keyview.py'

$packageParent = Join-Path $projectRoot 'package'
$packageRoot = Join-Path $packageParent '失落城堡2工具箱 1.5.0'
if (Test-Path -LiteralPath $packageRoot) {
    $resolvedPackageRoot = (Resolve-Path -LiteralPath $packageRoot).Path
    $expectedPackageRoot = [System.IO.Path]::GetFullPath($packageRoot)
    if ($resolvedPackageRoot -ne $expectedPackageRoot -or
        [System.IO.Path]::GetDirectoryName($resolvedPackageRoot) -ne [System.IO.Path]::GetFullPath($packageParent)) {
        throw "Refusing to remove unexpected package path: $resolvedPackageRoot"
    }
    Remove-Item -LiteralPath $resolvedPackageRoot -Recurse -Force
}
$packageConfig = Join-Path $packageRoot 'config'
$packageModules = Join-Path $packageRoot 'modules'
$packageExports = Join-Path $packageRoot 'exports'
foreach ($directory in @($packageRoot, $packageConfig, $packageModules, $packageExports)) {
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
}
$runtimeRoot = Join-Path $projectRoot 'dist\失落城堡2工具箱'
Get-ChildItem -LiteralPath $runtimeRoot -Force | Copy-Item -Destination $packageRoot -Recurse -Force
Copy-Item -LiteralPath '.\package_assets\使用说明.txt' -Destination $packageRoot -Force
Copy-Item -LiteralPath '.\package_assets\modules.README.txt' -Destination (Join-Path $packageModules 'README.txt') -Force
Copy-Item -LiteralPath '.\package_assets\exports.README.txt' -Destination (Join-Path $packageExports 'README.txt') -Force

Write-Output $packageRoot
