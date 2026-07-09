# AUTOMYX 2.5 — Terminal-First AI Agent

## ✅ Transformación Completada

He transformado Automyx en una experiencia **terminal-first profesional** inspirada en Claude Code, pero mucho más potente.

---

## 🚀 Inicio Rápido

```bash
# Iniciar el REPL interactivo
python automyx_cli.py

# Con un modelo específico
python automyx_cli.py --model gpt-4

# Ejecutar el wizard de configuración
python automyx_cli.py onboard

# Verificar el sistema
python automyx_cli.py doctor
```

---

## 📦 Módulos Creados

### 1. **`automyx_cli.py`** — Entry Point Principal
- CLI completo con múltiples comandos
- Soporte para `--model`, `--verbose`, `--version`
- Subcomandos: `repl`, `chat`, `gateway`, `doctor`, `onboard`, `tools`, `skills`, `context`, `session`

### 2. **`core/repl.py`** — REPL Interactivo (588 líneas)
- Interfaz tipo Claude Code
- Banner ASCII profesional
- Detección automática de contexto
- Sistema de comandos integrados (`/help`, `/model`, `/context`, etc.)
- Historial de comandos
- Manejo de interrupciones (Ctrl+C)
- Guardado automático de sesión

### 3. **`core/context.py`** — Context Awareness (391 líneas)
- Detección automática de tipo de proyecto (Python, Node.js, Rust, Go, Java)
- Integración Git (branch, status)
- Detección de frameworks (Django, React, FastAPI, PyTorch, etc.)
- Descubrimiento de herramientas (ffmpeg, docker, ollama, etc.)
- Análisis de dependencias

### 4. **`core/permissions.py`** — Sistema de Permisos (317 líneas)
- 4 niveles de permisos: Safe, Normal, Caution, Dangerous
- Prompts interactivos para operaciones peligrosas
- Listas de always-allow/always-deny
- Permisos por sesión
- Configuración persistente en `~/.automyx/permissions.json`

### 5. **`core/session.py`** — Gestión de Sesiones (265 líneas)
- Sesiones persistentes con historial completo
- Múltiples sesiones simultáneas
- Exportación de historial
- Metadatos de sesión (creado, actualizado, conteo)
- Almacenamiento en `~/.automyx/sessions/`

### 6. **`core/onboard_pro_v3.py`** — Wizard Profesional (436 líneas)
- 5 pasos guiados (~2 minutos)
- Selección de modelo (NVIDIA, OpenAI, Anthropic, Ollama)
- Configuración de API keys con validación
- Verificación de herramientas
- Experiencia de primera ejecución

---

## 🎯 Comandos Disponibles

### Comandos del REPL

| Comando | Descripción |
|---------|-------------|
| `/help` | Mostrar ayuda |
| `/clear` | Limpiar pantalla |
| `/history` | Historial de comandos |
| `/model` | Cambiar modelo |
| `/context` | Mostrar contexto del proyecto |
| `/permissions` | Configuración de permisos |
| `/session` | Gestión de sesiones |
| `/tools` | Listar herramientas (275+) |
| `/skills` | Listar skills (82+) |
| `/exit` | Salir |

### Comandos CLI

```bash
# REPL interactivo (default)
python automyx_cli.py

# Con modelo específico
python automyx_cli.py --model gpt-4

# API gateway
python automyx_cli.py gateway --port 3500

# Health check
python automyx_cli.py doctor

# Setup wizard
python automyx_cli.py onboard

# Listar herramientas
python automyx_cli.py tools

# Listar skills
python automyx_cli.py skills

# Mostrar contexto
python automyx_cli.py context

# Gestión de sesiones
python automyx_cli.py session list
python automyx_cli.py session new
python automyx_cli.py session load --id <session_id>
python automyx_cli.py session save
python automyx_cli.py session delete --id <session_id>
```

---

## 🧠 Características Principales

### 1. **Context Awareness**
```
📁 Working directory: C:\Users\COMPUMAX\Documents\AUTOMIX 2.5
🤖 Model: openai/gpt-oss-120b
📊 Context: Python · git:main · 2 frameworks · 16 tools
```

