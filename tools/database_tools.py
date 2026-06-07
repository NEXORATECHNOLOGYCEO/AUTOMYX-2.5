"""
Database Tools - SQL/NoSQL universal
=====================================
Conexión y query a SQLite, PostgreSQL, MySQL, MongoDB.
Ejecuta queries, hace backups, schema diff, migraciones simples.
"""
from __future__ import annotations

import os
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import pymongo
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------
def sqlite_query(db_path: str, query: str, params: Optional[List[Any]] = None,
                 *, max_rows: int = 1000) -> Dict[str, Any]:
    """Ejecuta un query en SQLite."""
    if not Path(db_path).exists():
        return {"ok": False, "error": f"DB no existe: {db_path}"}
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, params or [])
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = [dict(r) for r in cur.fetchmany(max_rows)]
            result = {"ok": True, "columns": cols, "rows": rows, "count": len(rows), "truncated": cur.fetchone() is not None}
        else:
            conn.commit()
            result = {"ok": True, "rows_affected": cur.rowcount, "lastrowid": cur.lastrowid}
        conn.close()
        return result
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def sqlite_tables(db_path: str) -> Dict[str, Any]:
    """Lista las tablas y su schema."""
    if not Path(db_path).exists():
        return {"ok": False, "error": f"DB no existe: {db_path}"}
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = [{"name": r[0], "sql": r[1]} for r in cur.fetchall()]
        conn.close()
        return {"ok": True, "count": len(tables), "tables": tables}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def sqlite_backup(db_path: str, backup_path: str) -> Dict[str, Any]:
    """Crea backup consistente de la DB."""
    if not Path(db_path).exists():
        return {"ok": False, "error": f"DB no existe: {db_path}"}
    try:
        Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(backup_path)
        with dest:
            source.backup(dest)
        source.close()
        dest.close()
        size = os.path.getsize(backup_path)
        return {"ok": True, "backup": backup_path, "size_bytes": size}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def sqlite_schema_diff(db_a: str, db_b: str) -> Dict[str, Any]:
    """Compara schemas de dos SQLite DBs."""
    a = sqlite_tables(db_a)
    b = sqlite_tables(db_b)
    if not a["ok"]:
        return a
    if not b["ok"]:
        return b
    a_tables = {t["name"]: t["sql"] for t in a["tables"]}
    b_tables = {t["name"]: t["sql"] for t in b["tables"]}
    only_a = set(a_tables) - set(b_tables)
    only_b = set(b_tables) - set(a_tables)
    common = set(a_tables) & set(b_tables)
    diffs = []
    for t in common:
        if a_tables[t] != b_tables[t]:
            diffs.append({"table": t, "a": a_tables[t], "b": b_tables[t]})
    return {
        "ok": True,
        "only_in_a": sorted(only_a),
        "only_in_b": sorted(only_b),
        "modified": diffs,
    }


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------
def postgres_query(connection_string: str, query: str, params: Optional[List[Any]] = None,
                   *, max_rows: int = 1000) -> Dict[str, Any]:
    if not POSTGRES_AVAILABLE:
        return {"ok": False, "error": "instala psycopg2 (pip install psycopg2-binary)"}
    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params or [])
        if cur.description:
            rows = [dict(r) for r in cur.fetchmany(max_rows)]
            cols = [d.name for d in cur.description]
            result = {"ok": True, "columns": cols, "rows": rows, "count": len(rows)}
        else:
            conn.commit()
            result = {"ok": True, "rows_affected": cur.rowcount}
        cur.close()
        conn.close()
        return result
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# MySQL
# ---------------------------------------------------------------------------
def mysql_query(host: str, user: str, password: str, database: str, query: str,
                *, port: int = 3306, params: Optional[List[Any]] = None,
                max_rows: int = 1000) -> Dict[str, Any]:
    if not MYSQL_AVAILABLE:
        return {"ok": False, "error": "instala pymysql (pip install pymysql)"}
    try:
        conn = pymysql.connect(host=host, user=user, password=password, database=database, port=port,
                               cursorclass=pymysql.cursors.DictCursor)
        cur = conn.cursor()
        cur.execute(query, params or [])
        if cur.description:
            rows = cur.fetchmany(max_rows)
            cols = [d[0] for d in cur.description]
            result = {"ok": True, "columns": cols, "rows": rows, "count": len(rows)}
        else:
            conn.commit()
            result = {"ok": True, "rows_affected": cur.rowcount}
        cur.close()
        conn.close()
        return result
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
def mongo_find(connection_string: str, database: str, collection: str,
               filter_doc: Optional[Dict] = None, *, limit: int = 100,
               projection: Optional[Dict] = None, sort: Optional[List[Tuple]] = None) -> Dict[str, Any]:
    if not MONGODB_AVAILABLE:
        return {"ok": False, "error": "instala pymongo (pip install pymongo)"}
    try:
        client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        db = client[database]
        col = db[collection]
        cur = col.find(filter_doc or {}, projection).limit(limit)
        if sort:
            cur = cur.sort(sort)
        docs = []
        for d in cur:
            d["_id"] = str(d.get("_id"))  # ObjectId no es JSON serializable
            docs.append(d)
        client.close()
        return {"ok": True, "count": len(docs), "documents": docs}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def mongo_insert(connection_string: str, database: str, collection: str, document: Dict) -> Dict[str, Any]:
    if not MONGODB_AVAILABLE:
        return {"ok": False, "error": "instala pymongo"}
    try:
        client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        result = client[database][collection].insert_one(document)
        client.close()
        return {"ok": True, "inserted_id": str(result.inserted_id)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def mongo_aggregate(connection_string: str, database: str, collection: str, pipeline: List[Dict],
                   *, limit: int = 1000) -> Dict[str, Any]:
    if not MONGODB_AVAILABLE:
        return {"ok": False, "error": "instala pymongo"}
    try:
        client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        cur = client[database][collection].aggregate(pipeline)
        docs = []
        for d in cur:
            d["_id"] = str(d.get("_id"))
            docs.append(d)
        client.close()
        return {"ok": True, "count": len(docs), "results": docs[:limit]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------
class DatabaseTools:
    @staticmethod
    def sqlite_query(db_path: str, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        return sqlite_query(db_path, query, params)

    @staticmethod
    def sqlite_tables(db_path: str) -> Dict[str, Any]:
        return sqlite_tables(db_path)

    @staticmethod
    def sqlite_backup(db_path: str, backup_path: str) -> Dict[str, Any]:
        return sqlite_backup(db_path, backup_path)

    @staticmethod
    def sqlite_diff(db_a: str, db_b: str) -> Dict[str, Any]:
        return sqlite_schema_diff(db_a, db_b)

    @staticmethod
    def postgres_query(connection_string: str, query: str) -> Dict[str, Any]:
        return postgres_query(connection_string, query)

    @staticmethod
    def mysql_query(host: str, user: str, password: str, database: str, query: str) -> Dict[str, Any]:
        return mysql_query(host, user, password, database, query)

    @staticmethod
    def mongo_find(connection_string: str, database: str, collection: str,
                   filter_doc: Optional[Dict] = None) -> Dict[str, Any]:
        return mongo_find(connection_string, database, collection, filter_doc)

    @staticmethod
    def mongo_insert(connection_string: str, database: str, collection: str, document: Dict) -> Dict[str, Any]:
        return mongo_insert(connection_string, database, collection, document)

    @staticmethod
    def mongo_aggregate(connection_string: str, database: str, collection: str, pipeline: List[Dict]) -> Dict[str, Any]:
        return mongo_aggregate(connection_string, database, collection, pipeline)
