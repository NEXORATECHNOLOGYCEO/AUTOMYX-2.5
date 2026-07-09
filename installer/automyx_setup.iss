; ============================================================================
; AUTOMYX 2.5 — Inno Setup Script
; Genera: dist/AutomyxSetup.exe
; ============================================================================

#define AppName      "Automyx"
#define AppVersion   "2.5.0"
#define AppPublisher "Nexora Technology LLC"
#define AppURL       "https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5"
#define AppExeName   "Automyx.exe"
#define AppDesc      "Autonomous AI Agent — Terminal Edition"
#define SourceDir    "..\dist\Automyx"
#define OutputDir    "..\dist"
#define IconFile     "..\assets\logo.ico"

[Setup]
; ── Identificadores ──────────────────────────────────────────────────────────
AppId={{F4A2B3C1-8D7E-4F9A-B2C3-D4E5F6A7B8C9}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

; ── Rutas ────────────────────────────────────────────────────────────────────
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir={#OutputDir}
OutputBaseFilename=AutomyxSetup
SetupIconFile={#IconFile}

; ── Compresión ───────────────────────────────────────────────────────────────
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; ── Apariencia ───────────────────────────────────────────────────────────────
WizardStyle=modern
WizardSizePercent=120
DisableWelcomePage=no
LicenseFile=..\LICENSE
; Imagen lateral del wizard (bmp 164x314 o 55x58 arriba)
; WizardImageFile=wizard_image.bmp

; ── Plataforma ───────────────────────────────────────────────────────────────
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; ── Opciones extra ───────────────────────────────────────────────────────────
AllowNoIcons=yes
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
PrivilegesRequiredOverridesAllowed=dialog
PrivilegesRequired=lowest

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; ── Mensajes personalizados ──────────────────────────────────────────────────
[CustomMessages]
spanish.WelcomeTitle=Bienvenido a {#AppName} {#AppVersion}
spanish.WelcomeDesc=El agente de IA autónomo más potente para tu terminal.{br}{br}Este asistente instalará {#AppName} en tu equipo.
english.WelcomeTitle=Welcome to {#AppName} {#AppVersion}
english.WelcomeDesc=The most powerful autonomous AI agent for your terminal.{br}{br}This wizard will install {#AppName} on your computer.

[Tasks]
Name: "desktopicon";    Description: "Crear acceso directo en el &escritorio";    GroupDescription: "Iconos:"; Flags: unchecked
Name: "quicklaunchicon";Description: "Crear icono en la &barra de inicio rápido"; GroupDescription: "Iconos:"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "addtopath";      Description: "Añadir {#AppName} al &PATH del sistema";    GroupDescription: "Sistema:"; Flags: unchecked

[Files]
; ── Archivos del programa ─────────────────────────────────────────────────────
; Copiar toda la carpeta dist/Automyx al directorio de instalación
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Configuración inicial ─────────────────────────────────────────────────────
; .env vacío para que el usuario configure sus API keys
Source: "..\installer\default.env"; DestDir: "{app}"; DestName: ".env"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
; Opción de lanzar Automyx al finalizar la instalación
Filename: "{app}\{#AppExeName}"; Parameters: "--version"; Description: "Verificar instalación de {#AppName}"; Flags: nowait postinstall skipifsilent runascurrentuser

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Registry]
; Añadir al PATH si el usuario lo eligió
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
// ── Verificar si la ruta ya está en PATH ─────────────────────────────────────
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
end;

// ── Página de bienvenida personalizada ───────────────────────────────────────
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel1.Caption := CustomMessage('WelcomeTitle');
  WizardForm.WelcomeLabel2.Caption := CustomMessage('WelcomeDesc');
end;
