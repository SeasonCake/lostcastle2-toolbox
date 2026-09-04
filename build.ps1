param(
    [ValidateSet('Diagnostic', 'Distribution')]
    [string]$BuildProfile = 'Diagnostic',
    [string]$GameDir = '',
    [string]$DotNetPath = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
$trainerPath = Join-Path $projectRoot 'third_party\LostCastle2SoulStoneTrainer v1.2.exe'
$trainerSha256 = '025FB6CD01E79F9F2D8018BA9BF4FF592DE43EF2A7EDFD2E7A22F3C1842DF645'
$goldEditorPath = Join-Path $projectRoot 'third_party\LC2GoldFree.dll'
$goldEditorSha256 = 'BB6FF96AA4AF9BB3521ED93C3A5582E48D5D9CB8C7BAAF5291FA4C3E57647B56'
$communityModsPath = Join-Path $projectRoot 'third_party\community_mods'
$runtimeBundlePath = Join-Path $projectRoot 'third_party\lc2_runtime'
$runtimeManifestPath = Join-Path $projectRoot 'assets\lc2_runtime_manifest.json'
$runtimeNoticesPath = Join-Path $projectRoot 'package_assets\运行环境'
$supportAssetsPath = Join-Path $projectRoot 'package_assets\赞助与投喂'
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
if (@(Get-ChildItem -LiteralPath $communityModsPath -File -Recurse).Count -ne 61) {
    throw 'Prepared community MOD payload file count mismatch.'
}
$runtimeManifest = Get-Content -LiteralPath $runtimeManifestPath -Raw | ConvertFrom-Json
$runtimeArchivePath = Join-Path $runtimeBundlePath $runtimeManifest.runtime_archive.filename
$runtimeBridgePath = Join-Path $runtimeBundlePath $runtimeManifest.bridge.filename
if (-not (Test-Path -LiteralPath $runtimeArchivePath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $runtimeBridgePath -PathType Leaf)) {
    throw 'Missing prepared LC2 HUD/MOD runtime bundle.'
}
if ((Get-Item -LiteralPath $runtimeArchivePath).Length -ne [long]$runtimeManifest.runtime_archive.size_bytes -or
    (Get-FileHash -Algorithm SHA256 -LiteralPath $runtimeArchivePath).Hash -ne $runtimeManifest.runtime_archive.sha256) {
    throw 'Prepared BepInEx runtime archive identity mismatch.'
}
if ((Get-Item -LiteralPath $runtimeBridgePath).Length -ne [long]$runtimeManifest.bridge.size_bytes -or
    (Get-FileHash -Algorithm SHA256 -LiteralPath $runtimeBridgePath).Hash -ne $runtimeManifest.bridge.sha256) {
    throw 'Prepared LC2 Combat Bridge identity mismatch.'
}
if ([int]$runtimeManifest.runtime_file_count -ne 307 -or
    @($runtimeManifest.runtime_files).Count -ne 307) {
    throw 'Prepared BepInEx runtime member count mismatch.'
}
if (-not (Test-Path -LiteralPath (Join-Path $runtimeNoticesPath 'BepInEx-LICENSE.txt') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $runtimeNoticesPath 'README.txt') -PathType Leaf)) {
    throw 'Missing BepInEx runtime notices.'
}
$supportAssetHashes = @{
    '支付宝赞助码.png' = 'F29F4D1E311B0F0723A73C66E7ED49EB1A2C84953963E6AA1159D4E9FE33CABD'
    '微信赞助码.jpg' = 'BF866A996CD110E75CB1D490BEBF270DB05F37F4669892913EDDA2F2D10B1A4C'
    '微信赞助码.png' = 'DF613B6822443E081A2F4376B6DFA01DF11DC9318A55E6EA8A68D23C5EFBFFF4'
    '猫猫1.jpg' = 'F9DBD1606686D054B5CFFA1063E174C715E3B7536654DB41E212019E86ECC04C'
    '猫猫2.jpg' = '0F9C600CF4D2399EBA82179BD2D7EF6631BBF9E9A61344C43BE3819A200169AA'
}
if (-not (Test-Path -LiteralPath $supportAssetsPath -PathType Container) -or
    @(Get-ChildItem -LiteralPath $supportAssetsPath -File).Count -ne 6) {
    throw 'Sponsorship asset set is incomplete.'
}
foreach ($entry in $supportAssetHashes.GetEnumerator()) {
    $assetPath = Join-Path $supportAssetsPath $entry.Key
    if (-not (Test-Path -LiteralPath $assetPath -PathType Leaf) -or
        (Get-FileHash -Algorithm SHA256 -LiteralPath $assetPath).Hash -ne $entry.Value) {
        throw "Sponsorship asset identity mismatch: $($entry.Key)"
    }
}
$supportReadme = Join-Path $supportAssetsPath '赞助说明.txt'
if (-not (Test-Path -LiteralPath $supportReadme -PathType Leaf)) {
    throw 'Missing free sponsorship explanation.'
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
if ($LASTEXITCODE -ne 0) {
    throw "Icon generation failed with exit code $LASTEXITCODE."
}
$excludedReleaseTests = @(
    'test_prepare_lc2_public_catalog.py',
    'test_prepare_lc2_public_runtime.py',
    'test_public_build.py'
)
$releaseTestModules = Get-ChildItem -LiteralPath '.\tests' -File -Filter 'test_*.py' |
    Where-Object { $_.Name -notin $excludedReleaseTests } |
    Sort-Object Name |
    ForEach-Object { 'tests.' + $_.BaseName }
py -3 -m unittest @releaseTestModules -v
if ($LASTEXITCODE -ne 0) {
    throw "Test suite failed with exit code $LASTEXITCODE."
}
py -3 .\keyview.py --self-test
if ($LASTEXITCODE -ne 0) {
    throw "Source self-test failed with exit code $LASTEXITCODE."
}
$profileId = $BuildProfile.ToLowerInvariant()
$profileDefinition = Join-Path $projectRoot "assets\build_profiles\$profileId\build_profile.json"
if (-not (Test-Path -LiteralPath $profileDefinition -PathType Leaf)) {
    throw "Build profile definition is missing: $BuildProfile"
}
$profilePayload = Get-Content -LiteralPath $profileDefinition -Raw | ConvertFrom-Json
$diagnosticsExpected = $BuildProfile -eq 'Diagnostic'
$profileBooleanFields = @(
    'combat_diagnostics_available',
    'bridge_diagnostics_enabled',
    'default_recording_enabled'
)
foreach ($fieldName in $profileBooleanFields) {
    $fieldProperty = $profilePayload.PSObject.Properties[$fieldName]
    if ($null -eq $fieldProperty -or $fieldProperty.Value -isnot [bool]) {
        throw "Build profile boolean field is invalid: $BuildProfile/$fieldName"
    }
}
if ([int]$profilePayload.schema_version -ne 1 -or
    $profilePayload.profile_id -ne $profileId -or
    $profilePayload.combat_diagnostics_available -ne $diagnosticsExpected -or
    $profilePayload.bridge_diagnostics_enabled -ne $diagnosticsExpected -or
    $profilePayload.default_recording_enabled -ne $diagnosticsExpected) {
    throw "Build profile definition is inconsistent: $BuildProfile"
}

$resolvedDotNetPath = $DotNetPath
if ([string]::IsNullOrWhiteSpace($resolvedDotNetPath)) {
    $bundledDotNet = Join-Path $projectRoot 'artifacts\toolchains\dotnet-sdk-6.0.428\dotnet.exe'
    if (Test-Path -LiteralPath $bundledDotNet -PathType Leaf) {
        $resolvedDotNetPath = $bundledDotNet
    } else {
        $dotnetCommand = Get-Command dotnet -ErrorAction SilentlyContinue
        if ($null -ne $dotnetCommand) {
            $resolvedDotNetPath = $dotnetCommand.Source
        }
    }
}
if ([string]::IsNullOrWhiteSpace($resolvedDotNetPath) -or
    -not (Test-Path -LiteralPath $resolvedDotNetPath -PathType Leaf) -or
    -not @(& $resolvedDotNetPath --list-sdks)) {
    throw 'A .NET 6 SDK is required to build the selected Bridge profile.'
}

$resolvedGameDir = $GameDir
if ([string]::IsNullOrWhiteSpace($resolvedGameDir)) {
    $resolvedGameDir = $env:LC2_GAME_DIR
}
if ([string]::IsNullOrWhiteSpace($resolvedGameDir)) {
    $localSettingsPath = Join-Path $projectRoot 'config\settings.json'
    if (Test-Path -LiteralPath $localSettingsPath -PathType Leaf) {
        $localSettings = Get-Content -LiteralPath $localSettingsPath -Raw | ConvertFrom-Json
        $resolvedGameDir = [string]$localSettings.game_path
    }
}
if (-not [string]::IsNullOrWhiteSpace($resolvedGameDir) -and
    [System.IO.Path]::GetExtension($resolvedGameDir)) {
    $resolvedGameDir = Split-Path -Parent $resolvedGameDir
}
if ([string]::IsNullOrWhiteSpace($resolvedGameDir) -or
    -not (Test-Path -LiteralPath (Join-Path $resolvedGameDir 'BepInEx\core\BepInEx.Core.dll') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $resolvedGameDir 'BepInEx\interop\LC2.Core.dll') -PathType Leaf)) {
    throw 'A validated Lost Castle 2 BepInEx/interop directory is required to build Bridge.'
}

