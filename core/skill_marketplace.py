from __future__ import annotations

import json
import os
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

_INSTANCE: Optional[SkillMarketplace] = None

_MARKETPLACE_API = "https://api.github.com/repos/automyx-community/skills/contents/"
_CACHE_PATH = Path(os.path.expanduser("~")) / ".automyx" / "marketplace" / "cache.json"
_CACHE_TTL_SECONDS = 3600


def _fetch_url(url: str, headers: dict = {}) -> Optional[bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "automyx/2.5", **headers})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()
    except urllib.error.URLError:
        return None
    except Exception:
        return None


class SkillMarketplace:
    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir:
            self._skills_dir = Path(skills_dir)
        else:
            self._skills_dir = Path(os.getcwd()) / "skills"

        self._skills_dir.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._cache: list[dict] = self._load_cache()

    def _load_cache(self) -> list[dict]:
        if _CACHE_PATH.exists():
            try:
                data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
                if time.time() - data.get("_fetched_at", 0) < _CACHE_TTL_SECONDS:
                    return data.get("skills", [])
            except Exception:
                pass
        return []

    def _save_cache(self, skills: list[dict]):
        data = {"_fetched_at": time.time(), "skills": skills}
        _CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def refresh_cache(self) -> dict:
        raw = _fetch_url(_MARKETPLACE_API)
        if not raw:
            return {"ok": False, "error": "No se pudo conectar al marketplace. Verifica tu conexión."}

        try:
            items = json.loads(raw.decode("utf-8"))
        except Exception:
            return {"ok": False, "error": "Respuesta inválida del marketplace"}

        skills: list[dict] = []
        for item in items:
            if item.get("type") == "dir":
                skills.append({
                    "name": item["name"],
                    "id": item["name"].lower().replace(" ", "-"),
                    "url": item.get("url", ""),
                    "download_url": item.get("html_url", ""),
                    "description": f"Skill: {item['name']}",
                    "tags": [],
                    "version": "latest",
                    "author": "automyx-community",
                })

        self._cache = skills
        self._save_cache(skills)
        return {"ok": True, "count": len(skills)}

    def search(self, query: str, category: Optional[str] = None) -> list[dict]:
        if not self._cache:
            self.refresh_cache()

        results: list[dict] = []
        query_lower = query.lower()

        for skill in self._cache:
            name_match = query_lower in skill.get("name", "").lower()
            desc_match = query_lower in skill.get("description", "").lower()
            tag_match = any(query_lower in t.lower() for t in skill.get("tags", []))
            cat_match = category is None or category.lower() in skill.get("tags", [])

            if (name_match or desc_match or tag_match) and cat_match:
                results.append(skill)

        installed = {s["name"] for s in self.list_installed()}
        for r in results:
            r["installed"] = r["name"] in installed

        return results

    def install(self, skill_id_or_name: str) -> dict:
        skill_info = None
        for s in self._cache:
            if s.get("id") == skill_id_or_name or s.get("name") == skill_id_or_name:
                skill_info = s
                break

        if not skill_info and "://" in skill_id_or_name:
            url = skill_id_or_name
            name = url.split("/")[-1].replace(".zip", "")
            skill_info = {"name": name, "download_url": url}

        if not skill_info:
            if not self._cache:
                self.refresh_cache()
            for s in self._cache:
                if s.get("id") == skill_id_or_name or s.get("name") == skill_id_or_name:
                    skill_info = s
                    break

        if not skill_info:
            return {"ok": False, "error": f"Skill '{skill_id_or_name}' no encontrada en el marketplace"}

        name = skill_info["name"]
        skill_dir = self._skills_dir / name

        if skill_dir.exists():
            return {"ok": False, "error": f"Skill '{name}' ya está instalada. Usa update_all() para actualizar."}

        download_url = skill_info.get("download_url", "")
        if not download_url:
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                f"# {name}\n\nSkill instalada desde el marketplace.\n\n## Descripción\n{skill_info.get('description', '')}\n",
                encoding="utf-8",
            )
            return {"ok": True, "name": name, "path": str(skill_dir), "note": "Skill stub creada (sin código remoto disponible)"}

        raw = _fetch_url(download_url)
        if not raw:
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n\n{skill_info.get('description', '')}\n", encoding="utf-8")
            return {"ok": True, "name": name, "path": str(skill_dir), "note": "Stub creado (descarga fallida)"}

        zip_path = _CACHE_PATH.parent / f"{name}.zip"
        zip_path.write_bytes(raw)
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(skill_dir)
        except zipfile.BadZipFile:
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n\n{skill_info.get('description', '')}\n", encoding="utf-8")
        finally:
            zip_path.unlink(missing_ok=True)

        return {"ok": True, "name": name, "path": str(skill_dir)}

    def uninstall(self, skill_name: str) -> dict:
        skill_dir = self._skills_dir / skill_name
        if not skill_dir.exists():
            return {"ok": False, "error": f"Skill '{skill_name}' no está instalada"}
        shutil.rmtree(skill_dir)
        return {"ok": True, "name": skill_name, "removed": True}

    def list_installed(self) -> list[dict]:
        result: list[dict] = []
        if not self._skills_dir.exists():
            return result

        for entry in sorted(self._skills_dir.iterdir()):
            if not entry.is_dir():
                continue
            skill_md = entry / "SKILL.md"
            meta = {"name": entry.name, "path": str(entry), "has_tools": (entry / "tools.py").exists()}
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8", errors="replace")
                first_desc = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
                meta["description"] = first_desc[0] if first_desc else ""
            result.append(meta)
        return result

    def list_available(self) -> list[dict]:
        if not self._cache:
            self.refresh_cache()
        return list(self._cache)

    def publish(self, skill_name: str, description: str, tags: list[str] = []) -> dict:
        skill_dir = self._skills_dir / skill_name
        if not skill_dir.exists():
            return {"ok": False, "error": f"Skill '{skill_name}' no encontrada en {self._skills_dir}"}

        output_path = _CACHE_PATH.parent / f"{skill_name}-publish.zip"
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in skill_dir.rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(skill_dir))

        meta_path = _CACHE_PATH.parent / f"{skill_name}-meta.json"
        meta = {
            "name": skill_name,
            "description": description,
            "tags": tags,
            "version": "1.0.0",
            "author": os.environ.get("AUTOMYX_USER", "unknown"),
            "published_at": datetime.now().isoformat(),
            "zip": str(output_path),
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        return {
            "ok": True,
            "zip": str(output_path),
            "meta": str(meta_path),
            "instructions": "Para publicar: sube el ZIP y metadata a https://github.com/automyx-community/skills via PR",
        }

    def get_skill_info(self, skill_name: str) -> dict:
        installed = {s["name"]: s for s in self.list_installed()}
        available = {s.get("name", ""): s for s in self._cache}

        result: dict = {}
        if skill_name in installed:
            result.update(installed[skill_name])
            result["installed"] = True
        if skill_name in available:
            result.update({k: v for k, v in available[skill_name].items() if k not in result})
            result.setdefault("installed", False)

        if not result:
            return {"error": f"Skill '{skill_name}' no encontrada"}
        return result

    def update_all(self) -> dict:
        installed = self.list_installed()
        results: list[dict] = []
        for skill in installed:
            name = skill["name"]
            self.uninstall(name)
            res = self.install(name)
            results.append({"name": name, "ok": res.get("ok", False)})
        return {"updated": results, "count": len(results)}


def get_marketplace(skills_dir: Optional[str] = None) -> SkillMarketplace:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = SkillMarketplace(skills_dir)
    return _INSTANCE
