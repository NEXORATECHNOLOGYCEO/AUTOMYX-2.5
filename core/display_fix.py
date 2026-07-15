# Corrección del conflicto de display
# Se implementa un singleton para el display principal y se desactivan las salidas visuales paralelas
import sys

class DisplayManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DisplayManager, cls).__new__(cls)
            cls._instance.active = False
        return cls._instance

    def activate(self):
        if not self.active:
            # Solo una instancia puede activar el display
            self.active = True
            return True
        return False

display_mgr = DisplayManager()
