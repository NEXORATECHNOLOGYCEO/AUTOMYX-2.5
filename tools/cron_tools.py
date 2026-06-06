import schedule
import time
import threading
import logging
import json
import os

logger = logging.getLogger("CronTools")

class CronTools:
    """
    Inspirado en los 'cron tools' de OpenClaw.
    Permite al agente programar tareas recurrentes o en el futuro.
    """
    _scheduler_running = False

    @classmethod
    def _start_scheduler(cls):
        if not cls._scheduler_running:
            def run_schedule():
                while True:
                    schedule.run_pending()
                    time.sleep(1)
            
            t = threading.Thread(target=run_schedule, daemon=True)
            t.start()
            cls._scheduler_running = True

    @staticmethod
    def schedule_task(task_name: str, interval_minutes: int, command_to_run: str) -> str:
        """
        Programa una tarea para que el sistema la ejecute periódicamente.
        """
        try:
            CronTools._start_scheduler()
            
            # En una implementación real, esto enviaría un mensaje de vuelta al Agente para que procese el "command_to_run".
            # Por simplicidad, aquí simulamos que lo guarda en un log de crons.
            
            def job():
                print(f"\n[CRON] Ejecutando tarea programada: {task_name} -> {command_to_run}")
                # Aquí se podría inyectar el command_to_run de nuevo en el AutomyxAgent.run()
                
            schedule.every(interval_minutes).minutes.do(job).tag(task_name)
            
            return f"⏰ Tarea '{task_name}' programada exitosamente para ejecutarse cada {interval_minutes} minutos."
        except Exception as e:
            return f"❌ Error programando tarea: {str(e)}"

    @staticmethod
    def list_scheduled_tasks() -> str:
        """Lista todas las tareas cron activas."""
        jobs = schedule.get_jobs()
        if not jobs:
            return "No hay tareas programadas actualmente."
        
        result = "⏰ Tareas programadas:\n"
        for job in jobs:
            result += f"- {list(job.tags)[0]} (Cada {job.interval} {job.unit})\n"
        return result

    @staticmethod
    def cancel_task(task_name: str) -> str:
        """Cancela una tarea programada por su nombre."""
        schedule.clear(task_name)
        return f"✅ Tarea cron '{task_name}' cancelada."
