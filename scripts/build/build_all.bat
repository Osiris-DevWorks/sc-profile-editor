@echo off
echo ========================================
echo SC Profile Editor - Build Script
echo ========================================
echo.

echo Step 1: Building executable...
.venv\Scripts\python.exe scripts\build\build_exe.py
if errorlevel 1 (
    echo ERROR: Failed to build executable
    pause
    exit /b 1
)
echo   - Executable created
echo.

echo Step 2: Verifying onedir build...
if exist "dist\SCProfileEditor\SCProfileEditor.exe" (
    echo   - Build folder exists: OK
) else (
    echo   - ERROR: dist\SCProfileEditor\SCProfileEditor.exe not found!
    pause
    exit /b 1
)
echo.

echo Step 3: Creating installer (requires Inno Setup 6)...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    %ISCC% installer.iss
    if errorlevel 1 (
        echo WARNING: Installer creation failed
    ) else (
        echo   - Installer created successfully!
    )
) else (
    echo WARNING: Inno Setup not found; skipping installer creation
    echo Install from https://jrsoftware.org/isdl.php or compile installer.iss manually
)
echo.

echo ========================================
echo Build Complete!
echo ========================================
for %%f in (dist\SCProfileEditor-v*-Setup.exe) do (
    echo   [OK] Installer: %%f
)
echo.
pause
