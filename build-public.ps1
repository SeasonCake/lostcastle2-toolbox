[CmdletBinding()]
param(
    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

$packageName = '失落城堡2工具箱1.7.6-public-core'
$appName = '失落城堡2工具箱'
$publicBuildParent = Join-Path $projectRoot 'build'
$publicBuildRoot = Join-Path $publicBuildParent 'public-core'
$publicDistParent = Join-Path $projectRoot 'dist'
$publicDistRoot = Join-Path $publicDistParent 'public-core'
$publicPackageParent = Join-Path $projectRoot 'package\public-core'
$publicPackageRoot = Join-Path $publicPackageParent $packageName
$publicStageAssets = Join-Path $publicBuildRoot 'staging\assets'

$publicModCatalogPath = Join-Path $projectRoot 'assets\mod_catalog.public.json'
$publicCommunityCatalogPath = Join-Path $projectRoot 'assets\community_mod_catalog.public.json'
$publicRuntimeManifestPath = Join-Path $projectRoot 'assets\lc2_public_runtime_manifest.json'
$publicProfilePath = Join-Path $projectRoot 'assets\build_profiles\distribution\build_profile.json'
$publicRuntimeSource = Join-Path $projectRoot 'third_party\lc2_public_runtime'
$sevenZipSource = Join-Path $projectRoot 'third_party\7zip'
$supportAssetsSource = Join-Path $projectRoot 'package_assets\赞助与投喂'
$publicRuntimeNoticesSource = Join-Path $projectRoot 'package_assets\运行环境\public-core'

$expectedPublicModCatalogSha256 = '879388326B33DCCE722DCC4E4FD76802DC5628787713ED51D6EAA0999E12BE0C'
$expectedPublicCommunityCatalogSha256 = '5840BFBC0891F779F47E2FE06BA93FE6A4D6E59C5D89F22F0DF849C530A260CA'
$expectedPublicRuntimeManifestSha256 = '5265F0D56DA5CF6979BA937AE3FD683A2277B69648D0821C91240AA3CF1549BB'
$expectedOfficialRuntimeSha256 = '2A7CBF74D26ABE4765C3E662DB1721B923BAC39849EBFEF2CA5DC7DE7E2D9B7F'
$expectedOfficialRuntimeSize = 34335572L
$expectedOfficialRuntimeMemberCount = 228
$expectedOfficialRuntimeUncompressedBytes = 75665788L
$expectedOfficialRuntimeUrl = 'https://builds.bepinex.dev/projects/bepinex_be/785/BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.785+6abdba4.zip'
$expectedOfficialRuntimeFilename = 'BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.785+6abdba4.zip'
$expectedBridgeSha256 = '190B8B4A8C661C73A32ADF15DF56487E57473E591BFA25520D172A7E188E7DED'
$expectedBridgeSize = 102400L
$expectedSevenZipExeSha256 = '4CD7D776C686427226A151789D2D61F0B2ED2C392148CC4E69C0238362FAFECF'
$expectedSevenZipDllSha256 = '5BD20FB38499D95C39594F41D4781B6181B3304B7F1F4D06B0182F514E7EAA74'
$legacyPreparedRuntimeSha256 = '0B617BC439F53E39680444F1EFD84C2B31A96D144D3267EE06EBEA05B59738A8'
$trainerSha256 = '025FB6CD01E79F9F2D8018BA9BF4FF592DE43EF2A7EDFD2E7A22F3C1842DF645'
$goldEditorSha256 = 'BB6FF96AA4AF9BB3521ED93C3A5582E48D5D9CB8C7BAAF5291FA4C3E57647B56'

function Assert-Condition {
    param(
        [Parameter(Mandatory = $true)]
        [bool]$Condition,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Assert-LeafFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )
    Assert-Condition (Test-Path -LiteralPath $Path -PathType Leaf) "Missing ${Label}: $Path"
}

function Get-UpperSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Assert-FileIdentity {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][long]$SizeBytes,
        [Parameter(Mandatory = $true)][string]$Sha256,
        [Parameter(Mandatory = $true)][string]$Label
    )
    Assert-LeafFile $Path $Label
    $item = Get-Item -LiteralPath $Path
    Assert-Condition ($item.Length -eq $SizeBytes) "$Label size mismatch."
    Assert-Condition ((Get-UpperSha256 $Path) -eq $Sha256.ToUpperInvariant()) "$Label SHA-256 mismatch."
}

function Read-JsonObject {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )
    Assert-LeafFile $Path $Label
    try {
        $payload = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        throw "$Label is not valid JSON: $($_.Exception.Message)"
    }
    Assert-Condition ($null -ne $payload) "$Label is empty."
    return $payload
}

