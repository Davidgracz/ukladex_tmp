@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Buduje przenosna wersje Impozycjoner Studio (np. na pendrive).
rem   BUILD_EXE_WINDOWS.bat            -> folder dist\Impozycjoner-Studio + ZIP (zalecane, szybki start)
rem   BUILD_EXE_WINDOWS.bat jedenplik  -> dodatkowo jeden plik dist\jeden-plik\Impozycjoner-Studio.exe
set "ONEFILE="
if /i "%~1"=="jedenplik" set "ONEFILE=1"
if /i "%~1"=="onefile" set "ONEFILE=1"
set "APP=dist\Impozycjoner-Studio"

call "%~dp0BOOTSTRAP_WINDOWS.bat"
if errorlevel 1 goto ERROR

echo [Impozycjoner] Instalacja bibliotek, PyInstaller i pytest ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt "pyinstaller>=6,<7" pytest
if errorlevel 1 goto ERROR

echo [Impozycjoner] Testy przed budowaniem ...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto TESTS

echo [Impozycjoner] Ikona ...
".venv\Scripts\python.exe" scripts\make_icon.py build\impozycjoner.ico
if errorlevel 1 goto ERROR

set "COMMON=--noconfirm --clean --windowed --name Impozycjoner-Studio --icon build\impozycjoner.ico --collect-all pymupdf --hidden-import sheet_editor --hidden-import whitecrop --hidden-import tools_ui --hidden-import table_actions --hidden-import user_data --hidden-import page_boxes --hidden-import page_box_ui --add-data assets;assets"

echo [Impozycjoner] Budowanie folderu programu ...
".venv\Scripts\python.exe" -m PyInstaller %COMMON% --onedir app.py
if errorlevel 1 goto ERROR

rem Tryb przenosny: szablony i profile maszyn w folderze "dane" obok EXE.
copy /y "packaging\PORTABLE.txt" "%APP%\PORTABLE.txt" >nul
if not exist "%APP%\dane" mkdir "%APP%\dane"
if not exist "%APP%\przyklady" mkdir "%APP%\przyklady"
copy /y "examples\*.pdf" "%APP%\przyklady\" >nul
copy /y "examples\*.psimp" "%APP%\przyklady\" >nul

echo [Impozycjoner] Sprawdzenie zbudowanego programu (--self-test) ...
".venv\Scripts\python.exe" scripts\check_exe.py "%APP%\Impozycjoner-Studio.exe"
if errorlevel 1 goto ERROR

echo [Impozycjoner] Archiwum ZIP ...
if exist "dist\Impozycjoner-Studio-przenosny.zip" del "dist\Impozycjoner-Studio-przenosny.zip"
powershell -NoProfile -Command "Compress-Archive -Path '%APP%' -DestinationPath 'dist\Impozycjoner-Studio-przenosny.zip'"
if errorlevel 1 goto ERROR

if not defined ONEFILE goto DONE
echo [Impozycjoner] Budowanie jednego pliku EXE ...
".venv\Scripts\python.exe" -m PyInstaller %COMMON% --onefile --distpath dist\jeden-plik app.py
if errorlevel 1 goto ERROR
copy /y "packaging\PORTABLE.txt" "dist\jeden-plik\PORTABLE.txt" >nul
".venv\Scripts\python.exe" scripts\check_exe.py "dist\jeden-plik\Impozycjoner-Studio.exe"
if errorlevel 1 goto ERROR

:DONE
echo.
echo ============================================================
echo  Gotowe. Na pendrive skopiuj caly folder:
echo     %APP%
echo  albo rozpakuj dist\Impozycjoner-Studio-przenosny.zip
echo  i uruchom Impozycjoner-Studio.exe. Szablony i profile maszyn
echo  zapisuja sie w podfolderze "dane" na pendrive.
if defined ONEFILE echo  Jeden plik: dist\jeden-plik\Impozycjoner-Studio.exe + PORTABLE.txt obok
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
