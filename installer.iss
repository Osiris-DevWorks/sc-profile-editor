; Star Citizen Profile Editor Installer Script
; Created with Inno Setup

#define MyAppName "Star Citizen Profile Editor"
#define MyAppVersion "0.7.4"
#define MyAppPublisher "SC Profile Tools"
#define MyAppURL "https://github.com/yourusername/scpe-releases"
#define MyAppExeName "SCProfileEditor-v0.7.4.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{8F9A7B5C-3D2E-4A1B-9C8D-7E6F5A4B3C2D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=SCProfileEditor-v{#MyAppVersion}-Setup
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[CustomMessages]
SCDirectoryPrompt=Star Citizen Profiles Directory
SCDirectoryPromptDesc=Please specify your Star Citizen profiles directory for quick access to your control profiles.
SCDirectoryDefaultDesc=This is typically located at:
SCDirectoryDefaultPath=C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\USER\Client\0\Controls\Mappings

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "label_overrides.json"; DestDir: "{app}"; Flags: ignoreversion
; Visual templates are embedded in the .onefile executable
; Source: "dist\visual-templates\*"; DestDir: "{app}\visual-templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "example-profiles\*"; DestDir: "{app}\example-profiles"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "default-bindings\*"; DestDir: "{app}\default-bindings"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\User Guide"; Filename: "{app}\README.md"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UnInstallOldVersion(): Integer;
var
  sUnInstallString: String;
  iResultCode: Integer;
begin
  // Return Values:
  // 1 - uninstall string is empty
  // 2 - error executing the UnInstallString
  // 3 - successfully executed the UnInstallString

  // default return value
  Result := 0;

  // get the uninstall string of the old app
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES','', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := 3
    else
      Result := 2;
  end else
    Result := 1;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep=ssInstall) then
  begin
    if (IsUpgrade()) then
    begin
      UnInstallOldVersion();
    end;
  end;
end;

var
  SCDirectoryPage: TInputDirWizardPage;
  SCDirectoryPath: String;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  UninstallString: String;
  ButtonPressed: Integer;
begin
  Result := True;

  // Check if the application is already installed
  UninstallString := GetUninstallString();
  if UninstallString <> '' then
  begin
    // Show custom dialog with three options
    ButtonPressed := MsgBox('Star Citizen Profile Editor is already installed.' + #13#10 + #13#10 +
                            'Choose an option:' + #13#10 +
                            '  - Click YES to uninstall the old version and install this new version' + #13#10 +
                            '  - Click NO to uninstall the old version only (without installing)' + #13#10 +
                            '  - Click CANCEL to exit without making any changes',
                            mbConfirmation, MB_YESNOCANCEL);

    case ButtonPressed of
      IDYES: begin
        // Continue with upgrade (uninstall old, then install new)
        Result := True;
      end;
      IDNO: begin
        // Uninstall only, without installing new version
        UninstallString := RemoveQuotes(UninstallString);
        Exec(UninstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES','', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        Result := False;
      end;
      IDCANCEL: begin
        // Cancel installation
        Result := False;
      end;
    end;
  end;
end;

procedure InitializeWizard();
var
  DefaultPath: String;
begin
  // Create custom page for Star Citizen directory selection
  DefaultPath := ExpandConstant('{#MyAppVersion}');

  // Check if default SC directory exists
  if DirExists('C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\USER\Client\0\Controls\Mappings') then
    DefaultPath := 'C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\USER\Client\0\Controls\Mappings'
  else
    DefaultPath := 'C:\Program Files\Roberts Space Industries';

  SCDirectoryPage := CreateInputDirPage(
    wpSelectTasks,
    ExpandConstant('{cm:SCDirectoryPrompt}'),
    ExpandConstant('{cm:SCDirectoryPromptDesc}'),
    ExpandConstant('{cm:SCDirectoryDefaultDesc}' + #13#10 + '{cm:SCDirectoryDefaultPath}'),
    False,
    'Star Citizen Profiles'
  );

  SCDirectoryPage.Add('');
  SCDirectoryPage.Values[0] := DefaultPath;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  // Store the selected directory path
  if CurPageID = SCDirectoryPage.ID then
  begin
    SCDirectoryPath := SCDirectoryPage.Values[0];
  end;
end;

procedure CurInstallProgressChanged(CurProgress, MaxProgress: Integer);
begin
  // Empty - just to satisfy the syntax
end;

procedure CurFinished(LastStep: TSetupStep);
var
  RegPath: String;
begin
  if LastStep = ssPostInstall then
  begin
    // Save the SC directory to registry
    if SCDirectoryPath <> '' then
    begin
      RegPath := 'Software\SC Tools\Star Citizen Profile Viewer';
      RegWriteStringValue(HKCU, RegPath, 'sc_profiles_directory', SCDirectoryPath);
    end;
  end;
end;
