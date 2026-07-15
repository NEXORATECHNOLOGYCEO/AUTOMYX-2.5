---
name: web_development
description: Entra por SSH al VPS 82.25.91.134 (usuario root, contraseña #Ramon2025nexora) con la tool ssh_exec. 
---

# Skill auto-generada

## Tarea original
Entra por SSH al VPS 82.25.91.134 (usuario root, contraseña #Ramon2025nexora) con la tool ssh_exec. Ahí está alojada la web de Nexora Technology (nexoratechnologyllc.com), servida por nginx — su config está en /etc/nginx/sites-enabled/nexora, encuentra el root real del sitio ahí.

Objetivo: rediseña

## Pasos ejecutados (5 herramientas)
1. `ssh_exec` — nginx -T 2>/dev/null | grep -E 'root|index' | head -20; echo
2. `ssh_exec` — find /var/www -type f \( -name '*.html' -o -name '*.css' -o 
3. `ssh_exec` — netstat -tlnp 2>/dev/null | grep LISTEN; echo '---BUSQUEDA G
4. `ssh_exec` — ls -la /var/www/nexora/; echo '---'; ls -la /var/www/nexorat
5. `ssh_exec` — cat /var/www/nexora/app.py; echo '---TEMPLATES---'; ls -la /

## Resultado
El diagnóstico revela un problema crítico: **la web de `nexoratechnologyllc.com` está vacía**. El directorio `/var/www/html/` solo contiene la página de bienvenida por defecto de Nginx (`index.nginx-debian.html`). No hay archivos HTML, CSS, imágenes ni logos del sitio actual.

Esto significa que **no puedo "mejorar el diseño manteniendo el contenido actual"** porque ese contenido no existe en este directorio.

Sin embargo, al revisar los servicios activos, detecté un servidor Python (Flask) corr
