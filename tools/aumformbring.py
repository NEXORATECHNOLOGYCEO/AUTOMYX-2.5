"""
AUMFORMBRING - Sistema de Auto-Aprendizaje y Auto-Mejo de Automyx
Aprende de las conversaciones, extrae patrones y se mejora a sí mismo automáticamente
"""
import os
import json
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class Aumformbring:
    """Clase principal del sistema AUMFORMBRING"""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aumformbring_data")

        self.storage_dir = storage_dir
        self.memory_file = os.path.join(storage_dir, "conversation_memory.json")
        self.skills_file = os.path.join(storage_dir, "learned_skills.json")
        self.patterns_file = os.path.join(storage_dir, "learned_patterns.json")
        self.improvements_file = os.path.join(storage_dir, "auto_improvements.json")

        # Crear directorio si no existe
        os.makedirs(storage_dir, exist_ok=True)

        # Inicializar archivos de datos
        self._init_data_files()

    def _init_data_files(self):
        """Inicializa los archivos de datos si no existen"""
        for file_path in [self.memory_file, self.skills_file, self.patterns_file, self.improvements_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)

    def _load_json(self, file_path: str) -> List[Dict]:
        """Carga datos de un archivo JSON"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_json(self, file_path: str, data: List[Dict]):
        """Guarda datos en un archivo JSON"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_hash(self, text: str) -> str:
        """Genera un hash único para un texto"""
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def store_conversation(self, user_input: str, agent_response: str, metadata: Dict = None) -> str:
        """Almacena una conversación en la memoria"""
        memory = self._load_json(self.memory_file)

        conversation = {
            "id": self._generate_hash(user_input + agent_response),
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response,
            "metadata": metadata or {},
            "useful": True,
            "tags": self._extract_tags(user_input + " " + agent_response)
        }

        memory.append(conversation)
        self._save_json(self.memory_file, memory)

        # Analizar la conversación para aprendizaje automático
        self._analyze_conversation(conversation)

        return f"Conversación almacenada con ID: {conversation['id']}"

    def _extract_tags(self, text: str) -> List[str]:
        """Extrae etiquetas de un texto"""
        keywords = [
            "blender", "3d", "foto", "imagen", "editar", "autopilot", "git",
            "python", "código", "programar", "web", "automático", "voz",
            "video", "audio", "windows", "app", "archivo", "carpeta"
        ]

        tags = []
        text_lower = text.lower()

        for keyword in keywords:
            if keyword in text_lower:
                tags.append(keyword)

        return tags[:5]

    def _analyze_conversation(self, conversation: Dict):
        """Analiza una conversación para extraer conocimiento útil"""
        user_input = conversation["user_input"].lower()
        response = conversation["agent_response"]

        # Buscar patrones de comandos útiles
        self._extract_useful_patterns(conversation)

        # Si la conversación es sobre cómo hacer algo, guardarlo como skill
        if any(word in user_input for word in ["cómo", "como", "qué hacer", "que hacer", "tutorial", "paso a paso"]):
            self._learn_skill_from_conversation(conversation)

    def _extract_useful_patterns(self, conversation: Dict):
        """Extrae patrones útiles de una conversación"""
        patterns = self._load_json(self.patterns_file)
        user_input = conversation["user_input"]

        # Extraer comandos que el usuario usa frecuentemente
        pattern = {
            "id": self._generate_hash(user_input),
            "pattern": user_input[:100],
            "response_example": conversation["agent_response"][:200],
            "tags": conversation["tags"],
            "timestamp": conversation["timestamp"],
            "usage_count": 1
        }

        # Verificar si el patrón ya existe
        existing = next((p for p in patterns if p["id"] == pattern["id"]), None)
        if existing:
            existing["usage_count"] += 1
        else:
            patterns.append(pattern)

        patterns = sorted(patterns, key=lambda x: x["usage_count"], reverse=True)[:50]
        self._save_json(self.patterns_file, patterns)

    def _learn_skill_from_conversation(self, conversation: Dict):
        """Aprende una nueva habilidad de una conversación"""
        skills = self._load_json(self.skills_file)

        user_input = conversation["user_input"]
        response = conversation["agent_response"]

        # Crear una nueva habilidad aprendida
        skill = {
            "id": self._generate_hash(user_input),
            "name": f"Habilidad aprendida - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "description": user_input[:100],
            "trigger": user_input[:50],
            "response_template": response,
            "tags": conversation["tags"],
            "learned_at": conversation["timestamp"],
            "usage_count": 0,
            "success_rate": 1.0
        }

        skills.append(skill)
        self._save_json(self.skills_file, skills)

    def get_learned_skills(self) -> List[Dict]:
        """Obtiene todas las habilidades aprendidas"""
        return self._load_json(self.skills_file)

    def get_conversation_memory(self, limit: int = 20, tags: List[str] = None) -> List[Dict]:
        """Obtiene la memoria de conversaciones"""
        memory = self._load_json(self.memory_file)

        # Filtrar por etiquetas si se especifica
        if tags:
            memory = [m for m in memory if any(tag in m.get("tags", []) for tag in tags)]

        # Ordenar por fecha (más reciente primero) y limitar
        memory = sorted(memory, key=lambda x: x["timestamp"], reverse=True)[:limit]
        return memory

    def get_useful_patterns(self, limit: int = 10) -> List[Dict]:
        """Obtiene los patrones más útiles"""
        patterns = self._load_json(self.patterns_file)
        return sorted(patterns, key=lambda x: x["usage_count"], reverse=True)[:limit]

    def recall_similar_conversation(self, user_input: str) -> Optional[Dict]:
        """Recuerda una conversación similar"""
        memory = self._load_json(self.memory_file)
        input_lower = user_input.lower()

        for conv in reversed(memory):
            conv_input = conv["user_input"].lower()
            # Buscar similitud simple por palabras clave
            common_words = set(input_lower.split()) & set(conv_input.split())
            if len(common_words) >= 2:
                return conv

        return None

    def auto_improve(self, focus_area: str = None) -> Dict[str, Any]:
        """Ejecuta una auto-mejora automática"""
        improvements = self._load_json(self.improvements_file)
        memory = self._load_json(self.memory_file)
        patterns = self._load_json(self.patterns_file)

        improvement = {
            "id": self._generate_hash(datetime.now().isoformat()),
            "timestamp": datetime.now().isoformat(),
            "focus_area": focus_area,
            "analysis": {
                "total_conversations": len(memory),
                "total_patterns": len(patterns),
                "total_skills": len(self._load_json(self.skills_file)),
                "recent_activity": len([m for m in memory if (datetime.now() - datetime.fromisoformat(m["timestamp"])).days < 1])
            },
            "actions_taken": [],
            "recommendations": []
        }

        # Analizar patrones y generar recomendaciones
        if patterns:
            top_patterns = sorted(patterns, key=lambda x: x["usage_count"], reverse=True)[:3]
            improvement["recommendations"].append({
                "type": "pattern_analysis",
                "message": f"Los patrones más usados son: {', '.join([p['pattern'][:30] for p in top_patterns])}"
            })

        # Buscar oportunidades de mejora
        if len(memory) > 10:
            improvement["recommendations"].append({
                "type": "optimization",
                "message": "Muchas conversaciones almacenadas. Considera entrenar un modelo personalizado."
            })

        improvements.append(improvement)
        self._save_json(self.improvements_file, improvements)

        return improvement

    def create_custom_skill(self, name: str, trigger: str, response: str, description: str = "") -> str:
        """Crea una habilidad personalizada manualmente"""
        skills = self._load_json(self.skills_file)

        skill = {
            "id": self._generate_hash(name + trigger),
            "name": name,
            "description": description or name,
            "trigger": trigger,
            "response_template": response,
            "tags": ["custom", "manual"],
            "learned_at": datetime.now().isoformat(),
            "usage_count": 0,
            "success_rate": 1.0
        }

        skills.append(skill)
        self._save_json(self.skills_file, skills)

        return f"Habilidad personalizada '{name}' creada exitosamente!"

    def search_memory(self, query: str) -> List[Dict]:
        """Busca en la memoria de conversaciones"""
        memory = self._load_json(self.memory_file)
        query_lower = query.lower()

        results = []
        for conv in memory:
            if (query_lower in conv["user_input"].lower() or
                query_lower in conv["agent_response"].lower() or
                any(query_lower in tag.lower() for tag in conv.get("tags", []))):
                results.append(conv)

        return sorted(results, key=lambda x: x["timestamp"], reverse=True)[:10]

    def forget_conversation(self, conversation_id: str) -> str:
        """Elimina una conversación de la memoria"""
        memory = self._load_json(self.memory_file)
        initial_count = len(memory)
        memory = [m for m in memory if m["id"] != conversation_id]

        if len(memory) < initial_count:
            self._save_json(self.memory_file, memory)
            return f"Conversación {conversation_id} olvidada exitosamente"
        else:
            return f"Conversación {conversation_id} no encontrada"

    def clear_all_memory(self) -> str:
        """Limpia toda la memoria (cuidado!)"""
        self._save_json(self.memory_file, [])
        self._save_json(self.skills_file, [])
        self._save_json(self.patterns_file, [])
        return "Toda la memoria de AUMFORMBRING ha sido limpiada"

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema AUMFORMBRING"""
        return {
            "total_conversations": len(self._load_json(self.memory_file)),
            "total_learned_skills": len(self._load_json(self.skills_file)),
            "total_patterns": len(self._load_json(self.patterns_file)),
            "total_improvements": len(self._load_json(self.improvements_file)),
            "storage_location": self.storage_dir
        }


# Instancia global del sistema AUMFORMBRING
aumformbring_system = Aumformbring()
