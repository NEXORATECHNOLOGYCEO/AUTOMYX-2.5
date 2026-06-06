<div align="center">
  <img src="assets/logo.png" alt="Automyx Logo" width="150">
  
  <h1>AUTOMYX</h1>
  <h3>Professional Automation Suite with AI</h3>
  
  <p>The most advanced AI automation engine with full system control, 2D/3D professional editing, real-time voice, and 100% impactful autonomy.</p>
  
  <p>
    <a href="#features">Features</a> •
    <a href="#installation">Installation</a> •
    <a href="#getting-started">Getting Started</a> •
    <a href="#license">License</a>
  </p>
</div>

---

## 📖 What is Automyx?

Automyx is an open-source, all-in-one artificial intelligence automation suite that provides:
- Full control over your computer (terminal, file management, app opening)
- Professional 2D image and 3D model editing with Blender integration
- Real-time voice interaction
- Project Autopilot for autonomous project management
- Universal App Control for any desktop app
- Support for both cloud and local AI models (via Ollama)

---

## 🚀 Features

### Unique Features
- **AUMFORMBRING™**: Auto-learning and self-improvement system
- **Project Autopilot™**: Full project autonomy (analyze, detect bugs, fix, document)
- **Universal App Control™**: Total control over any desktop app using UI automation
- **Professional Gateway**: Advanced security system with access tokens
- **Fixed Port 3500**: Always accessible at http://localhost:3500

### Professional 2D & 3D Editing
- Blender integration: Create, edit, animate, and render professional 3D models
  - 3D primitives (cubes, spheres, toruses, cylinders, cones)
  - Materials, textures, and transformations
  - Animations and rendering
  - Model import/export
- Professional Photo Editor: Advanced image editing with Pillow
  - Resize, crop, rotate, flip
  - Brightness, contrast, saturation, and exposure adjustments
  - Professional filters
  - Watermarks (text and image)
  - Thumbnails and collages

### Real-Time Voice
- **ElevenLabs TTS**: Natural and professional voice
- **Speech Recognition**: Talk directly to Automyx
- **Real-Time Calls**: Fluid and natural conversations

### System Control
- **Integrated Terminal**: Execute PowerShell/CMD commands
- **File Management**: Read, write, copy, move, delete
- **Open Programs**: Launch any application
- **UI Automation**: Click, type, hotkeys, drag & drop
- **Screenshots**: Take screenshots of specific regions

### Web & Networks
- **Web Search**: Advanced searches
- **Browser Control**: Open sites, fill out forms, analyze content
- **Social Networks**: WhatsApp, Telegram, TikTok, Facebook
- **OSINT**: Open-source intelligence

### Data & DevOps
- **Data Analysis**: CSV, charts
- **Docker Management**: Container control
- **Git Integration**: Automatic commits, pushes, pulls

### Audio & Video
- **Auto-Tune**: Professional voice effects
- **Mixing & Mastering**: Studio-quality audio
- **Video Editing**: Crop, concatenate, subtitles, effects

### AI & Agents
- **Multi-Agent**: Create and manage multiple agents with different personalities
- **Skills System**: Extensible skill system
- **Persistent Memory**: Remembers past conversations
- **Ollama Support**: Local models for maximum privacy

---

## 💻 Installation

