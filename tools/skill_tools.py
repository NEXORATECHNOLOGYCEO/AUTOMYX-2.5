import os
from tools.pc_tools import PCTools

class SkillTools:
    SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")

    @staticmethod
    def create_skill(name: str, description: str, code: str) -> str:
        try:
            skill_folder = os.path.join(SkillTools.SKILLS_DIR, name)
            os.makedirs(skill_folder, exist_ok=True)
            skill_file = os.path.join(skill_folder, "SKILL.md")
            
            content = f"---\nname: {name}\ndescription: {description}\n---\n\n{code}"
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ Habilidad '{name}' creada/actualizada exitosamente en {skill_file}"
        except Exception as e:
            return f"❌ Error creando habilidad: {str(e)}"
        
    @staticmethod
    def list_skills() -> str:
        try:
            if not os.path.exists(SkillTools.SKILLS_DIR):
                return "No hay habilidades creadas."
            skills = [d for d in os.listdir(SkillTools.SKILLS_DIR) if os.path.isdir(os.path.join(SkillTools.SKILLS_DIR, d))]
            return f"Habilidades disponibles ({len(skills)}):\n" + "\n".join(skills)
        except Exception as e:
            return f"❌ Error listando habilidades: {str(e)}"
        
    @staticmethod
    def read_skill(name: str) -> str:
        try:
            skill_file = os.path.join(SkillTools.SKILLS_DIR, name, "SKILL.md")
            if not os.path.exists(skill_file):
                return f"❌ Habilidad '{name}' no encontrada."
            with open(skill_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"❌ Error leyendo habilidad: {str(e)}"