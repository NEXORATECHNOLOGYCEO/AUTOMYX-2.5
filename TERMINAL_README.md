# AUTOMYX 2.5 — Terminal-First AI Agent

**Claude Code Style · World-Class AI · Self-Learning**

---

## 🚀 Quick Start

```bash
# Start the terminal REPL
python automyx_cli.py

# Or use the short form
python automyx_cli.py repl

# Start with a specific model
python automyx_cli.py --model gpt-4
```

---

## ✨ Features

### 🎯 Terminal-First Experience
- **Interactive REPL** with streaming responses
- **Rich terminal UI** with colors, panels, and tables
- **Command history** with arrow key navigation
- **Auto-completion** for commands and tools
- **Session persistence** across restarts

### 🧠 Context Awareness
- **Automatic project detection** (Python, Node.js, Rust, Go, etc.)
- **Git integration** (branch, status, remote)
- **Framework detection** (Django, React, FastAPI, etc.)
- **Tool discovery** (ffmpeg, docker, ollama, etc.)
- **Dependency analysis** (requirements.txt, package.json, etc.)

### 🔐 Permission System
- **Safe operations** (read, search) — no permission needed
- **Normal operations** (write, execute) — show what will happen
- **Caution operations** (delete, move) — require confirmation
- **Dangerous operations** (system commands) — explicit confirmation
- **Always allow/deny lists** for frequently used operations

### 🎨 Professional Onboarding
- **Step-by-step wizard** (5 steps, ~2 minutes)
- **Model selection** (NVIDIA, OpenAI, Anthropic, Ollama)
- **API key configuration** with validation
- **Tool verification** (ffmpeg, python, git)
- **First-run experience** with interactive test

### 🔄 Session Management
- **Persistent sessions** with full history
- **Multiple sessions** support
- **Session export** to text files
- **Session metadata** (created, updated, message count)

### 🛠️ Auto-Learning Capabilities
- **Error learning system** — learns from mistakes
- **Skill forger** — creates new skills automatically
- **Aumformbring** — conversational memory + auto-improvement
- **Pattern detection** — identifies repeated requests
- **Skill promotion** — promotes successful skills

---

## 📖 Commands

### REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear screen |
| `/history` | Show command history |
| `/model` | Change model |
| `/context` | Show current context |
| `/permissions` | Show permission settings |
| `/session` | Session management |
| `/tools` | List available tools |
| `/skills` | List available skills |
| `/exit` | Exit Automyx |

### CLI Commands

```bash
# Start REPL (default)
python automyx_cli.py

# Start with specific model
python automyx_cli.py --model gpt-4

# Start API gateway
python automyx_cli.py gateway --port 3500

# Run health check
python automyx_cli.py doctor

# Run setup wizard
python automyx_cli.py onboard

# List tools
python automyx_cli.py tools

# List skills
python automyx_cli.py skills

# Show context
python automyx_cli.py context

# Session management
python automyx_cli.py session list
python automyx_cli.py session new
python automyx_cli.py session load --id <session_id>
python automyx_cli.py session save
python automyx_cli.py session delete --id <session_id>
```

---

## 🎯 Examples

### Video Editing
```
❯ edita el video fabricio.mp4 en descargas
❯ ponle subtítulos verdes centrados
❯ aplica efecto de zoom dinámico
```

### File Management
```
❯ crea una carpeta llamada proyecto en descargas
❯ mueve todos los archivos .mp4 a la carpeta videos
❯ busca archivos mayores a 1GB
```

### Web Operations
```
❯ busca información sobre machine learning
❯ descarga el video de youtube https://...
❯ abre github.com
```

### Code Execution
```
❯ ejecuta este código python: print("hello")
❯ crea un script que sume dos números
❯ analiza este archivo csv
```

### System Control
```
❯ abre chrome
❯ toma una captura de pantalla
❯ lista los procesos activos
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Model selection
AUTOMYX_MODEL=openai/gpt-oss-120b

# API keys
NVIDIA_API_KEY=nvapi-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
AUTOMYX_VERBOSE=1
AUTOMYX_LOG_LEVEL=INFO
```

### Permission Configuration

Permissions are stored in `~/.automyx/permissions.json`:

```json
{
  "always_allow": [
    "read_file",
    "list_directory",
    "web_search"
  ],
  "always_deny": [
    "system_shutdown",
    "format_disk"
  ]
}
```

### Session Storage

Sessions are stored in `~/.automyx/sessions/`:

```
~/.automyx/
├── sessions/
│   ├── session_1234567890.json
│   └── session_1234567891.json
└── permissions.json
```

---

## 🏗️ Architecture

```
automyx_cli.py          # Main entry point
├── core/
│   ├── repl.py         # Interactive REPL
│   ├── context.py      # Context awareness
│   ├── permissions.py  # Permission system
│   ├── session.py      # Session management
│   ├── agent.py        # AI agent logic
│   ├── terminal.py     # Terminal UI
│   └── onboard_pro_v3.py  # Setup wizard
├── tools/
│   ├── video_tools.py
│   ├── photo_editor_tools.py
│   ├── web_tools.py
│   └── ...
├── skills/
│   ├── video-editor-pro/
│   ├── motion-graphics-pro/
│   └── ...
└── state/
    ├── automyx.sqlite
    └── onboard_state.json
```

---

## 🎓 Learning System

Automyx has three learning systems:

### 1. Error Learning System
- Logs errors and their context
- Extracts lessons from failures
- Provides warnings for similar situations
- Tracks error statistics

### 2. Skill Forger
- Detects repeated patterns
- Clusters similar requests
- Creates new skills automatically
- Validates and promotes successful skills

### 3. Aumformbring
- Conversational memory
- Pattern recognition
- Auto-improvement cycles
- Skill usage tracking

---

## 🔒 Security

### Permission Levels

| Level | Description | Example |
|-------|-------------|---------|
| **Safe** | No permission needed | `read_file`, `web_search` |
| **Normal** | Show what will happen | `write_file`, `execute_cmd` |
| **Caution** | Require confirmation | `delete_file`, `move_file` |
| **Dangerous** | Explicit confirmation | `system_shutdown` |

### Best Practices

1. **Review permissions** before running dangerous operations
2. **Use session permissions** for temporary access
3. **Keep API keys secure** in `.env` file
4. **Regular backups** of important data
5. **Test in safe environment** first

---

## 🐛 Troubleshooting

### Common Issues

**Issue:** "Model not found"
```bash
# Solution: Check available models
python automyx_cli.py tools
```

**Issue:** "Permission denied"
```bash
# Solution: Check permissions
python automyx_cli.py context
# Or run with --verbose
python automyx_cli.py --verbose
```

**Issue:** "API key invalid"
```bash
# Solution: Re-run setup
python automyx_cli.py onboard
```

**Issue:** "Tool not found"
```bash
# Solution: Install missing tool
# Example: ffmpeg
choco install ffmpeg  # Windows
brew install ffmpeg   # macOS
sudo apt install ffmpeg  # Linux
```

---

## 📚 Documentation

- **GitHub:** https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5
- **Issues:** https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5/issues
- **Discussions:** https://github.com/NEXORATECHNOLOGYCEO/AUTOMYX-2.5/discussions

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **NVIDIA** for providing free API access
- **OpenAI** for GPT models
- **Anthropic** for Claude models
- **Ollama** for local model support
- **Rich** for beautiful terminal UI
- **FastAPI** for the API gateway

---

**Made with ❤️ by Nexora Technology LLC**