$profileStageParent = Join-Path $projectRoot 'build\profile-stage'
$profileStageRoot = Join-Path $profileStageParent $profileId
if (Test-Path -LiteralPath $profileStageRoot) {
    $resolvedStageRoot = (Resolve-Path -LiteralPath $profileStageRoot).Path
    if ([System.IO.Path]::GetDirectoryName($resolvedStageRoot) -ne
        [System.IO.Path]::GetFullPath($profileStageParent)) {
        throw "Refusing to remove unexpected profile stage: $resolvedStageRoot"
    }
    Remove-Item -LiteralPath $resolvedStageRoot -Recurse -Force
}
$stagedAssetsPath = Join-Path $profileStageRoot 'assets'
$stagedRuntimeBundlePath = Join-Path $profileStageRoot 'third_party\lc2_runtime'
$stagedBridgeOutput = Join-Path $profileStageRoot 'bridge'
foreach ($directory in @($stagedAssetsPath, $stagedRuntimeBundlePath, $stagedBridgeOutput)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
$bridgeDiagnostics = if ($diagnosticsExpected) { 'true' } else { 'false' }
& $resolvedDotNetPath build '.\game_plugins\LC2CombatBridge\LC2CombatBridge.csproj' `
    -t:Rebuild `
    -c Release `
    "-p:GameDir=$resolvedGameDir" `
    "-p:CombatDiagnostics=$bridgeDiagnostics" `
    --output $stagedBridgeOutput `
    --nologo
if ($LASTEXITCODE -ne 0) {
    throw "Bridge $BuildProfile build failed with exit code $LASTEXITCODE."
}
$stagedBridgeSource = Join-Path $stagedBridgeOutput 'LC2CombatBridge.dll'
py -3 .\tools\verify_lc2_bridge_profile.py `
    --bridge $stagedBridgeSource `
    --profile $profileId
if ($LASTEXITCODE -ne 0) {
    throw "Bridge $BuildProfile profile verification failed with exit code $LASTEXITCODE."
}

Copy-Item -LiteralPath $runtimeArchivePath -Destination $stagedRuntimeBundlePath
$stagedBridgePath = Join-Path $stagedRuntimeBundlePath 'LC2CombatBridge.dll'
Copy-Item -LiteralPath $stagedBridgeSource -Destination $stagedBridgePath
$stagedManifest = Get-Content -LiteralPath $runtimeManifestPath -Raw | ConvertFrom-Json
$stagedManifest.runtime_version = 'BepInEx 6.0.0-be.785 + LC2CombatBridge 1.7.4'
$stagedManifest.bridge.size_bytes = (Get-Item -LiteralPath $stagedBridgePath).Length
$stagedManifest.bridge.sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $stagedBridgePath).Hash
$stagedManifest | Add-Member -NotePropertyName build_profile -NotePropertyValue $profileId
$stagedManifest.bridge | Add-Member `
    -NotePropertyName diagnostics_enabled `
    -NotePropertyValue $diagnosticsExpected
