$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

py -3 .\generate_icon.py
py -3 -m unittest discover -s .\tests -v
py -3 .\keyview.py --self-test
py -3 -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name '失落城堡2按键显示器' `
    --icon '.\assets\keyview.ico' `
    --version-file '.\version_info.txt' `
    '.\keyview.py'

$packageRoot = Join-Path $projectRoot 'package\失落城堡2工具箱'
$packageConfig = Join-Path $packageRoot 'config'
$packageModules = Join-Path $packageRoot 'modules'
$packageExports = Join-Path $packageRoot 'exports'
foreach ($directory in @($packageRoot, $packageConfig, $packageModules, $packageExports)) {
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
}
$runtimeRoot = Join-Path $projectRoot 'dist\失落城堡2按键显示器'
Get-ChildItem -LiteralPath $runtimeRoot -Force | Copy-Item -Destination $packageRoot -Recurse -Force
Copy-Item -LiteralPath '.\package_assets\使用说明.txt' -Destination $packageRoot -Force
Copy-Item -LiteralPath '.\package_assets\modules.README.txt' -Destination (Join-Path $packageModules 'README.txt') -Force
Copy-Item -LiteralPath '.\package_assets\exports.README.txt' -Destination (Join-Path $packageExports 'README.txt') -Force

Write-Output $packageRoot
