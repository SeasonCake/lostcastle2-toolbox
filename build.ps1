$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
$trainerPath = Join-Path $projectRoot 'third_party\LostCastle2SoulStoneTrainer v1.2.exe'
$trainerSha256 = '025FB6CD01E79F9F2D8018BA9BF4FF592DE43EF2A7EDFD2E7A22F3C1842DF645'
$goldEditorPath = Join-Path $projectRoot 'third_party\LC2GoldFree.dll'
$goldEditorSha256 = 'BB6FF96AA4AF9BB3521ED93C3A5582E48D5D9CB8C7BAAF5291FA4C3E57647B56'
$communityModsPath = Join-Path $projectRoot 'third_party\community_mods'
$sevenZipPath = Join-Path $projectRoot 'third_party\7zip'
$sevenZipExeSha256 = '4CD7D776C686427226A151789D2D61F0B2ED2C392148CC4E69C0238362FAFECF'
$sevenZipDllSha256 = '5BD20FB38499D95C39594F41D4781B6181B3304B7F1F4D06B0182F514E7EAA74'
if (-not (Test-Path -LiteralPath $trainerPath -PathType Leaf)) {
    throw 'Missing bundled third-party trainer source.'
}
if ((Get-Item -LiteralPath $trainerPath).Length -ne 72428059) {
    throw 'Bundled third-party trainer size mismatch.'
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $trainerPath).Hash -ne $trainerSha256) {
    throw 'Bundled third-party trainer SHA-256 mismatch.'
}
if (-not (Test-Path -LiteralPath $goldEditorPath -PathType Leaf)) {
    throw 'Missing bundled gold editor source.'
}
if ((Get-Item -LiteralPath $goldEditorPath).Length -ne 9216) {
    throw 'Bundled gold editor size mismatch.'
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $goldEditorPath).Hash -ne $goldEditorSha256) {
    throw 'Bundled gold editor SHA-256 mismatch.'
}
if (-not (Test-Path -LiteralPath $communityModsPath -PathType Container)) {
    throw 'Missing prepared community MOD payloads.'
}
if (@(Get-ChildItem -LiteralPath $communityModsPath -File -Recurse).Count -ne 47) {
    throw 'Prepared community MOD payload file count mismatch.'
}
$sevenZipExe = Join-Path $sevenZipPath '7z.exe'
$sevenZipDll = Join-Path $sevenZipPath '7z.dll'
$sevenZipLicense = Join-Path $sevenZipPath 'License.txt'
if (-not (Test-Path -LiteralPath $sevenZipExe -PathType Leaf) -or
    -not (Test-Path -LiteralPath $sevenZipDll -PathType Leaf) -or
    -not (Test-Path -LiteralPath $sevenZipLicense -PathType Leaf)) {
    throw 'Missing bundled 7-Zip components.'
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $sevenZipExe).Hash -ne $sevenZipExeSha256 -or
    (Get-FileHash -Algorithm SHA256 -LiteralPath $sevenZipDll).Hash -ne $sevenZipDllSha256) {
    throw 'Bundled 7-Zip identity mismatch.'
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
    --add-data '.\assets\community_mod_catalog.json;assets' `
    --add-data '.\contracts\combat_event.schema.json;contracts' `
    --add-data "$trainerPath;third_party" `
    --add-data "$goldEditorPath;third_party" `
    --add-data "$communityModsPath;third_party/community_mods" `
    --add-data "$sevenZipPath;third_party/7zip" `
    '.\keyview.py'

$packageParent = Join-Path $projectRoot 'package'
$packageRoot = Join-Path $packageParent '失落城堡2工具箱 1.5.8'
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
$packageUserMods = Join-Path $packageRoot '用户MOD'
foreach ($directory in @($packageRoot, $packageConfig, $packageModules, $packageExports, $packageUserMods)) {
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
}
$runtimeRoot = Join-Path $projectRoot 'dist\失落城堡2工具箱'
Get-ChildItem -LiteralPath $runtimeRoot -Force | Copy-Item -Destination $packageRoot -Recurse -Force
Copy-Item -LiteralPath '.\package_assets\使用说明.txt' -Destination $packageRoot -Force
Copy-Item -LiteralPath '.\package_assets\MOD自动添加说明.txt' -Destination $packageRoot -Force
Copy-Item -LiteralPath '.\package_assets\用户MOD\请把MOD放到这里.txt' -Destination $packageUserMods -Force
Copy-Item -LiteralPath '.\package_assets\modules.README.txt' -Destination (Join-Path $packageModules 'README.txt') -Force
Copy-Item -LiteralPath '.\package_assets\exports.README.txt' -Destination (Join-Path $packageExports 'README.txt') -Force

Write-Output $packageRoot
