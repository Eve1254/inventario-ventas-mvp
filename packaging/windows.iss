; SourceDir, ReleaseDir y AppVersion llegan desde scripts/build_windows.py.
[Setup]
AppId={{948B7B28-820F-4F45-85C4-687006BB98A1}
AppName=Inventario y Ventas
AppVersion={#AppVersion}
AppPublisher=Eve1254
AppPublisherURL=https://github.com/Eve1254/inventario-ventas-mvp
DefaultDirName={localappdata}\Programs\InventarioVentas
DefaultGroupName=Inventario y Ventas
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SourceDir={#SourceDir}
OutputDir={#ReleaseDir}
OutputBaseFilename=InventarioVentas-{#AppVersion}-Windows-x64-Setup
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\InventarioVentas.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
Source: "*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Inventario y Ventas"; Filename: "{app}\InventarioVentas.exe"; WorkingDir: "{app}"
Name: "{group}\Ejemplos CSV"; Filename: "{app}\examples"
Name: "{autodesktop}\Inventario y Ventas"; Filename: "{app}\InventarioVentas.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\InventarioVentas.exe"; Description: "Abrir Inventario y Ventas"; Flags: nowait postinstall skipifsilent

; No se elimina %LOCALAPPDATA%\InventarioVentas al desinstalar.