Detecta automáticamente:
- Tipo de proyecto (Python, Node.js, Rust, Go, Java)
- Branch de Git y status
- Frameworks (Django, React, FastAPI, PyTorch, etc.)
- Herramientas disponibles (ffmpeg, docker, ollama, etc.)
- Dependencias del proyecto

### 2. **Sistema de Permisos**

**4 niveles de seguridad:**

| Nivel | Descripción | Ejemplo |
|-------|-------------|---------|
| **Safe** | Sin permiso necesario | `read_file`, `web_search` |
| **Normal** | Muestra qué hará | `write_file`, `execute_cmd` |
| **Caution** | Requiere confirmación | `delete_file`, `move_file` |
| **Dangerous** | Confirmación explícita | `system_shutdown` |

**Configuración persistente:**
```json
{
  "always_allow": ["read_file", "list_directory"],
  "always_deny": ["system_shutdown", "format_disk"]
}
```

### 3. **Gestión de Sesiones**

- Sesiones persistentes en `~/.automyx/sessions/`
- Historial completo de conversaciones
- Múltiples sesiones simultáneas
- Exportación a archivos de texto
- Metadatos (creado, actualizado, conteo)

### 4. **Onboarding Profesional**

**5 pasos guiados:**
1. Bienvenida e introducción
2. Selección de modelo (NVIDIA, OpenAI, Anthropic, Ollama)
3. Configuración de API keys
4. Verificación de herramientas
5. Experiencia de primera ejecución

---

## 🎨 Interfaz del REPL

```
    ╔═══════════════════════════════════════════════════════════╗
    ║   █████╗ ██╗   ██╗████████╗ ██████╗ ███╗   ███╗██╗   ██╗ ║
    ║  ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗████╗ ████║╚██╗ ██╔╝ ║
    ║  ███████║██║   ██║   ██║   ██║   ██║██╔████╔██║ ╚████╔╝  ║
    ║  ██╔══██║██║   ██║   ██║   ██║   ██║██║╚██╔╝██║  ╚██╔╝   ║
    ║  ██║  ██║╚██████╔╝   ██║   ╚██████╔╝██║ ╚═╝ ██║   ██║    ║
    ║  ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝     ╚═╝   ╚═╝    ║
    ║                                                               ║
    ║              AUTOMYX v2.5 · Terminal Mode                    ║
    ║              Claude Code Style · World-Class AI              ║
    ╚═══════════════════════════════════════════════════════════╝

📁 Working directory: C:\Users\COMPUMAX\Documents\AUTOMIX 2.5
🤖 Model: openai/gpt-oss-120b
📊 Context: Python · git:main · 2 frameworks · 16 tools

Type /help for commands, /exit to quit
Press Tab for completions, ↑↓ for history

──────────────────────────────────────────────────────────────────────

Git: main (19 modified, 6 untracked)
Project: Python
Tools: git, python, python3, node, npm +11 more

❯ 
```

---

## 🔧 Configuración

### Variables de Entorno

```bash
# Modelo por defecto
AUTOMYX_MODEL=openai/gpt-oss-120b

# API keys
NVIDIA_API_KEY=nvapi-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Opcional
AUTOMYX_VERBOSE=1
AUTOMYX_LOG_LEVEL=INFO
```

### Archivos de Configuración

```
~/.automyx/
├── sessions/
│   ├── session_1234567890.json
│   └── session_1234567891.json
└── permissions.json
```

---

## 💪 Ventajas sobre Claude Code

| Característica | Claude Code | Automyx 2.5 |
|----------------|-------------|-------------|
| **Modelos** | Solo Anthropic | NVIDIA, OpenAI, Anthropic, Ollama |
| **Herramientas** | ~50 | **275+ herramientas** |
| **Skills** | Limitadas | **82+ skills profesionales** |
| **Auto-aprendizaje** | No | **3 sistemas de aprendizaje** |
| **Edición de video** | No | **FFmpeg profesional** |
| **Generación 3D** | No | **Blender integrado** |
| **Control PC** | Limitado | **PyAutoGUI completo** |
| **Multi-tarea** | No | **6 workers paralelos** |
| **Sesiones** | Básicas | **Persistencia completa** |
| **Permisos** | Básicos | **4 niveles con always-allow/deny** |
| **Contexto** | Básico | **Detección automática** |
| **Código abierto** | No | **100% open source** |
| **Precio** | $20/mes | **Gratis (NVIDIA API)** |

