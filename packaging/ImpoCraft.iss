; Instalator ImpoCraft (Inno Setup 6). Budowanie: BUILD_INSTALLER_WINDOWS.bat
; Nazwa, wersja, autor i identyfikator: build\app_info.iss, generowany z app_info.py
; przez scripts\make_version_info.py (jedno źródło prawdy, bez ręcznego przepisywania).

#include "..\build\app_info.iss"
#ifndef SourceDir
  #define SourceDir "..\dist\" + AppName
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

[Setup]
AppId={{#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright={#AppCopyright}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} — instalator
VersionInfoCopyright={#AppCopyright}
; Instalacja w systemie (Program Files, dla wszystkich użytkowników); w oknie można wybrać tylko bieżącego użytkownika.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\build\impozycjoner.ico
OutputDir={#OutputDir}
OutputBaseFilename={#AppName}-{#AppVersion}-instalator
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
CloseApplications=yes
; Podpis cyfrowy dodaje BUILD_INSTALLER_WINDOWS.bat (signtool) po zbudowaniu — tutaj nic nie podpisujemy.

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "psimpassoc"; Description: "Otwieraj pliki projektów .psimp w {#AppName}"; GroupDescription: "Skojarzenia plików:"

[Files]
; Bez PORTABLE.txt i folderu „dane”: zainstalowany program zapisuje dane w %APPDATA%\{#AppName}.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Excludes: "PORTABLE.txt,\dane\*"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autoprograms}\{#AppName} — przykłady"; Filename: "{app}\przyklady"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.psimp\OpenWithProgids"; ValueType: string; ValueName: "ImpoCraft.Project"; ValueData: ""; Flags: uninsdeletevalue; Tasks: psimpassoc
Root: HKA; Subkey: "Software\Classes\ImpoCraft.Project"; ValueType: string; ValueName: ""; ValueData: "Projekt {#AppName}"; Flags: uninsdeletekey; Tasks: psimpassoc
Root: HKA; Subkey: "Software\Classes\ImpoCraft.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"; Tasks: psimpassoc
Root: HKA; Subkey: "Software\Classes\ImpoCraft.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: psimpassoc

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; Aktualizacja z programu (updater.py): cicha instalacja z /RELAUNCH uruchamia nową wersję jako zwykły użytkownik.
Filename: "{app}\{#AppExe}"; Flags: nowait runasoriginaluser; Check: RelaunchRequested

[Code]
function RelaunchRequested: Boolean;
begin
  Result := Pos('/RELAUNCH', UpperCase(GetCmdTail)) > 0;
end;
