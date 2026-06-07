# 📝 Changelog

All notable changes to **Automyx 2.5** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.5.0] — 2026-06-06 — The Intent-Aware Release 🚀

### ✨ Added (Major)

#### 🧠 Intent Engine v2.5 (`core/intent_engine.py`)
- 30+ intent classifier (Spanish + English)
- Slang/typo/phrase normalizer (`ahorita metele a youtube` → `play_video`)
- Entity extractor (apps, folders, URLs, dates, languages)
- 86-skill × 24-category catalog
- Tool alias resolver (`guardar_archivo` → `write_file`)
- Stem-based + fuzzy match
- New endpoints: `POST /api/intent/analyze`, `GET /api/intent/keywords`

#### ⚡ Multi-Task Dispatcher (`core/multi_task.py`)
- `ThreadPoolExecutor` with 6 workers (`AUTOMYX_MAX_WORKERS` env)
- Per-task state machine: `pending → running → streaming → completed / failed / cancelled`
- Task listeners per session
- Serial-tools queue for side-effect operations
- New endpoints: `POST /api/multitask/submit`, `GET /api/multitask/list`, `GET /api/multitask/task/{id}`, `DELETE /api/multitask/task/{id}`, `GET /api/multitask/stats`, `GET /api/multitask/wait/{id}`

#### 🛠️ Tool Alias Explosion (`tools/mega_tools.py`)
- 12,606 colloquial tool aliases (5× the original 2,500 target)
- 55 Spanish prefixes + 51 English prefixes × 16 seeds × 3 = 12,606 unique
- `max_per_seed` configurable via `AUTOMYX_MAX_ALIAS_PER_SEED` env
- Auto-dedup with `slugify`
- Wrappers delegate to canonical tools (no code duplication)

#### 🎨 Frontend (`frontend/index.html`)
- New **Multi-Tarea** sidebar + view (3-second polling, cancel buttons, progress bars)
- New **Catálogo** sidebar + view (search, collapsible categories, 86 skills)
- Live HUD for agent phases (idle → analyzing → thinking → tool_executing → responding)
- Glassmorphism theme refined

#### 🖥️ CLI (`automix.py`)
- `automix multitask submit / list / stats`
- `automix intent "phrase"`
- `automix catalog`
- `automix skill list / show / create`

#### 📚 Skills
- 86 total skills now in `skills/` marketplace
- New: `vyrex-studio-expert`, `pdf-professional-creator` (overhauled), `content-factory` (overhauled)
- Auto-loader discovers `skills/*/SKILL.md` on startup

#### 🧪 Tools
- `click_image` / `find_image_on_screen` now accept `image_name` / `path` / `file` / `template` aliases
- `write_file` / `create_directory` accept extended aliases and return actionable error messages
- `_validate_tool_call` detects missing required args and suggests the JSON schema

### 🐛 Fixed
- `click_at` tool missing → suggestion of `ui_click_image` alias
- `ui_click_image(image_name=...)` parameter mismatch → now accepts the alias
- `write_file()` with empty args → returns helpful JSON example
- Module-level logger not defined in `api/main.py` → imported

### 🔧 Changed
- `AutomyxAgent.run()` signature: `run(user_input, custom_system_prompt=None, agent_skills=None, agent_id="main", progress_callback=None)`
- `_set_phase()` is now thread-safe (`threading.RLock`)
- `Soul.md` regenerated to include the new tools + intents
- Tool documentation in `Soul.md` now lists the alias surface

### 📦 Documentation
- New `ARCHITECTURE.md` with **12 Mermaid diagrams** (root → leaves, request flow, dispatcher, intent engine, alias explosion, memory, deployment, streaming, module deps, skill lifecycle, error flow)
- README overhauled: badges, comparison table, full command reference, all 5 platforms, all 86 skills grouped by category
- Installation guides for: Windows, macOS, Linux, Raspberry Pi, Termux, VPS, Docker (coming soon)

### 📊 Stats
- 70 Python files / ~23,930 LOC
- 10 frontend files / ~4,864 LOC
- 115 .md files / ~9,000 LOC
- 86 skills × 24 categories
- 9,467 total callable tool names
- 40+ HTTP endpoints
- 30+ intents recognized

---

## [2.4.0] — 2026-05 — "Vyrex Edition"

- Blender bridge with `bpy` fallback
- PDF Pro (59K LOC) overhaul
- Video Pro (58K LOC) overhaul
- Skill Forger (auto-generate SKILL.md from patterns)
- AUMFORMBRING memory subsystem v1
- WhatsApp + Telegram bridges
- Soul.md expansion to 44K LOC

---

## [2.3.0] — 2026-03 — "Stealth RPA"

- Browser stealth (anti-detect automation)
- Nmap + OSINT integration
- Smart contract auditor
- 35+ skills launched

---

## [2.2.0] — 2026-01 — "Cross-Platform"

- Raspberry Pi support
- Termux support
- VPS deployment guide
- Optimized for 4GB RAM

---

## [2.0.0] — 2025-11 — "Nexora LLC Foundation"

- Project handed to Nexora Technology LLC
- Juan Kappler appointed Lead Architect
- AGPL-licensed core → Proprietary license
- All rights reserved

---

## [1.x] — Pre-Nexora (legacy)

- Initial prototype by community contributors
- See git history for details
