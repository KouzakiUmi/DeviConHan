@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
cls

set "ROOT=%~dp0"
set PY_SCRIPT=main.py
set OUT_TOOL=Tyrano_Toolbox
set OUT_PATCH=DevilConnection_Patch

echo ==========================================
echo    Tyrano Builder 
echo ==========================================

if not exist "%ROOT%tools\node.exe" (
    echo [Error] File missing: tools\node.exe
    pause
    exit /b 1
)

if not exist "%ROOT%tools\bundled_asar" (
    echo [Error] Folder missing: tools\bundled_asar
    pause
    exit /b 1
)

if not exist "%ROOT%tools\asar_cli.mjs" (
    echo [Error] File missing: tools\asar_cli.mjs
    pause
    exit /b 1
)

if not exist "%ROOT%%PY_SCRIPT%" (
    echo [Error] Script missing: main.py
    pause
    exit /b 1
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found
    pause
    exit /b 1
)
python --version

python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] PyInstaller not found
    pause
    exit /b 1
)

echo.
echo [1/2] Building Toolbox...
echo ------------------------------------------

if exist "dist" rd /s /q "dist"

python -m PyInstaller -F -w --clean -i "%ROOT%icon.ico" --distpath "dist" --workpath "build_toolbox" --add-data "%ROOT%icon.ico;." --add-data "%ROOT%tools\node.exe;tools" --add-data "%ROOT%tools\bundled_asar;tools\bundled_asar" --add-data "%ROOT%tools\asar_cli.mjs;tools" --add-data "%ROOT%config.ini;." --add-data "%ROOT%core;core" --add-data "%ROOT%gui;gui" --add-data "%ROOT%utils;utils" --name "%OUT_TOOL%" "%ROOT%%PY_SCRIPT%"

if %errorlevel% neq 0 (
    echo [Error] Toolbox build failed
    pause
    exit /b 1
)

if exist "build_toolbox" rd /s /q "build_toolbox"

echo.
echo [2/2] Checking for Patch Data...

set "BUILD_PATCHER=0"

if exist "%ROOT%Patch.zip" (
    echo - Patch.zip found.
    set "BUILD_PATCHER=1"
)

if exist "%ROOT%Patch" (
    setlocal enabledelayedexpansion
    set "HAS_PATCH_FILES="
    for /D %%F in ("%ROOT%Patch\*") do set "HAS_PATCH_FILES=1" & goto :check_files
    for %%F in ("%ROOT%Patch\*") do set "HAS_PATCH_FILES=1" & goto :check_files
    :check_files
    if defined HAS_PATCH_FILES (
        echo - Patch folder found. Compressing to Patch.zip to boost startup performance...
        if exist "%ROOT%Patch.zip" del /q "%ROOT%Patch.zip"
        python -c "import shutil; shutil.make_archive('Patch', 'zip', 'Patch')"
        
        if exist "%ROOT%Patch.zip" (
            echo - Cleaning up original Patch directory...
            rd /s /q "%ROOT%Patch"
            set "HAS_PATCH_DATA=1"
        ) else (
            echo [Error] Failed to compress Patch directory.
        )
    ) else (
        echo - Warning: Patch folder is empty.
    )
    if defined HAS_PATCH_DATA (
        endlocal & set "BUILD_PATCHER=1"
    ) else (
        endlocal
    )
)

if "%BUILD_PATCHER%"=="1" (
    echo - Building Patcher...
    echo ------------------------------------------

    python -m PyInstaller -F -w --clean -i "%ROOT%icon.ico" --distpath "dist" --workpath "build_patcher" --add-data "%ROOT%icon.ico;." --add-data "%ROOT%tools\node.exe;tools" --add-data "%ROOT%tools\bundled_asar;tools\bundled_asar" --add-data "%ROOT%tools\asar_cli.mjs;tools" --add-data "%ROOT%config.ini;." --add-data "%ROOT%core;core" --add-data "%ROOT%gui;gui" --add-data "%ROOT%utils;utils" --add-data "%ROOT%Patch.zip;." --name "%OUT_PATCH%" "%ROOT%%PY_SCRIPT%"

    if %errorlevel% neq 0 (
        echo [Error] Patcher build failed
        pause
        exit /b 1
    )
    echo - Patcher build success.

    if exist "build_patcher" rd /s /q "build_patcher"
) else (
    echo - No Patch data found. Skipped.
)

echo.
echo [Cleanup] Cleaning up...
if exist "build_toolbox" rd /s /q "build_toolbox"
if exist "build_patcher" rd /s /q "build_patcher"
if exist "__pycache__" rd /s /q "__pycache__"
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
