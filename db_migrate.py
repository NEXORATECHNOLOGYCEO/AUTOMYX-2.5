import sqlite3
import json
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os

DB_PATH = "state/automyx.sqlite"

def init_db():
    os.makedirs("state", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla Agents
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        name TEXT,
        model TEXT,
        prompt TEXT,
        status TEXT,
        skills TEXT
    )
    ''')
    
    # Tabla Tasks
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        name TEXT,
        agent_id TEXT,
        prompt TEXT,
        interval_minutes INTEGER,
        status TEXT,
        next_run TEXT
    )
    ''')
    
    # Tabla Config
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def migrate_json_to_sqlite():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Migrar agents.json
    if os.path.exists("agents.json"):
        try:
            with open("agents.json", "r", encoding="utf-8") as f:
                agents = json.load(f)
            for a in agents:
                skills_json = json.dumps(a.get("skills", {"write": True, "pc": True}))
                cursor.execute(
                    "INSERT OR REPLACE INTO agents (id, name, model, prompt, status, skills) VALUES (?, ?, ?, ?, ?, ?)",
                    (a["id"], a["name"], a["model"], a["prompt"], a["status"], skills_json)
                )
            print("✅ agents.json migrado a SQLite.")
            os.remove("agents.json")
        except Exception as e:
            print(f"Error migrando agents.json: {e}")

    # Migrar tasks.json
    if os.path.exists("tasks.json"):
        try:
            with open("tasks.json", "r", encoding="utf-8") as f:
                tasks = json.load(f)
            for t in tasks:
                cursor.execute(
                    "INSERT OR REPLACE INTO tasks (id, name, agent_id, prompt, interval_minutes, status, next_run) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (t["id"], t["name"], t["agent_id"], t["prompt"], t.get("interval_minutes", 0), t["status"], t.get("next_run", ""))
                )
            print("✅ tasks.json migrado a SQLite.")
            os.remove("tasks.json")
        except Exception as e:
            print(f"Error migrando tasks.json: {e}")

    # Migrar config.json
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            for k, v in config.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                    (k, str(v))
                )
            print("✅ config.json migrado a SQLite.")
            os.remove("config.json")
        except Exception as e:
            print(f"Error migrando config.json: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    migrate_json_to_sqlite()
    print("Base de datos SQLite inicializada correctamente en state/automyx.sqlite")