### Prerequisites
- Python 3.10 or higher
- [Ollama](https://ollama.ai/) (optional, for local models)
- [Blender](https://www.blender.org/) (optional, for 3D tools)

### Step 1: Clone or download the project
```bash
git clone <your-repository-url>
cd "AUTOMIX 2.5win, mac, rasberry pi"
```

### Step 2: Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Install the npm wrapper (for `ollama launch`)
```bash
cd npm-package
npm install -g .
```

### Step 4: Run Automyx
```bash
# Option 1: Using ollama launch (like OpenClaw)
ollama launch automyx --model llama3.1:8b

# Option 2: Using the CLI
python automix.py gateway

# Option 3: Using the npm CLI
automyx
```

### Step 5: Access the interface
Open your browser and go to: http://localhost:3500

**IMPORTANT**: Copy the gateway token that appears in the terminal and paste it into the interface to connect!

---

## 📚 Tutorial - Getting Started

### Using the Web Interface (Easiest)
1. Start Automyx (see Installation above)
2. Open http://localhost:3500 in your browser
3. Use the chat to talk directly to Automyx
4. You have access to all tools and options!

### Using the CLI
```bash
# See all available commands
python automix.py --help

# See help for a specific command
python automix.py gateway --help
```

### Using Ollama (Local Models)
Automyx supports local models via Ollama for maximum privacy:
1. Make sure Ollama is installed and running locally
2. List installed Ollama models:
   ```bash
   python automix.py ollama list
   ```

### Using the Custom Automyx Ollama Model
You can create a custom Ollama model with Automyx's system prompt using the included Modelfile:
1. Build the custom model:
   ```bash
   ollama create NEXORATECHNOLOGYGEO/automyx -f Modelfile
   ```
2. Run the custom model:
   ```bash
   ollama run NEXORATECHNOLOGYGEO/automyx
   ```
3. Or use it with Automyx:
   ```bash
   python automix.py ollama launch --model NEXORATECHNOLOGYGEO/automyx --location local
   ```

### Publishing to Ollama
To publish your model to Ollama for others to use:
1. Login to Ollama with your `NEXORATECHNOLOGYGEO` account:
   ```bash
   ollama login
   ```
2. Push your model:
   ```bash
   ollama push NEXORATECHNOLOGYGEO/automyx
   ```
3. Now anyone can use your model:
   ```bash
   ollama pull NEXORATECHNOLOGYGEO/automyx
   ```
3. Download a model if you don't have one:
   ```bash
   python automix.py ollama pull llama3.2:1b
   ```
4. Launch Automyx with a local Ollama model:
   ```bash
   # Option 1: Using the CLI
   python automix.py ollama launch --model llama3.2:1b --location local
   
   # Option 2: Using ollama_launch.py
   python ollama_launch.py --model llama3.2:1b --location local
   
   # Option 3: Using an environment variable
   $env:AUTOMYX_MODEL="ollama/llama3.2:1b"  # Windows PowerShell
   # export AUTOMYX_MODEL="ollama/llama3.2:1b"  # macOS/Linux
   python automix.py gateway
   ```

### Using the API (For Developers)
Automyx comes with a complete REST API to integrate it into your projects:
- Base URL: http://localhost:3500
- Authentication: A token is required (generated when starting the server)

### Using the Python Client
You can import and use Automyx directly in your Python scripts:
```python
from core.agent import AutomyxAgent

agent = AutomyxAgent()
response = agent.run("Tell me a joke")
print(response)
```

---

## 🔧 All Automyx Tools

| Category | Tools |
|-----------|--------------|
| System | Execute commands, file management, open programs, screenshot |
| Blender 3D | Create objects, materials, animations, render, import/export |
| Photo Editor | Edit photos, filters, watermarks, collages |
| 3D & VFX Studio | Cinematic environments, advanced physics simulations, script execution, node compositing |
| Project Autopilot | Analyze project, detect bugs, auto-improve, git, docs |
| Universal App Control | Activate windows, click, type, hotkeys, automate sequences |
| AUMFORMBRING | Auto-learning, memory, patterns, self-improvement, learned skills |
| Web | Search, browser, scraping, form filler |
| Social Networks | WhatsApp, Telegram, TikTok, Facebook |
| Audio/Video | Auto-tune, mix, edit video, subtitles |
| Data | CSV analysis, charts, Excel |
| DevOps | Docker, system resources |
| Email | Read emails, create drafts |
| HR | Read PDFs, CVs |
| Skills | Create and manage custom skills |
| Voice | ElevenLabs TTS, speech recognition |
| Scheduled Tasks | Cron jobs, automation |

---

## 📝 AUMFORMBRING - The Self-Learning Brain

AUMFORMBRING is Automyx's revolutionary self-learning system:
- **Perpetual Memory**: Automatically stores all your conversations
- **Pattern Extraction**: Learns what you frequently ask for
- **Auto-Created Skills**: When you ask "how" to do something, it saves it as a new skill
- **Continuous Self-Improvement**: Analyzes its own performance and optimizes itself
- **Smart Recall**: Remembers similar conversations to respond better

### AUMFORMBRING Commands
- "Show me your learning statistics"
- "What skills have you learned?"
- "Remember a conversation similar to [something]"
- "Search your memory about [topic]"
- "Perform a self-improvement"
- "Create a custom skill"

---

## 🔒 Security

Automyx includes a professional security system with:
- Unique gateway token generated on every startup
- Mandatory verification for all API requests
- Fixed port 3500 for secure access
- Token configuration screen in the interface

---

## 📄 License

This project is open-source and licensed under the [MIT License](LICENSE).

---

## 💡 Usage Examples

### Blender 3D
> "Create a red cube in Blender, place it in the center, and render an image"

### Photo Editing
> "Open the photo 'vacations.jpg', increase brightness by 20%, add a watermark with my name, and save it as 'vacations_edited.jpg'"

### Project Autopilot
> "Analyze my project, detect bugs, and fix them"

### Universal App Control
> "Open Notepad, type 'Hello from Automyx!', save the file, and close the window"

### Real-Time Voice
> Activate the voice button in the interface and talk directly to Automyx

### AUMFORMBRING - Auto-Learning
> "What skills have you learned so far?"
> "Show me your learning statistics"
> "Search your memory about Blender"
> "Perform a self-improvement"

---

<div align="center">
  <strong>Designed, Developed & Presented by NEXORA TECHNOLOGY LLC</strong>
  <br>
  Version 2.5 - Ultra Elite
</div>
