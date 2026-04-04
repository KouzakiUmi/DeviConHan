@echo off
setlocal
:: 切换编码防止乱码
chcp 65001 >nul
:: 强制进入脚本所在目录 (防止路径跑偏)
cd /d "%~dp0"
cls

:: ================= 配置区域 =================
:: 获取当前脚本的绝对路径 (带反斜杠)
set "ROOT=%~dp0"

:: Python 脚本文件名
set PY_SCRIPT=main.py

:: 输出文件名
set OUT_TOOL=Tyrano_Toolbox
set OUT_PATCH=DevilConnection_Patch
:: ===========================================

echo ==========================================
echo    Tyrano Builder 
echo ==========================================

:: 1. 检查 node.exe 是否存在 (使用绝对路径检测)
if not exist "%ROOT%tools\node.exe" (
    echo [Error] File missing: "%ROOT%tools\node.exe"
    echo 请确认 tools 文件夹就在 Pack.cmd 旁边
    pause
    exit /b 1
)

:: 1b. 检查 bundled_asar 文件夹是否存在
if not exist "%ROOT%tools\bundled_asar" (
    echo [Error] Folder missing: "%ROOT%tools\bundled_asar"
    pause
    exit /b 1
)

:: 1c. 检查 asar_cli.mjs 是否存在
if not exist "%ROOT%tools\asar_cli.mjs" (
    echo [Error] File missing: "%ROOT%tools\asar_cli.mjs"
    pause
    exit /b 1
)

:: 1d. 检查 Python 脚本是否存在
if not exist "%ROOT%%PY_SCRIPT%" (
    echo [Error] Script missing: "%ROOT%%PY_SCRIPT%"
    pause
    exit /b 1
)

:: 2. 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found!
    pause
    exit /b 1
)

:: 3. 检查 PyInstaller (用 python -m 调用)
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] PyInstaller not found.
    echo Please run: pip install pyinstaller
    pause
    exit /b 1
)

:: ========================================================
:: 任务 A: 构建 [纯净工具箱] (Toolbox Mode)
:: ========================================================
echo.
echo [1/2] Building Toolbox...
echo ------------------------------------------

if exist "dist" rd /s /q "dist"

python -m PyInstaller -F --clean ^
    --distpath "dist" ^
    --workpath "build_toolbox" ^
    --add-data "%ROOT%tools\node.exe;tools" ^
    --add-data "%ROOT%tools\bundled_asar;tools\bundled_asar" ^
    --add-data "%ROOT%tools\asar_cli.mjs;tools" ^
    --add-data "%ROOT%config.ini;." ^
    --add-data "%ROOT%utils\language.py;utils" ^
    --name "%OUT_TOOL%" ^
    "%ROOT%%PY_SCRIPT%"

if %errorlevel% neq 0 (
    echo [Error] Toolbox build failed.
    pause
    exit /b 1
)

:: ========================================================
:: 任务 B: 构建 [汉化补丁] (Auto-Patcher Mode)
:: ========================================================
echo.
echo [2/2] Checking for Patch Data...

if not exist "%ROOT%Patch" (
    echo - No Patch folder found. Skipped.
) else (
    REM 检查 Patch 文件夹是否非空
    setlocal enabledelayedexpansion
    set "HAS_PATCH_FILES="
    for /D %%F in ("%ROOT%Patch\*") do set "HAS_PATCH_FILES=1" & goto :check_files
    for %%F in ("%ROOT%Patch\*") do set "HAS_PATCH_FILES=1" & goto :check_files
    :check_files
    if not defined HAS_PATCH_FILES (
        echo - Warning: Patch folder is empty. Skipped.
    ) else (

        echo - Patch folder found. Building Patcher...
        echo ------------------------------------------

        python -m PyInstaller -F --clean ^
            --distpath "dist" ^
            --workpath "build_patcher" ^
            --add-data "%ROOT%tools\node.exe;tools" ^
            --add-data "%ROOT%tools\bundled_asar;tools\bundled_asar" ^
            --add-data "%ROOT%tools\asar_cli.mjs;tools" ^
            --add-data "%ROOT%config.ini;." ^
            --add-data "%ROOT%utils\language.py;utils" ^
            --add-data "%ROOT%Patch;Patch" ^
            --name "%OUT_PATCH%" ^
            "%ROOT%%PY_SCRIPT%"

        if %errorlevel% neq 0 (
            echo [Error] Patcher build failed.
            pause
            exit /b 1
        )
        echo - Patcher build success.
    )
)

:: ========================================================
:: 收尾
:: ========================================================
echo.
echo [Cleanup] Cleaning up...
if exist "build_toolbox" rd /s /q "build_toolbox"
if exist "build_patcher" rd /s /q "build_patcher"
if exist "__pycache__" rd /s /q "__pycache__"
REM 删除根目录生成的 spec 文件
del /q *.spec >nul 2>&1

echo.
echo ==========================================
echo    Build Complete!
echo ==========================================
echo.
echo Generated files:
if exist "dist\%OUT_TOOL%.exe" (
    echo   - Toolbox: dist\%OUT_TOOL%.exe
)
if exist "dist\%OUT_PATCH%.exe" (
    echo   - Patcher: dist\%OUT_PATCH%.exe
)
echo.
if not "%GITHUB_ACTIONS%"=="true" pause