function Assert-NoUnsafeRelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $normalized = $Value.Replace('\', '/')
    $segments = @($normalized.Split('/'))
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($normalized)) "$Label is empty."
    Assert-Condition (-not $normalized.StartsWith('/')) "$Label is absolute."
    Assert-Condition (-not $normalized.EndsWith('/')) "$Label has an empty final segment."
    Assert-Condition (-not ($normalized -match '^[A-Za-z]:')) "$Label has a drive prefix."
    Assert-Condition (-not ($segments -contains '')) "$Label has an empty path segment."
    Assert-Condition (-not ($segments -contains '.')) "$Label contains a current-directory segment."
    Assert-Condition (-not ($segments -contains '..')) "$Label traverses outside its root."
    Assert-Condition (@($segments | Where-Object { $_ -match ':' }).Count -eq 0) "$Label contains a drive-qualified segment."
}

function Get-CatalogIds {
    param([Parameter(Mandatory = $true)]$Catalog)
    return @($Catalog.entries | ForEach-Object { [string]$_.id } | Sort-Object)
}

function Assert-PublicCatalog {
    param(
        [Parameter(Mandatory = $true)][string]$PublicPath,
        [Parameter(Mandatory = $true)][string]$RegularPath,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256,
        [Parameter(Mandatory = $true)][int]$ExpectedEntryCount,
        [Parameter(Mandatory = $true)][string]$Label
    )
    Assert-LeafFile $PublicPath $Label
    Assert-Condition ((Get-UpperSha256 $PublicPath) -eq $ExpectedSha256) "$Label frozen SHA-256 mismatch."
    $publicCatalog = Read-JsonObject $PublicPath $Label
    $regularCatalog = Read-JsonObject $RegularPath "regular source for $Label"
    Assert-Condition ([int]$publicCatalog.schema_version -eq 2) "$Label schema must be 2."
    $entries = @($publicCatalog.entries)
    Assert-Condition ($entries.Count -eq $ExpectedEntryCount) "$Label entry count mismatch."
    $ids = @(Get-CatalogIds $publicCatalog)
    Assert-Condition (@($ids | Select-Object -Unique).Count -eq $ids.Count) "$Label contains duplicate ids."
    $regularIds = @(Get-CatalogIds $regularCatalog)
    Assert-Condition (@(Compare-Object -ReferenceObject $regularIds -DifferenceObject $ids).Count -eq 0) "$Label ids differ from the source catalog."
    foreach ($entry in $entries) {
        Assert-Condition ($null -ne $entry.operation) "$Label entry '$($entry.id)' has no operation."
        $operationProperties = @($entry.operation.PSObject.Properties.Name)
        Assert-Condition ($operationProperties -contains 'bundled') "$Label entry '$($entry.id)' omits bundled."
        Assert-Condition ($entry.operation.bundled -eq $false) "$Label entry '$($entry.id)' is still bundled."
        Assert-Condition (-not ($operationProperties -contains 'bundle_dir')) "$Label entry '$($entry.id)' still has bundle_dir."
        $entryJson = $entry | ConvertTo-Json -Depth 100 -Compress
        Assert-Condition (-not ($entryJson -match '(?i)third_party[/\\]')) "$Label entry '$($entry.id)' references third_party."
        Assert-Condition ([string]$entry.integrity_policy.redistribution_status -eq 'public_core_user_supplied_required') "$Label entry '$($entry.id)' lacks the public-core redistribution boundary."
        Assert-Condition ($entry.integrity_policy.PSObject.Properties.Name -contains 'source_redistribution_status') "$Label entry '$($entry.id)' lost its source redistribution record."
        foreach ($fileField in @('files', 'superseded_files')) {
            if ($operationProperties -contains $fileField) {
                foreach ($file in @($entry.operation.$fileField)) {
                    Assert-NoUnsafeRelativePath ([string]$file.path) "$Label entry '$($entry.id)' $fileField path"
                    Assert-Condition ([long]$file.size_bytes -gt 0) "$Label entry '$($entry.id)' has an invalid $fileField size."
                    Assert-Condition ([string]$file.sha256 -match '^[0-9A-Fa-f]{64}$') "$Label entry '$($entry.id)' has an invalid $fileField SHA-256."
                }
            }
        }
    }
    return $publicCatalog
}

function Get-StreamSha256 {
    param([Parameter(Mandatory = $true)][System.IO.Stream]$Stream)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $algorithm.ComputeHash($Stream)
        return (-join ($bytes | ForEach-Object { $_.ToString('X2') }))
    }
    finally {
        $algorithm.Dispose()
    }
}

