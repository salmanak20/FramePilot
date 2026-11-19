#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8A93EE4E-1F2A-4EF6-A594-7A6E504C10A1}
AppName=FramePilot
AppVersion={#AppVersion}
AppPublisher=FramePilot
DefaultDirName={localappdata}\Programs\FramePilot
DefaultGroupName=FramePilot
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64
OutputDir=..
OutputBaseFilename=FramePilot-Setup-windows-x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=FramePilot
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\FramePilot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\FramePilot"; Filename: "{app}\FramePilot.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\FramePilot"; Filename: "{app}\FramePilot.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\FramePilot.exe"; Description: "Launch FramePilot"; Flags: postinstall nowait skipifsilent