$stagedManifestPath = Join-Path $stagedAssetsPath 'lc2_runtime_manifest.json'
$stagedManifest | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $stagedManifestPath -Encoding utf8
$stagedProfilePath = Join-Path $stagedAssetsPath 'build_profile.json'
Copy-Item -LiteralPath $profileDefinition -Destination $stagedProfilePath

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
    --add-data "$stagedManifestPath;assets" `
    --add-data '.\assets\keyview.ico;assets' `
    --add-data "$stagedProfilePath;assets" `
    --add-data '.\contracts\combat_event.schema.json;contracts' `
    --add-data "$trainerPath;third_party" `
    --add-data "$goldEditorPath;third_party" `
    --add-data "$communityModsPath;third_party/community_mods" `
    --add-data "$stagedRuntimeBundlePath;third_party/lc2_runtime" `
    --add-data "$sevenZipPath;third_party/7zip" `
    '.\keyview.py'
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$packageParent = Join-Path $projectRoot 'package'
$packageName = if ($BuildProfile -eq 'Diagnostic') {
    '失落城堡2工具箱1.7.6-诊断候选-r1'
} else {
    '失落城堡2工具箱1.7.6-实时数值监测+一键MOD安装'
}
$packageRoot = Join-Path $packageParent $packageName
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
$packageUserMods = Join-Path $packageRoot '用户MOD'
$packageSupport = Join-Path $packageRoot '赞助与投喂'
$packageRuntimeNotices = Join-Path $packageRoot '运行环境'
foreach ($directory in @($packageRoot, $packageConfig, $packageModules, $packageUserMods, $packageSupport, $packageRuntimeNotices)) {
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
}
$runtimeRoot = Join-Path $projectRoot 'dist\失落城堡2工具箱'
Get-ChildItem -LiteralPath $runtimeRoot -Force | Copy-Item -Destination $packageRoot -Recurse -Force
Copy-Item -LiteralPath '.\package_assets\使用说明.txt' -Destination $packageRoot -Force
Copy-Item -LiteralPath '.\package_assets\MOD自动添加说明.txt' -Destination $packageRoot -Force
Copy-Item -LiteralPath '.\LICENSE' -Destination $packageRoot -Force
Copy-Item -LiteralPath '.\THIRD_PARTY_NOTICES.md' -Destination $packageRoot -Force
Copy-Item -LiteralPath '.\package_assets\用户MOD\请把MOD放到这里.txt' -Destination $packageUserMods -Force
Copy-Item -LiteralPath '.\package_assets\modules.README.txt' -Destination (Join-Path $packageModules 'README.txt') -Force
Get-ChildItem -LiteralPath $supportAssetsPath -File | Copy-Item -Destination $packageSupport -Force
Get-ChildItem -LiteralPath $runtimeNoticesPath -File | Copy-Item -Destination $packageRuntimeNotices -Force
if (-not (Test-Path -LiteralPath (Join-Path $packageRoot 'LICENSE') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $packageRoot 'THIRD_PARTY_NOTICES.md') -PathType Leaf)) {
    throw 'Packaged license or third-party notices are missing.'
}
py -3 .\tools\verify_packaged_runtime.py --package $packageRoot
if ($LASTEXITCODE -ne 0) {
    throw "Packaged runtime/profile verification failed with exit code $LASTEXITCODE."
}

Write-Output $packageRoot