function Assert-PublicRuntime {
    param([Parameter(Mandatory = $true)][string]$ManifestPath)
    Assert-Condition ((Get-UpperSha256 $ManifestPath) -eq $expectedPublicRuntimeManifestSha256) 'Public runtime manifest frozen SHA-256 mismatch.'
    $manifest = Read-JsonObject $ManifestPath 'public runtime manifest'
    Assert-Condition ([int]$manifest.schema_version -eq 1) 'Public runtime manifest schema must be 1.'
    Assert-Condition ([string]$manifest.build_profile -ceq 'distribution') 'Public runtime build profile must be distribution.'
    Assert-Condition ([string]$manifest.source_identity.kind -eq 'official_bepinex_build') 'Public runtime source is not marked as an official BepInEx build.'
    Assert-Condition ([string]$manifest.source_identity.project -eq 'bepinex_be') 'Public runtime project identity mismatch.'
    Assert-Condition ([int]$manifest.source_identity.build -eq 785) 'Public runtime build identity mismatch.'
    Assert-Condition ([string]$manifest.source_identity.version -eq '6.0.0-be.785+6abdba4') 'Public runtime version identity mismatch.'
    Assert-Condition ([string]$manifest.source_identity.url -ceq $expectedOfficialRuntimeUrl) 'Public runtime official source URL mismatch.'
    Assert-Condition ([string]$manifest.source_identity.filename -ceq $expectedOfficialRuntimeFilename) 'Public runtime official filename mismatch.'
    Assert-Condition ([long]$manifest.source_identity.size_bytes -eq $expectedOfficialRuntimeSize) 'Public runtime source size mismatch.'
    Assert-Condition ([string]$manifest.source_identity.sha256 -ceq $expectedOfficialRuntimeSha256) 'Public runtime source SHA-256 mismatch.'
    Assert-Condition ([string]$manifest.runtime_archive.filename -ceq 'bepinex-runtime.zip') 'Public runtime bundle filename mismatch.'
    Assert-Condition ([long]$manifest.runtime_archive.size_bytes -eq $expectedOfficialRuntimeSize) 'Public runtime archive size mismatch.'
    Assert-Condition ([string]$manifest.runtime_archive.sha256 -ceq $expectedOfficialRuntimeSha256) 'Public runtime archive SHA-256 mismatch.'
    Assert-Condition ([int]$manifest.runtime_file_count -eq $expectedOfficialRuntimeMemberCount) 'Public runtime member count declaration mismatch.'
    Assert-Condition ([long]$manifest.runtime_uncompressed_bytes -eq $expectedOfficialRuntimeUncompressedBytes) 'Public runtime uncompressed byte count mismatch.'

    Assert-Condition ([string]$manifest.configuration.path -ceq 'BepInEx/config/BepInEx.cfg') 'Public runtime fresh configuration path mismatch.'
    Assert-Condition ($manifest.configuration.fresh_console_enabled -eq $false) 'Public runtime fresh console policy must be disabled.'
    Assert-Condition ([string]$manifest.configuration.fresh_unity_base_libraries_source -ceq 'https://unity.bepinex.dev/libraries/{VERSION}.zip') 'Public runtime Unity library source template mismatch.'
    Assert-Condition ([string]$manifest.bridge.filename -ceq 'LC2CombatBridge.dll') 'Public Bridge filename mismatch.'
    Assert-Condition ([string]$manifest.bridge.target -ceq 'BepInEx/plugins/LC2CombatBridge/LC2CombatBridge.dll') 'Public Bridge target mismatch.'
    Assert-Condition ([long]$manifest.bridge.size_bytes -eq $expectedBridgeSize) 'Public Bridge manifest size mismatch.'
    Assert-Condition ([string]$manifest.bridge.sha256 -ceq $expectedBridgeSha256) 'Public Bridge manifest SHA-256 mismatch.'
    Assert-Condition ($manifest.bridge.diagnostics_enabled -eq $false) 'Public Bridge diagnostics must be disabled.'

    $expectedRequired = @(
        '.doorstop_version',
        'doorstop_config.ini',
        'winhttp.dll',
        'BepInEx/core/BepInEx.Core.dll',
        'BepInEx/core/BepInEx.Unity.IL2CPP.dll',
        'dotnet/coreclr.dll'
    ) | Sort-Object
    $actualRequired = @($manifest.required_paths | ForEach-Object { [string]$_ } | Sort-Object)
    Assert-Condition (@(Compare-Object -ReferenceObject $expectedRequired -DifferenceObject $actualRequired).Count -eq 0) 'Public runtime required path set mismatch.'

    $specs = @($manifest.runtime_files)
    Assert-Condition ($specs.Count -eq $expectedOfficialRuntimeMemberCount) 'Public runtime file specification count mismatch.'
    $specByPath = @{}
    $declaredBytes = 0L
    foreach ($spec in $specs) {
        $relative = [string]$spec.path
        Assert-NoUnsafeRelativePath $relative 'public runtime member path'
        $folded = $relative.Replace('\', '/').ToLowerInvariant()
        Assert-Condition (-not $specByPath.ContainsKey($folded)) "Duplicate public runtime member: $relative"
        Assert-Condition ([long]$spec.size_bytes -gt 0) "Invalid public runtime member size: $relative"
        Assert-Condition ([string]$spec.sha256 -match '^[0-9A-F]{64}$') "Invalid public runtime member SHA-256: $relative"
        Assert-Condition (-not ($folded.StartsWith('bepinex/plugins/') -or $folded.StartsWith('bepinex/cache/') -or $folded.StartsWith('bepinex/interop/') -or $folded.StartsWith('bepinex/unity-libs/') -or $folded.StartsWith('bepinex/config/'))) "Forbidden generated/runtime-local member in official archive: $relative"
        $specByPath[$folded] = $spec
        $declaredBytes += [long]$spec.size_bytes
    }
    Assert-Condition ($declaredBytes -eq $expectedOfficialRuntimeUncompressedBytes) 'Public runtime file specs do not sum to the declared byte count.'

    Assert-Condition (Test-Path -LiteralPath $publicRuntimeSource -PathType Container) 'Missing public runtime source directory.'
    $sourceFiles = @(Get-ChildItem -LiteralPath $publicRuntimeSource -File -Recurse -Force)
    $expectedSourceNames = @('bepinex-runtime.zip', 'LC2CombatBridge.dll') | Sort-Object
    $actualSourceNames = @($sourceFiles | ForEach-Object { $_.FullName.Substring($publicRuntimeSource.Length).TrimStart('\', '/').Replace('\', '/') } | Sort-Object)
    Assert-Condition (@(Compare-Object -ReferenceObject $expectedSourceNames -DifferenceObject $actualSourceNames).Count -eq 0) 'Public runtime source must contain exactly the official ZIP and LC2 Combat Bridge.'
    $runtimeArchivePath = Join-Path $publicRuntimeSource 'bepinex-runtime.zip'
    $bridgePath = Join-Path $publicRuntimeSource 'LC2CombatBridge.dll'
    Assert-FileIdentity $runtimeArchivePath $expectedOfficialRuntimeSize $expectedOfficialRuntimeSha256 'official BepInEx archive'
    Assert-FileIdentity $bridgePath $expectedBridgeSize $expectedBridgeSha256 'LC2 Combat Bridge'

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($runtimeArchivePath)
    try {
        $archiveFiles = @($archive.Entries | Where-Object { -not [string]::IsNullOrEmpty($_.Name) })
        Assert-Condition ($archiveFiles.Count -eq $expectedOfficialRuntimeMemberCount) 'Official BepInEx ZIP member count mismatch.'
        $seen = @{}
        $actualBytes = 0L
        foreach ($entry in $archiveFiles) {
            $relative = $entry.FullName.Replace('\', '/')
            Assert-NoUnsafeRelativePath $relative 'official BepInEx ZIP member'
            $folded = $relative.ToLowerInvariant()
            Assert-Condition (-not $seen.ContainsKey($folded)) "Duplicate official BepInEx ZIP member: $relative"
            Assert-Condition ($specByPath.ContainsKey($folded)) "Official BepInEx ZIP member is not in the manifest: $relative"
            $spec = $specByPath[$folded]
            Assert-Condition ([long]$entry.Length -eq [long]$spec.size_bytes) "Official BepInEx ZIP member size mismatch: $relative"
            $stream = $entry.Open()
            try {
                $entrySha256 = Get-StreamSha256 $stream
            }
            finally {
                $stream.Dispose()
            }
            Assert-Condition ($entrySha256 -eq [string]$spec.sha256) "Official BepInEx ZIP member SHA-256 mismatch: $relative"
            $seen[$folded] = $true
            $actualBytes += [long]$entry.Length
        }
        Assert-Condition ($actualBytes -eq $expectedOfficialRuntimeUncompressedBytes) 'Official BepInEx ZIP uncompressed byte count mismatch.'
    }
    finally {
        $archive.Dispose()
    }
    return $manifest
}

function Assert-SevenZipAndPackageAssets {
    $sevenZipExe = Join-Path $sevenZipSource '7z.exe'
    $sevenZipDll = Join-Path $sevenZipSource '7z.dll'
    $sevenZipLicense = Join-Path $sevenZipSource 'License.txt'
    Assert-FileIdentity $sevenZipExe 575488L $expectedSevenZipExeSha256 '7-Zip executable'
    Assert-FileIdentity $sevenZipDll 1906176L $expectedSevenZipDllSha256 '7-Zip library'
    Assert-LeafFile $sevenZipLicense 'complete 7-Zip license'
    Assert-Condition ((Get-Item -LiteralPath $sevenZipLicense).Length -gt 1000) '7-Zip license is unexpectedly short.'
    $sevenZipFiles = @(Get-ChildItem -LiteralPath $sevenZipSource -File -Recurse -Force)
    Assert-Condition ($sevenZipFiles.Count -eq 3) '7-Zip source must contain exactly 7z.exe, 7z.dll and License.txt.'

    $supportAssetHashes = @{
        '支付宝赞助码.png' = 'F29F4D1E311B0F0723A73C66E7ED49EB1A2C84953963E6AA1159D4E9FE33CABD'
        '微信赞助码.jpg' = 'BF866A996CD110E75CB1D490BEBF270DB05F37F4669892913EDDA2F2D10B1A4C'
        '微信赞助码.png' = 'DF613B6822443E081A2F4376B6DFA01DF11DC9318A55E6EA8A68D23C5EFBFFF4'
        '猫猫1.jpg' = 'F9DBD1606686D054B5CFFA1063E174C715E3B7536654DB41E212019E86ECC04C'
        '猫猫2.jpg' = '0F9C600CF4D2399EBA82179BD2D7EF6631BBF9E9A61344C43BE3819A200169AA'
    }
    Assert-Condition (Test-Path -LiteralPath $supportAssetsSource -PathType Container) 'Missing sponsorship asset directory.'
    Assert-Condition (@(Get-ChildItem -LiteralPath $supportAssetsSource -File -Force).Count -eq 6) 'Sponsorship asset set is incomplete.'
    foreach ($entry in $supportAssetHashes.GetEnumerator()) {
        $assetPath = Join-Path $supportAssetsSource $entry.Key
        Assert-LeafFile $assetPath "sponsorship asset $($entry.Key)"
        Assert-Condition ((Get-UpperSha256 $assetPath) -eq $entry.Value) "Sponsorship asset identity mismatch: $($entry.Key)"
    }
    Assert-LeafFile (Join-Path $supportAssetsSource '赞助说明.txt') 'sponsorship explanation'

    $requiredRuntimeNoticeNames = @(
        'BepInEx-LICENSE.txt',
        'Dobby-LICENSE.txt',
        'Dotnet-Runtime-LICENSE.txt',
        'Dotnet-Runtime-PATENTS.txt',
        'Dotnet-Runtime-THIRD-PARTY-NOTICES.txt',
        'README.txt',
        'UnityDoorstop-LICENSE.txt'
    ) | Sort-Object
    Assert-Condition (Test-Path -LiteralPath $publicRuntimeNoticesSource -PathType Container) 'Missing public-core runtime notice directory.'
    $actualRuntimeNoticeNames = @(Get-ChildItem -LiteralPath $publicRuntimeNoticesSource -File -Force | ForEach-Object { $_.Name } | Sort-Object)
    Assert-Condition (@(Compare-Object -ReferenceObject $requiredRuntimeNoticeNames -DifferenceObject $actualRuntimeNoticeNames).Count -eq 0) 'Public-core runtime license/notice set mismatch.'
    foreach ($noticeName in $requiredRuntimeNoticeNames) {
        Assert-Condition ((Get-Item -LiteralPath (Join-Path $publicRuntimeNoticesSource $noticeName)).Length -gt 100) "Public-core runtime notice is unexpectedly short: $noticeName"
    }
    Assert-LeafFile (Join-Path $projectRoot 'LICENSE') 'project license'
    Assert-LeafFile (Join-Path $projectRoot 'PUBLIC_CORE_THIRD_PARTY_NOTICES.md') 'public-core third-party notices'
    Assert-LeafFile (Join-Path $projectRoot 'package_assets\public-core.README.txt') 'public-core usage guide'
}

function Remove-ExactGeneratedRoot {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$ExpectedParent
    )
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
    $fullParent = [System.IO.Path]::GetFullPath($ExpectedParent).TrimEnd('\')
    Assert-Condition ([System.IO.Path]::GetDirectoryName($fullPath) -eq $fullParent) "Refusing to clean unexpected generated path: $fullPath"
    Assert-Condition ($fullPath.StartsWith(([System.IO.Path]::GetFullPath($projectRoot).TrimEnd('\') + '\'), [System.StringComparison]::OrdinalIgnoreCase)) "Generated path escapes project root: $fullPath"
    if (Test-Path -LiteralPath $fullPath) {
        $resolved = (Resolve-Path -LiteralPath $fullPath).Path.TrimEnd('\')
        Assert-Condition ($resolved -eq $fullPath) "Generated path resolves unexpectedly: $resolved"
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

function Invoke-PythonChecked {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Label
    )
    & py -3 @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

function Get-ForbiddenPayloadHashes {
    param([Parameter(Mandatory = $true)][string[]]$CatalogPaths)
    $hashes = @{
        $trainerSha256 = $true
        $goldEditorSha256 = $true
        $legacyPreparedRuntimeSha256 = $true
    }
    foreach ($catalogPath in $CatalogPaths) {
        $raw = Get-Content -LiteralPath $catalogPath -Raw -Encoding UTF8
        foreach ($match in [regex]::Matches($raw, '(?i)\b[0-9a-f]{64}\b')) {
            $hashes[$match.Value.ToUpperInvariant()] = $true
        }
    }
    return $hashes
}

function Assert-PublicPackage {
    param(
        [Parameter(Mandatory = $true)][string]$PackageRoot,
        [Parameter(Mandatory = $true)]$ForbiddenPayloadHashes
    )
    $packageExe = Join-Path $PackageRoot "$appName.exe"
    Assert-LeafFile $packageExe 'public-core executable'
    $version = (Get-Item -LiteralPath $packageExe).VersionInfo.FileVersion.Trim()
    Assert-Condition ($version -in @('1.7.6', '1.7.6.0')) "Packaged FileVersion is not 1.7.6: $version"

    $internalRoot = Join-Path $PackageRoot '_internal'
    Assert-Condition (Test-Path -LiteralPath $internalRoot -PathType Container) 'Packaged PyInstaller _internal directory is missing.'
    $packagedAssetRoot = Join-Path $internalRoot 'assets'
    $packagedModCatalog = Join-Path $packagedAssetRoot 'mod_catalog.json'
    $packagedCommunityCatalog = Join-Path $packagedAssetRoot 'community_mod_catalog.json'
    $packagedRuntimeManifest = Join-Path $packagedAssetRoot 'lc2_runtime_manifest.json'
    $packagedProfile = Join-Path $packagedAssetRoot 'build_profile.json'
    Assert-Condition ((Get-UpperSha256 $packagedModCatalog) -eq $expectedPublicModCatalogSha256) 'Packaged public MOD catalog identity mismatch.'
    Assert-Condition ((Get-UpperSha256 $packagedCommunityCatalog) -eq $expectedPublicCommunityCatalogSha256) 'Packaged public community catalog identity mismatch.'
    Assert-Condition ((Get-UpperSha256 $packagedRuntimeManifest) -eq $expectedPublicRuntimeManifestSha256) 'Packaged public runtime manifest identity mismatch.'
    Assert-Condition ((Get-UpperSha256 $packagedProfile) -eq (Get-UpperSha256 $publicProfilePath)) 'Packaged distribution profile identity mismatch.'

    $packagedRuntimeRoot = Join-Path $internalRoot 'third_party\lc2_runtime'
    Assert-FileIdentity (Join-Path $packagedRuntimeRoot 'bepinex-runtime.zip') $expectedOfficialRuntimeSize $expectedOfficialRuntimeSha256 'packaged official BepInEx archive'
    Assert-FileIdentity (Join-Path $packagedRuntimeRoot 'LC2CombatBridge.dll') $expectedBridgeSize $expectedBridgeSha256 'packaged LC2 Combat Bridge'
    Assert-Condition (@(Get-ChildItem -LiteralPath $packagedRuntimeRoot -File -Recurse -Force).Count -eq 2) 'Packaged runtime bundle contains unexpected files.'

    $packagedSevenZipRoot = Join-Path $internalRoot 'third_party\7zip'
    Assert-FileIdentity (Join-Path $packagedSevenZipRoot '7z.exe') 575488L $expectedSevenZipExeSha256 'packaged 7-Zip executable'
    Assert-FileIdentity (Join-Path $packagedSevenZipRoot '7z.dll') 1906176L $expectedSevenZipDllSha256 'packaged 7-Zip library'
    Assert-LeafFile (Join-Path $packagedSevenZipRoot 'License.txt') 'packaged complete 7-Zip license'
    Assert-Condition (@(Get-ChildItem -LiteralPath $packagedSevenZipRoot -File -Recurse -Force).Count -eq 3) 'Packaged 7-Zip directory contains unexpected files.'

    $forbiddenRelativePaths = @(
        '_internal/third_party/LostCastle2SoulStoneTrainer v1.2.exe',
        '_internal/third_party/LC2GoldFree.dll',
        '_internal/third_party/community_mods',
        'artifacts',
        'runtime-captures',
        'Screenshots'
    )
    foreach ($relative in $forbiddenRelativePaths) {
        $candidate = Join-Path $PackageRoot $relative.Replace('/', '\')
        Assert-Condition (-not (Test-Path -LiteralPath $candidate)) "Forbidden public-core path exists: $relative"
    }

    $configRoot = Join-Path $PackageRoot 'config'
    Assert-Condition (Test-Path -LiteralPath $configRoot -PathType Container) 'Fresh config directory is missing.'
    Assert-Condition (@(Get-ChildItem -LiteralPath $configRoot -Force).Count -eq 0) 'Fresh config directory is not empty.'
    $exportsRoot = Join-Path $PackageRoot 'exports'
    Assert-Condition (-not (Test-Path -LiteralPath $exportsRoot)) 'Public distribution package must not contain exports.'

    Assert-LeafFile (Join-Path $PackageRoot 'LICENSE') 'packaged project license'
    Assert-LeafFile (Join-Path $PackageRoot 'THIRD_PARTY_NOTICES.md') 'packaged public-core third-party notices'
    Assert-LeafFile (Join-Path $PackageRoot '使用说明.txt') 'packaged public-core usage guide'
    $packagedRuntimeNotices = Join-Path $PackageRoot '运行环境\public-core'
    Assert-Condition (Test-Path -LiteralPath $packagedRuntimeNotices -PathType Container) 'Packaged public-core runtime notices are missing.'
    $sourceNoticeHashes = @{}
    foreach ($sourceNotice in @(Get-ChildItem -LiteralPath $publicRuntimeNoticesSource -File -Force)) {
        $sourceNoticeHashes[$sourceNotice.Name] = Get-UpperSha256 $sourceNotice.FullName
    }
    $packagedNotices = @(Get-ChildItem -LiteralPath $packagedRuntimeNotices -File -Force)
    Assert-Condition ($packagedNotices.Count -eq $sourceNoticeHashes.Count) 'Packaged public-core runtime notice count mismatch.'
    foreach ($packagedNotice in $packagedNotices) {
        Assert-Condition ($sourceNoticeHashes.ContainsKey($packagedNotice.Name)) "Unexpected packaged runtime notice: $($packagedNotice.Name)"
        Assert-Condition ((Get-UpperSha256 $packagedNotice.FullName) -eq $sourceNoticeHashes[$packagedNotice.Name]) "Packaged runtime notice identity mismatch: $($packagedNotice.Name)"
    }

    $packageFiles = @(Get-ChildItem -LiteralPath $PackageRoot -File -Recurse -Force)
    foreach ($file in $packageFiles) {
        $relative = $file.FullName.Substring($PackageRoot.Length).TrimStart('\').Replace('\', '/')
        Assert-Condition (-not ($relative -match '(?i)(^|/)(LogOutput|output_log|player)\.log$')) "Runtime log entered public-core: $relative"
        Assert-Condition (-not ($relative -match '(?i)(^|/)(screenshots?|runtime-captures?)(/|$)')) "Screenshot/capture entered public-core: $relative"
        $sha256 = Get-UpperSha256 $file.FullName
        Assert-Condition (-not $ForbiddenPayloadHashes.ContainsKey($sha256)) "Forbidden third-party payload hash entered public-core: $relative ($sha256)"
    }
    Assert-Condition (-not (@($packageFiles | Where-Object { (Get-UpperSha256 $_.FullName) -eq $legacyPreparedRuntimeSha256 }).Count -gt 0)) 'Legacy prepared runtime archive entered public-core.'

    $selfTest = Start-Process -FilePath $packageExe -ArgumentList '--self-test' -WindowStyle Hidden -Wait -PassThru
    Assert-Condition ($selfTest.ExitCode -eq 0) "Packaged self-test failed with exit code $($selfTest.ExitCode)."
    Assert-Condition (@(Get-ChildItem -LiteralPath $configRoot -Force).Count -eq 0) 'Packaged self-test polluted fresh config.'
    Assert-Condition (-not (Test-Path -LiteralPath $exportsRoot)) 'Packaged self-test created exports.'

    $totalBytes = ($packageFiles | Measure-Object -Property Length -Sum).Sum
    return [pscustomobject]@{
        package_name = $packageName
        package_path = $PackageRoot
        executable_sha256 = Get-UpperSha256 $packageExe
        file_version = $version
        file_count = $packageFiles.Count
        total_bytes = [long]$totalBytes
        runtime_archive_sha256 = $expectedOfficialRuntimeSha256
        bridge_sha256 = $expectedBridgeSha256
        config_file_count = 0
        exports_payload_count = 0
        self_test_exit_code = 0
    }
}

# Preflight is read-only and fail-closed. It never consults the local/private payload roots.
$publicModCatalog = Assert-PublicCatalog $publicModCatalogPath (Join-Path $projectRoot 'assets\mod_catalog.json') $expectedPublicModCatalogSha256 2 'public MOD catalog'
$publicCommunityCatalog = Assert-PublicCatalog $publicCommunityCatalogPath (Join-Path $projectRoot 'assets\community_mod_catalog.json') $expectedPublicCommunityCatalogSha256 60 'public community MOD catalog'
$publicRuntimeManifest = Assert-PublicRuntime $publicRuntimeManifestPath
Assert-LeafFile $publicProfilePath 'distribution build profile'
Assert-SevenZipAndPackageAssets

Invoke-PythonChecked @('tools\prepare_lc2_public_catalog.py', '--check') 'Public catalog generator check'

if ($ValidateOnly) {
    [pscustomobject]@{
        status = 'validated'
        package_name = $packageName
        public_mod_entries = @($publicModCatalog.entries).Count
        public_community_mod_entries = @($publicCommunityCatalog.entries).Count
        runtime_members = @($publicRuntimeManifest.runtime_files).Count
        runtime_archive_sha256 = $expectedOfficialRuntimeSha256
        bridge_sha256 = $expectedBridgeSha256
    } | ConvertTo-Json -Depth 4
    exit 0
}

Assert-LeafFile (Join-Path $projectRoot 'assets\keyview.ico') 'application icon'
Assert-LeafFile (Join-Path $projectRoot 'version_info.txt') 'Windows version resource'
Assert-LeafFile (Join-Path $projectRoot 'contracts\combat_event.schema.json') 'combat event schema'

Invoke-PythonChecked @('-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v') 'Full source test suite'
Invoke-PythonChecked @('keyview.py', '--self-test') 'Source self-test'

Remove-ExactGeneratedRoot $publicBuildRoot $publicBuildParent
Remove-ExactGeneratedRoot $publicDistRoot $publicDistParent
Remove-ExactGeneratedRoot $publicPackageParent (Join-Path $projectRoot 'package')

New-Item -ItemType Directory -Path $publicStageAssets -Force | Out-Null
Copy-Item -LiteralPath $publicModCatalogPath -Destination (Join-Path $publicStageAssets 'mod_catalog.json')
Copy-Item -LiteralPath $publicCommunityCatalogPath -Destination (Join-Path $publicStageAssets 'community_mod_catalog.json')
Copy-Item -LiteralPath $publicRuntimeManifestPath -Destination (Join-Path $publicStageAssets 'lc2_runtime_manifest.json')
Copy-Item -LiteralPath $publicProfilePath -Destination (Join-Path $publicStageAssets 'build_profile.json')

Assert-Condition ((Get-UpperSha256 (Join-Path $publicStageAssets 'mod_catalog.json')) -eq $expectedPublicModCatalogSha256) 'Staged public MOD catalog identity mismatch.'
Assert-Condition ((Get-UpperSha256 (Join-Path $publicStageAssets 'community_mod_catalog.json')) -eq $expectedPublicCommunityCatalogSha256) 'Staged public community catalog identity mismatch.'
Assert-Condition ((Get-UpperSha256 (Join-Path $publicStageAssets 'lc2_runtime_manifest.json')) -eq $expectedPublicRuntimeManifestSha256) 'Staged public runtime manifest identity mismatch.'

$pyInstallerWork = Join-Path $publicBuildRoot 'pyinstaller'
$pyInstallerSpec = Join-Path $publicBuildRoot 'spec'
New-Item -ItemType Directory -Path $pyInstallerWork -Force | Out-Null
New-Item -ItemType Directory -Path $pyInstallerSpec -Force | Out-Null
New-Item -ItemType Directory -Path $publicDistRoot -Force | Out-Null

$pyInstallerArguments = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onedir',
    '--windowed',
    '--name', $appName,
    '--icon', (Join-Path $projectRoot 'assets\keyview.ico'),
    '--version-file', (Join-Path $projectRoot 'version_info.txt'),
    '--workpath', $pyInstallerWork,
    '--distpath', $publicDistRoot,
    '--specpath', $pyInstallerSpec,
    '--collect-data', 'rfc3987_syntax',
    '--add-data', "$(Join-Path $projectRoot 'assets\combat_sources.json');assets",
    '--add-data', "$(Join-Path $projectRoot 'assets\game_locations.json');assets",
    '--add-data', "$(Join-Path $publicStageAssets 'mod_catalog.json');assets",
    '--add-data', "$(Join-Path $publicStageAssets 'community_mod_catalog.json');assets",
    '--add-data', "$(Join-Path $publicStageAssets 'lc2_runtime_manifest.json');assets",
    '--add-data', "$(Join-Path $publicStageAssets 'build_profile.json');assets",
    '--add-data', "$(Join-Path $projectRoot 'assets\keyview.ico');assets",
    '--add-data', "$(Join-Path $projectRoot 'contracts\combat_event.schema.json');contracts",
    '--add-data', "$publicRuntimeSource;third_party/lc2_runtime",
    '--add-data', "$sevenZipSource;third_party/7zip",
    (Join-Path $projectRoot 'keyview.py')
)
Invoke-PythonChecked $pyInstallerArguments 'Public-core PyInstaller build'

$runtimeRoot = Join-Path $publicDistRoot $appName
Assert-Condition (Test-Path -LiteralPath $runtimeRoot -PathType Container) 'Public-core PyInstaller output is missing.'

$packageConfig = Join-Path $publicPackageRoot 'config'
$packageModules = Join-Path $publicPackageRoot 'modules'
$packageUserMods = Join-Path $publicPackageRoot '用户MOD'
$packageSupport = Join-Path $publicPackageRoot '赞助与投喂'
$packageRuntimeNotices = Join-Path $publicPackageRoot '运行环境\public-core'
foreach ($directory in @($publicPackageRoot, $packageConfig, $packageModules, $packageUserMods, $packageSupport, $packageRuntimeNotices)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

Get-ChildItem -LiteralPath $runtimeRoot -Force | Copy-Item -Destination $publicPackageRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'package_assets\public-core.README.txt') -Destination (Join-Path $publicPackageRoot '使用说明.txt')
Copy-Item -LiteralPath (Join-Path $projectRoot 'package_assets\MOD自动添加说明.txt') -Destination $publicPackageRoot
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE') -Destination $publicPackageRoot
Copy-Item -LiteralPath (Join-Path $projectRoot 'PUBLIC_CORE_THIRD_PARTY_NOTICES.md') -Destination (Join-Path $publicPackageRoot 'THIRD_PARTY_NOTICES.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'package_assets\用户MOD\请把MOD放到这里.txt') -Destination $packageUserMods
Copy-Item -LiteralPath (Join-Path $projectRoot 'package_assets\modules.README.txt') -Destination (Join-Path $packageModules 'README.txt')
Get-ChildItem -LiteralPath $supportAssetsSource -File -Force | Copy-Item -Destination $packageSupport
Get-ChildItem -LiteralPath $publicRuntimeNoticesSource -File -Force | Copy-Item -Destination $packageRuntimeNotices

$forbiddenPayloadHashes = Get-ForbiddenPayloadHashes @($publicModCatalogPath, $publicCommunityCatalogPath)
$receipt = Assert-PublicPackage $publicPackageRoot $forbiddenPayloadHashes
$receipt | ConvertTo-Json -Depth 4
