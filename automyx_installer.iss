[Setup]
; Información del programa
AppName=Nexora Automyx Agent
AppVerName=Automyx Desktop Agent v2.5
AppVersion=2.5.0
AppPublisher=Automyx Team
AppPublisherURL=https://github.com/automyx
AppSupportURL=https://github.com/automyx/support
DefaultDirName={autopf64}\AutomyxAgent
DefaultGroupName=Nexora Automyx
AllowNoIcons=yes
Compression=lzma2
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=Automyx_Agent_Installer_v2.5.exe
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; Copia todo el contenido de la carpeta dist/Automyx al directorio de instalación
Source: "dist\Automyx\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Excluir archivos temporales de pyinstaller si los hubiera (opcional)

[Icons]
Name: "{group}\Nexora Automyx Agent"; Filename: "{app}\Automyx.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\Nexora Automyx Agent"; Filename: "{app}\Automyx.exe"; WorkingDir: "{app}"; Tasks: "desktopicon"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos adicionales:";

[Run]
Filename: "{app}\Automyx.exe"; Description: "Iniciar Nexora Automyx Agent"; Flags: nowait postinstall skipifsilent;