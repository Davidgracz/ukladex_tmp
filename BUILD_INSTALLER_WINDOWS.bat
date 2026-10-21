@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Buduje instalator ImpoCraft: dist\ImpoCraft-<wersja>-instalator.exe
rem Instaluje program w Program Files, dodaje skrot w menu Start, wpis "Aplikacje i funkcje"
rem (wydawca: Dawid Gracz) i deinstalator. Dane uzytkownika: %APPDATA%\ImpoCraft.
rem Podpis cyfrowy (opcjonalnie): ustaw IMPOCRAFT_SIGN_THUMBPRINT albo IMPOCRAFT_SIGN_PFX
rem (+ IMPOCRAFT_SIGN_PASSWORD) przed uruchomieniem - opis w scripts\sign_files.py.

set "KEEP_NOPAUSE=%NOPAUSE%"
set "NOPAUSE=1"
call "%~dp0BUILD_EXE_WINDOWS.bat"
if errorlevel 1 goto ERROR
set "NOPAUSE=%KEEP_NOPAUSE%"

set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC goto NOINNO

echo [ImpoCraft] Podpis programu (jesli podano certyfikat) ...
".venv\Scripts\python.exe" scripts\sign_files.py "dist\ImpoCraft\ImpoCraft.exe"
if errorlevel 1 goto ERROR

echo [ImpoCraft] Budowanie instalatora ...
if exist "dist\ImpoCraft-*-instalator.exe" del /q "dist\ImpoCraft-*-instalator.exe"
"%ISCC%" /Qp "packaging\ImpoCraft.iss"
if errorlevel 1 goto ERROR

set "SETUP="
for %%F in ("dist\ImpoCraft-*-instalator.exe") do set "SETUP=%%~fF"
if not defined SETUP goto ERROR

echo [ImpoCraft] Podpis instalatora (jesli podano certyfikat) ...
".venv\Scripts\python.exe" scripts\sign_files.py "%SETUP%"
if errorlevel 1 goto ERROR

echo.
echo ============================================================
echo  Gotowe. Instalator:
echo     %SETUP%
echo  Uruchom go na dowolnym komputerze z Windows 10/11 (64 bit).
echo ============================================================
if not defined NOPAUSE pause
exit /b 0

:NOINNO
echo.
echo Brak Inno Setup 6 (ISCC.exe). Zainstaluj go poleceniem:
echo     winget install --id JRSoftware.InnoSetup -e
echo i uruchom ten plik ponownie.
if not defined NOPAUSE pause
exit /b 1

:ERROR
echo.
echo Blad budowania instalatora. Skopiuj powyzszy blad i przeslij go do analizy.
if not defined NOPAUSE pause
exit /b 1
