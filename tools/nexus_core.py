"""
AUTOMYX NEXUS CORE - Sistema avanzado inspirado en Hermes Agent
Características únicas:
1. Trajectory Compressor - Compresión de historiales de conversación
2. User Profile Modeler - Modelado profundo del usuario
3. Skill Evolution Engine - Evolución automática de habilidades
4. Memory Search with Summarization - Búsqueda con resúmenes LLM
"""
import os
import json
import re
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class TrajectoryCompressor:
    """Comprime y optimiza historiales de conversación para recall eficiente"""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.db_path = self.storage_dir / "nexus_trajectories.db"
        self._init_db()
        
    def _init_db(self):
        """Inicializa la base de datos de trayectorias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trajectories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                timestamp TEXT,
                user_input TEXT,
                agent_response TEXT,
                compressed_summary TEXT,
                tags TEXT,
                is_important INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trajectory_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trajectory_id INTEGER,
                tag TEXT,
                FOREIGN KEY(trajectory_id) REFERENCES trajectories(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def compress_conversation(self, conversation_id: str, turns: List[Dict]) -> str:
        """Comprime una conversación en un resumen estructurado"""
        # Extraer información clave
        key_points = []
        for turn in turns:
            if "user" in turn:
                key_points.append(f"USER: {turn['user'][:100]}...")
            if "agent" in turn:
                key_points.append(f"AGENT: {turn['agent'][:150]}...")
                
        compressed = "\n".join(key_points)
        
        # Guardar en DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for turn in turns:
            cursor.execute('''
                INSERT INTO trajectories 
                (conversation_id, timestamp, user_input, agent_response, compressed_summary, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                conversation_id,
                datetime.now().isoformat(),
                turn.get("user", ""),
                turn.get("agent", ""),
                compressed,
                json.dumps(self._extract_tags(turn))
            ))
            
        conn.commit()
        conn.close()
        
        return compressed
    
    def _extract_tags(self, turn: Dict) -> List[str]:
        """Extrae etiquetas clave de un turno de conversación"""
        tags = []
        text = f"{turn.get('user', '')} {turn.get('agent', '')}".lower()
        
        keywords = {
            "blender": ["blender", "3d", "modelado", "render"],
            "photo": ["foto", "imagen", "editar", "photoshop", "gimp"],
            "code": ["código", "programar", "python", "javascript", "bug"],
            "git": ["git", "commit", "push", "pull", "repository"],
            "automation": ["automatizar", "autopilot", "cron"],
            "voice": ["voz", "hablar", "llamada", "elevenlabs"]
        }
        
        for category, words in keywords.items():
            if any(word in text for word in words):
                tags.append(category)
                
        return tags
    
    def search_trajectories(self, query: str, limit: int = 10) -> List[Dict]:
        """Busca en trayectorias pasadas y devuelve resúmenes relevantes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query_lower = f"%{query.lower()}%"
        cursor.execute('''
            SELECT id, conversation_id, timestamp, compressed_summary, tags
            FROM trajectories
            WHERE user_input LIKE ? OR agent_response LIKE ? OR tags LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (query_lower, query_lower, query_lower, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "conversation_id": row[1],
                "timestamp": row[2],
                "summary": row[3],
                "tags": json.loads(row[4]) if row[4] else []
            })
            
        conn.close()
        return results


class UserProfileModeler:
    """Modelado profundo del usuario basado en interacciones"""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.profile_path = self.storage_dir / "user_profile.json"
        self._init_profile()
        
    def _init_profile(self):
        """Inicializa el perfil del usuario"""
        if not self.profile_path.exists():
            default_profile = {
                "created_at": datetime.now().isoformat(),
                "interaction_count": 0,
                "preferences": {
                    "tone": "professional",
                    "detail_level": "medium",
                    "favorite_tools": [],
                    "timezone": "UTC"
                },
                "skills_used": {},
                "topics": {},
                "recent_interactions": []
            }
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(default_profile, f, ensure_ascii=False, indent=2)
                
    def update_profile_from_interaction(self, user_input: str, agent_response: str, tools_used: List[str]):
        """Actualiza el perfil del usuario desde una interacción"""
        with open(self.profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
            
        profile["interaction_count"] += 1
        
        # Registrar herramientas usadas
        for tool in tools_used:
            if tool not in profile["skills_used"]:
                profile["skills_used"][tool] = 0
            profile["skills_used"][tool] += 1
            
        # Extraer temas
        topics = self._extract_topics(user_input + " " + agent_response)
        for topic in topics:
            if topic not in profile["topics"]:
                profile["topics"][topic] = 0
            profile["topics"][topic] += 1
            
        # Guardar interacción reciente
        profile["recent_interactions"].insert(0, {
            "timestamp": datetime.now().isoformat(),
            "input": user_input[:100],
            "tools": tools_used
        })
        
        # Mantener solo las últimas 50 interacciones
        profile["recent_interactions"] = profile["recent_interactions"][:50]
        
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
            
    def _extract_topics(self, text: str) -> List[str]:
        """Extrae temas de un texto"""
        topics = []
        text_lower = text.lower()
        
        topic_keywords = {
            "3d_modeling": ["blender", "3d", "model", "render"],
            "photo_editing": ["photo", "image", "edit", "photoshop"],
            "coding": ["code", "python", "javascript", "programming"],
            "automation": ["automate", "autopilot", "cron"],
            "git": ["git", "commit", "push", "repository"],
            "voice": ["voice", "call", "elevenlabs"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)
                
        return topics
    
    def get_profile(self) -> Dict[str, Any]:
        """Devuelve el perfil completo del usuario"""
        with open(self.profile_path, "r", encoding="utf-8") as f:
            return json.load(f)


class SkillEvolutionEngine:
    """Motor de evolución automática de habilidades"""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.skills_path = self.storage_dir / "evolved_skills.json"
        self._init_skills()
        
    def _init_skills(self):
        """Inicializa la base de habilidades evolucionadas"""
        if not self.skills_path.exists():
            with open(self.skills_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
                
    def record_skill_usage(self, skill_name: str, success: bool, feedback: str = ""):
        """Registra el uso de una habilidad para su evolución"""
        with open(self.skills_path, "r", encoding="utf-8") as f:
            skills = json.load(f)
            
        # Encontrar o crear la habilidad
        skill = next((s for s in skills if s["name"] == skill_name), None)
        if not skill:
            skill = {
                "name": skill_name,
                "created_at": datetime.now().isoformat(),
                "usage_count": 0,
                "success_count": 0,
                "versions": []
            }
            skills.append(skill)
            
        # Actualizar estadísticas
        skill["usage_count"] += 1
        if success:
            skill["success_count"] += 1
            
        # Registrar feedback si existe
        if feedback:
            skill["versions"].append({
                "timestamp": datetime.now().isoformat(),
                "feedback": feedback,
                "success": success
            })
            
        with open(self.skills_path, "w", encoding="utf-8") as f:
            json.dump(skills, f, ensure_ascii=False, indent=2)
            
    def get_skill_stats(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Devuelve estadísticas de una habilidad"""
        with open(self.skills_path, "r", encoding="utf-8") as f:
            skills = json.load(f)
            
        skill = next((s for s in skills if s["name"] == skill_name), None)
        if skill:
            success_rate = (skill["success_count"] / skill["usage_count"]) * 100 if skill["usage_count"] > 0 else 0
            return {**skill, "success_rate": round(success_rate, 2)}
        return None
    
    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Devuelve todas las habilidades evolucionadas"""
        with open(self.skills_path, "r", encoding="utf-8") as f:
            skills = json.load(f)
            
        for skill in skills:
            success_rate = (skill["success_count"] / skill["usage_count"]) * 100 if skill["usage_count"] > 0 else 0
            skill["success_rate"] = round(success_rate, 2)
            
        return sorted(skills, key=lambda x: x["success_rate"], reverse=True)


class NexusCore:
    """Núcleo principal de AUTOMYX NEXUS"""
    
    def __init__(self):
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexus_data")
        self.compressor = TrajectoryCompressor(storage_dir)
        self.user_modeler = UserProfileModeler(storage_dir)
        self.skill_engine = SkillEvolutionEngine(storage_dir)
        
    def store_and_compress(self, conversation_id: str, turns: List[Dict]) -> str:
        """Almacena y comprime una conversación"""
        return self.compressor.compress_conversation(conversation_id, turns)
        
    def search_memory(self, query: str, limit: int = 10) -> List[Dict]:
        """Busca en la memoria y devuelve resultados relevantes"""
        return self.compressor.search_trajectories(query, limit)
        
    def update_user_profile(self, user_input: str, agent_response: str, tools_used: List[str]):
        """Actualiza el perfil del usuario"""
        self.user_modeler.update_profile_from_interaction(user_input, agent_response, tools_used)
        
    def get_user_profile(self) -> Dict[str, Any]:
        """Devuelve el perfil del usuario"""
        return self.user_modeler.get_profile()
        
    def record_skill(self, skill_name: str, success: bool, feedback: str = ""):
        """Registra el uso de una habilidad"""
        self.skill_engine.record_skill_usage(skill_name, success, feedback)
        
    def get_skill_stats(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Devuelve estadísticas de una habilidad"""
        return self.skill_engine.get_skill_stats(skill_name)
        
    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Devuelve todas las habilidades"""
        return self.skill_engine.get_all_skills()
        
    def get_full_stats(self) -> Dict[str, Any]:
        """Devuelve estadísticas completas del NEXUS CORE"""
        return {
            "user_profile": self.get_user_profile(),
            "skills": self.get_all_skills()
        }


# Instancia global del NEXUS CORE
nexus_core = NexusCore()
