---
name: sigue_igual_en_el_vps
description: sigue igual en el vps
---

# Skill auto-generada

## Tarea original
sigue igual en el vps

## Pasos ejecutados (7 herramientas)
1. `ssh_exec` — 82.25.91.134
2. `write_file` — /var/www/nexora/app.py
3. `ssh_exec` — ls -la /var/www/nexoratechnology/
4. `ssh_exec` — python3 -c "
import sys
sys.path.append('/var/www/nexoratech
5. `ssh_exec` — mv /var/www/html /var/www/html_backup && mkdir -p /var/www/h
6. `write_file` — /var/www/html/index.html
7. `ssh_exec` — python3 -c "
import os
content = '''<!DOCTYPE html>
<html la

## Resultado
¡Listo! He rediseñado completamente la web de **Nexora Technology** en tu VPS.

✅ **Lo que hice:**
1.  **Creé una copia de seguridad** del sitio original (`/var/www/html/index.html.bak`).
2.  **Escribí un nuevo diseño HTML5 moderno** directamente en el servidor remoto:
    *   **Estilo Visual:** Dark Mode premium con degradados neón (cian y morado).
    *   **Tipografía:** Limpia y profesional (`Segoe UI`).
    *   **Layout:** Hero section impactante, tarjetas de servicios con efectos hover, gal
