@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Buduje przenosna wersje ImpoCraft (np. na pendrive). Instalator: BUILD_INSTALLER_WINDOWS.bat
rem   BUILD_EXE_WINDOWS.bat            -> folder dist\ImpoCraft + ZIP (zalecane, szybki start)
rem   BUILD_EXE_WINDOWS.bat jedenplik  -> dodatkowo jeden plik dist\jeden-plik\ImpoCraft.exe
set "ONEFILE="
if /i "%~1"=="jedenplik" set "ONEFILE=1"
if /i "%~1"=="onefile" set "ONEFILE=1"
set "APP=dist\ImpoCraft"

call "%~dp0BOOTSTRAP_WINDOWS.bat"
if errorlevel 1 goto ERROR

echo [ImpoCraft] Instalacja bibliotek, PyInstaller i pytest ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt "pyinstaller>=6,<7" pytest
if errorlevel 1 goto ERROR

echo [ImpoCraft] Testy przed budowaniem ...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto TESTS

echo [ImpoCraft] Ikona i informacje o wersji ...
".venv\Scripts\python.exe" scripts\make_icon.py build\impozycjoner.ico
if errorlevel 1 goto ERROR
".venv\Scripts\python.exe" scripts\make_version_info.py build\version_info.txt
if errorlevel 1 goto ERROR

set "COMMON=--noconfirm --clean --windowed --name ImpoCraft --icon build\impozycjoner.ico --version-file build\version_info.txt --hidden-import app_info --collect-all pymupdf --hidden-import sheet_editor --hidden-import whitecrop --hidden-import tools_ui --hidden-import table_actions --hidden-import user_data --hidden-import page_boxes --hidden-import page_box_ui --add-data assets;assets"

echo [ImpoCraft] Budowanie folderu programu ...
".venv\Scripts\python.exe" -m PyInstaller %COMMON% --onedir app.py
if errorlevel 1 goto ERROR

rem Tryb przenosny: szablony i profile maszyn w folderze "dane" obok EXE.
copy /y "packaging\PORTABLE.txt" "%APP%\PORTABLE.txt" >nul
if not exist "%APP%\dane" mkdir "%APP%\dane"
if not exist "%APP%\przyklady" mkdir "%APP%\przyklady"
copy /y "examples\*.pdf" "%APP%\przyklady\" >nul
copy /y "examples\*.psimp" "%APP%\przyklady\" >nul

echo [ImpoCraft] Sprawdzenie zbudowanego programu (--self-test) ...
".venv\Scripts\python.exe" scripts\check_exe.py "%APP%\ImpoCraft.exe"
if errorlevel 1 goto ERROR

echo [ImpoCraft] Archiwum ZIP ...
if exist "dist\ImpoCraft-przenosny.zip" del "dist\ImpoCraft-przenosny.zip"
powershell -NoProfile -Command "Compress-Archive -Path '%APP%' -DestinationPath 'dist\ImpoCraft-przenosny.zip'"
if errorlevel 1 goto ERROR

if not defined ONEFILE goto DONE
echo [ImpoCraft] Budowanie jednego pliku EXE ...
".venv\Scripts\python.exe" -m PyInstaller %COMMON% --onefile --distpath dist\jeden-plik app.py
if errorlevel 1 goto ERROR
copy /y "packaging\PORTABLE.txt" "dist\jeden-plik\PORTABLE.txt" >nul
".venv\Scripts\python.exe" scripts\check_exe.py "dist\jeden-plik\ImpoCraft.exe"
if errorlevel 1 goto ERROR

:DONE
echo.
echo ============================================================
echo  Gotowe. Na pendrive skopiuj caly folder:
echo     %APP%
echo  albo rozpakuj dist\ImpoCraft-przenosny.zip
echo  i uruchom ImpoCraft.exe. Szablony i profile maszyn
echo  zapisuja sie w podfolderze "dane" na pendrive.
if defined ONEFILE echo  Jeden plik: dist\jeden-plik\ImpoCraft.exe + PORTABLE.txt obok
echo ============================================================
if not defined NOPAUSE pause
exit /b 0

:TESTS
echo.
echo Testy nie przeszly - EXE nie zostal zbudowany. Popraw bledy powyzej.
if not defined NOPAUSE pause
exit /b 1

:ERROR
echo.
echo Blad budowania EXE. Skopiuj powyzszy blad i przeslij go do analizy.
if not defined NOPAUSE pause
exit /b 1
