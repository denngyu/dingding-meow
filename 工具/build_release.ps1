param(
    [string]$Version = "1.4.0",
    [string]$PythonExe = "C:\Users\30660\AppData\Local\Programs\Python\Python312\python.exe"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$releaseRoot = Join-Path $repoRoot "_release_stage\package_build\v$Version"
$distRoot = Join-Path $releaseRoot "pyinstaller-dist"
$workRoot = Join-Path $releaseRoot "pyinstaller-work"
$specRoot = Join-Path $releaseRoot "pyinstaller-spec"
$packageRoot = Join-Path $releaseRoot "DingDingMeow"
$fixedZip = Join-Path $repoRoot "DingDingMeow-windows.zip"
$versionedZip = Join-Path $repoRoot "DingDingMeow-v$Version-windows.zip"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

$releaseParent = (Resolve-Path (Join-Path $repoRoot "_release_stage")).Path
$candidate = [System.IO.Path]::GetFullPath($releaseRoot)
if (-not $candidate.StartsWith(
    $releaseParent + [System.IO.Path]::DirectorySeparatorChar,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "Release path escaped _release_stage: $candidate"
}

if (Test-Path -LiteralPath $releaseRoot) {
    Remove-Item -LiteralPath $releaseRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $distRoot, $workRoot, $specRoot, $packageRoot | Out-Null

$iconPath = Join-Path $repoRoot "assets\dingdingmeow.ico"
$pyinstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "盯盯喵",
    "--icon", $iconPath,
    "--collect-all", "cv2",
    "--collect-all", "PIL",
    "--collect-all", "pystray",
    "--distpath", $distRoot,
    "--workpath", $workRoot,
    "--specpath", $specRoot,
    (Join-Path $repoRoot "pet.py")
)

& $PythonExe @pyinstallerArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$exePath = Join-Path $distRoot "盯盯喵.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Built executable not found: $exePath"
}
Copy-Item -LiteralPath $exePath -Destination (Join-Path $packageRoot "盯盯喵.exe")

New-Item -ItemType Directory -Force -Path (
    Join-Path $packageRoot "models"
), (
    Join-Path $packageRoot "assets\cat_sprites"
), (
    Join-Path $packageRoot "assets\cat_animations\knock"
), (
    Join-Path $packageRoot "assets\cat_animations\roll"
) | Out-Null

Copy-Item -LiteralPath (Join-Path $repoRoot "models\yolov4-tiny.cfg") -Destination (Join-Path $packageRoot "models")
Copy-Item -LiteralPath (Join-Path $repoRoot "models\yolov4-tiny.weights") -Destination (Join-Path $packageRoot "models")
Get-ChildItem -LiteralPath (Join-Path $repoRoot "assets\cat_sprites") -File |
    Copy-Item -Destination (Join-Path $packageRoot "assets\cat_sprites") -Force
Copy-Item -LiteralPath (Join-Path $repoRoot "assets\cat_animations\knock\frame_00.png") -Destination (Join-Path $packageRoot "assets\cat_animations\knock")
Copy-Item -LiteralPath (Join-Path $repoRoot "assets\cat_animations\knock\frame_01.png") -Destination (Join-Path $packageRoot "assets\cat_animations\knock")
Copy-Item -LiteralPath (Join-Path $repoRoot "assets\cat_animations\knock\frame_02.png") -Destination (Join-Path $packageRoot "assets\cat_animations\knock")
Copy-Item -LiteralPath (Join-Path $repoRoot "assets\cat_animations\roll\roll_ball.png") -Destination (Join-Path $packageRoot "assets\cat_animations\roll")
Copy-Item -LiteralPath $iconPath -Destination (Join-Path $packageRoot "assets\dingdingmeow.ico")
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $repoRoot "版本说明.md") -Destination $packageRoot

$bat = @'
@echo off
cd /d "%~dp0"
start "" "%~dp0盯盯喵.exe"
'@
[System.IO.File]::WriteAllText(
    (Join-Path $packageRoot "盯盯喵.bat"),
    $bat,
    [System.Text.UTF8Encoding]::new($true)
)

$vbs = @'
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = scriptDir
shell.Run """" & scriptDir & "\盯盯喵.exe""", 0, False
'@
[System.IO.File]::WriteAllText(
    (Join-Path $packageRoot "盯盯喵.vbs"),
    $vbs,
    [System.Text.Encoding]::Unicode
)

$readme = @"
盯盯喵 v$Version（Windows 10/11 便携版）

1. 解压整个 ZIP，不要只单独拖出 EXE。
2. 双击“盯盯喵.exe”或“盯盯喵.vbs”启动。
3. 首次启动会出现新手教程；摄像头画面只在本机处理。
4. 右键小猫或使用托盘菜单，可调整喝水提醒、关闭中央提醒、暂停检测和查看报告。

如 Windows SmartScreen 提示“未知发布者”，请确认下载来源为：
https://github.com/denngyu/dingding-meow/releases

本包不包含用户日志或 settings.json。
"@
[System.IO.File]::WriteAllText(
    (Join-Path $packageRoot "使用说明.txt"),
    $readme,
    [System.Text.UTF8Encoding]::new($true)
)

foreach ($zipPath in ($fixedZip, $versionedZip)) {
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
}
Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $fixedZip -CompressionLevel Optimal
Copy-Item -LiteralPath $fixedZip -Destination $versionedZip

$exeInfo = Get-Item -LiteralPath (Join-Path $packageRoot "盯盯喵.exe")
$zipInfo = Get-Item -LiteralPath $fixedZip
Write-Output "PACKAGE_DIR=$packageRoot"
Write-Output "EXE_PATH=$($exeInfo.FullName)"
Write-Output "EXE_BYTES=$($exeInfo.Length)"
Write-Output "ZIP_PATH=$($zipInfo.FullName)"
Write-Output "ZIP_BYTES=$($zipInfo.Length)"
Write-Output "VERSIONED_ZIP=$versionedZip"
