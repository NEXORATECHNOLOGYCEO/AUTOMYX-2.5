from __future__ import annotations

import csv
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

try:
    import psycopg2
    import psycopg2.extras
    _HAS_PSYCOPG2 = True
except ImportError:
    _HAS_PSYCOPG2 = False

try:
    import mysql.connector
    _HAS_MYSQL = True
except ImportError:
    _HAS_MYSQL = False

_INSTANCE: Optional[DatabaseAgent] = None


class DatabaseAgent:
    def __init__(self):
        self._conn = None
        self._cursor = None
        self._db_type: str = ""
        self._connected_at: Optional[datetime] = None
        self._connection_string: str = ""

    def connect(self, connection_string: str) -> dict:
        self._connection_string = connection_string
        parsed = urlparse(connection_string)
        scheme = parsed.scheme.lower()

        if scheme == "sqlite" or connection_string.startswith("sqlite:///"):
            db_path = connection_string.replace("sqlite:///", "")
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._cursor = self._conn.cursor()
            self._db_type = "sqlite"
            self._connected_at = datetime.now()
            return {"ok": True, "type": "sqlite", "database": db_path}

        elif scheme in ("postgresql", "postgres"):
            if not _HAS_PSYCOPG2:
                return {"ok": False, "error": "psycopg2 no instalado. Ejecuta: pip install psycopg2-binary"}
            self._conn = psycopg2.connect(connection_string)
            self._cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            self._db_type = "postgresql"
            self._connected_at = datetime.now()
            return {"ok": True, "type": "postgresql", "host": parsed.hostname, "database": parsed.path.lstrip("/")}

        elif scheme in ("mysql", "mysql+mysqlconnector"):
            if not _HAS_MYSQL:
                return {"ok": False, "error": "mysql-connector-python no instalado. Ejecuta: pip install mysql-connector-python"}
            self._conn = mysql.connector.connect(
                host=parsed.hostname,
                port=parsed.port or 3306,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip("/"),
            )
            self._cursor = self._conn.cursor(dictionary=True)
            self._db_type = "mysql"
            self._connected_at = datetime.now()
            return {"ok": True, "type": "mysql", "host": parsed.hostname, "database": parsed.path.lstrip("/")}

        else:
            return {"ok": False, "error": f"Tipo de base de datos no soportado: {scheme}. Usa sqlite:///, postgresql://, o mysql://"}

    def disconnect(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None
        self._cursor = None
        self._db_type = ""
        self._connected_at = None

    def get_schema(self) -> list[dict]:
        if not self.is_connected:
            return []

        tables: list[dict] = []

        if self._db_type == "sqlite":
            self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            table_names = [row[0] for row in self._cursor.fetchall()]
            for name in table_names:
                self._cursor.execute(f"PRAGMA table_info({name})")
                cols = [{"name": r[1], "type": r[2], "nullable": not r[3], "pk": bool(r[5])} for r in self._cursor.fetchall()]
                tables.append({"table": name, "columns": cols})

        elif self._db_type == "postgresql":
            self._cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
            )
            table_names = [r["table_name"] for r in self._cursor.fetchall()]
            for name in table_names:
                self._cursor.execute(
                    "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                    "WHERE table_name=%s ORDER BY ordinal_position",
                    (name,),
                )
                cols = [{"name": r["column_name"], "type": r["data_type"], "nullable": r["is_nullable"] == "YES"} for r in self._cursor.fetchall()]
                tables.append({"table": name, "columns": cols})

        elif self._db_type == "mysql":
            self._cursor.execute("SHOW TABLES")
            rows = self._cursor.fetchall()
            table_names = [list(r.values())[0] for r in rows]
            for name in table_names:
                self._cursor.execute(f"DESCRIBE `{name}`")
                cols = [{"name": r["Field"], "type": r["Type"], "nullable": r["Null"] == "YES"} for r in self._cursor.fetchall()]
                tables.append({"table": name, "columns": cols})

        return tables

    def execute_query(self, sql: str) -> dict:
        if not self.is_connected:
            return {"error": "No hay conexión activa"}

        start = time.time()
        try:
            self._cursor.execute(sql)
            duration_ms = round((time.time() - start) * 1000, 2)

            if self._cursor.description:
                columns = [d[0] for d in self._cursor.description]
                raw_rows = self._cursor.fetchall()
                if self._db_type == "sqlite":
                    rows = [list(r) for r in raw_rows]
                else:
                    rows = [list(r.values()) for r in raw_rows]
                return {"columns": columns, "rows": rows, "row_count": len(rows), "duration_ms": duration_ms}
            else:
                self._conn.commit()
                return {"columns": [], "rows": [], "row_count": self._cursor.rowcount, "duration_ms": duration_ms, "affected": self._cursor.rowcount}
        except Exception as e:
            return {"error": str(e), "duration_ms": round((time.time() - start) * 1000, 2)}

    def natural_language_query(self, question: str, llm_runner: Callable[[list], str]) -> dict:
        schema = self.get_schema()
        schema_text = ""
        for t in schema:
            cols_text = ", ".join(f"{c['name']} {c['type']}" for c in t["columns"])
            schema_text += f"- {t['table']}({cols_text})\n"

        prompt = (
            f"Eres un experto en SQL para {self._db_type}. Dado el siguiente schema:\n{schema_text}\n"
            f"Convierte esta pregunta en SQL válido: \"{question}\"\n"
            f"Responde SOLO con el SQL en un bloque ```sql ... ```. Sin explicaciones."
        )
        response = llm_runner([{"role": "user", "content": prompt}])

        sql = None
        match = re.search(r"```sql\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
        else:
            for keyword in ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH"):
                idx = response.upper().find(keyword)
                if idx != -1:
                    sql = response[idx:].strip()
                    break

        if not sql:
            return {"error": "No se pudo extraer SQL de la respuesta", "llm_response": response}

        result = self.execute_query(sql)
        result["generated_sql"] = sql
        return result

    def export_to_csv(self, sql: str, output_path: str) -> dict:
        result = self.execute_query(sql)
        if "error" in result:
            return result

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(result["columns"])
            writer.writerows(result["rows"])

        return {"ok": True, "path": str(path), "rows_written": result["row_count"]}

    def get_table_preview(self, table_name: str, limit: int = 10) -> dict:
        if self._db_type == "sqlite":
            sql = f"SELECT * FROM [{table_name}] LIMIT {limit}"
        elif self._db_type == "postgresql":
            sql = f'SELECT * FROM "{table_name}" LIMIT {limit}'
        else:
            sql = f"SELECT * FROM `{table_name}` LIMIT {limit}"
        return self.execute_query(sql)

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    @property
    def connection_info(self) -> dict:
        if not self.is_connected:
            return {"connected": False}
        parsed = urlparse(self._connection_string)
        return {
            "type": self._db_type,
            "host": parsed.hostname or "local",
            "database": parsed.path.lstrip("/") or self._connection_string.replace("sqlite:///", ""),
            "connected_at": self._connected_at.isoformat() if self._connected_at else None,
        }


def get_db_agent() -> DatabaseAgent:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = DatabaseAgent()
    return _INSTANCE