---

## 🎯 Ejemplos de Uso

### Edición de Video
```
❯ edita el video fabricio.mp4 en descargas
❯ ponle subtítulos verdes centrados
❯ aplica efecto de zoom dinámico
```

### Gestión de Archivos
```
❯ crea una carpeta llamada proyecto en descargas
❯ mueve todos los archivos .mp4 a la carpeta videos
❯ busca archivos mayores a 1GB
```

### Operaciones Web
```
❯ busca información sobre machine learning
❯ descarga el video de youtube https://...
❯ abre github.com
```

### Ejecución de Código
```
❯ ejecuta este código python: print("hello")
❯ crea un script que sume dos números
❯ analiza este archivo csv
```

### Control del Sistema
```
❯ abre chrome
❯ toma una captura de pantalla
❯ lista los procesos activos
```

---

## 🐛 Troubleshooting

### Error: "Model not found"
```bash
python automyx_cli.py tools
```

### Error: "Permission denied"
```bash
python automyx_cli.py context
# O ejecuta con --verbose
python automyx_cli.py --verbose
```

### Error: "API key invalid"
```bash
python automyx_cli.py onboard
```

### Error: "Tool not found"
```bash
# Instala la herramienta faltante
# Ejemplo: ffmpeg
choco install ffmpeg  # Windows
brew install ffmpeg   # macOS
sudo apt install ffmpeg  # Linux
```

---

## 📚 Documentación

- **GitHub:** https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5
- **Issues:** https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5/issues
- **Discussions:** https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5/discussions

---

## 🎓 Sistemas de Auto-Aprendizaje

### 1. Error Learning System
- Registra errores y su contexto
- Extrae lecciones de fallos
- Provee advertencias para situaciones similares
- Estadísticas de errores

### 2. Skill Forger
- Detecta patrones repetidos
- Agrupa solicitudes similares
- Crea nuevas skills automáticamente
- Valida y promueve skills exitosas

### 3. Aumformbring
- Memoria conversacional
- Reconocimiento de patrones
- Ciclos de auto-mejora
- Tracking de uso de skills

---

## 🔄 Comparación con la Versión Anterior

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| **Interfaz** | Web-first | **Terminal-first** |
| **Onboarding** | Básico | **Profesional (5 pasos)** |
| **Contexto** | Manual | **Automático** |
| **Permisos** | No existía | **4 niveles** |
| **Sesiones** | Básicas | **Persistencia completa** |
| **Comandos** | Limitados | **10+ comandos especiales** |
| **UX** | Compleja | **Intuitiva (Claude Code style)** |

---

## 🎉 Resultado Final

Automyx ahora es:
- ✅ **Terminal-first** como Claude Code
- ✅ **Más potente** (275+ herramientas vs ~50)
- ✅ **Más inteligente** (3 sistemas de auto-aprendizaje)
- ✅ **Más seguro** (sistema de permisos de 4 niveles)
- ✅ **Más profesional** (onboarding guiado)
- ✅ **Más flexible** (múltiples proveedores de IA)
- ✅ **Más completo** (edición de video, 3D, control PC)
- ✅ **100% open source** y gratuito

---

## 🚀 Para Empezar

```bash
# 1. Ejecutar el wizard de configuración (primera vez)
python automyx_cli.py onboard

# 2. Iniciar el REPL
python automyx_cli.py

# 3. Explorar comandos
❯ /help

# 4. Ver contexto del proyecto
❯ /context

# 5. Listar herramientas disponibles
❯ /tools

# 6. Salir
❯ /exit
```

---

**Made with ❤️ by Nexora Technology LLC**

**Automyx 2.5 — Terminal-First AI Agent · Claude Code Style · World-Class AI**
