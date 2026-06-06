# Automyx Vision

Automyx es la Inteligencia Artificial que realmente **hace cosas**. Se ejecuta en tus dispositivos, en tus canales de comunicación y bajo tus propias reglas.

Este documento explica el estado actual y la dirección del proyecto. Aún estamos en una fase temprana, por lo que la iteración es rápida y constante. 
- Visión general del proyecto y documentación: `README.md`
- Configuración de la "personalidad" (Soul) del agente: `Soul.md`
- Definición y estado de los agentes: `Agents.md`

Automyx comenzó como un entorno de experimentación para aprender sobre IA y construir algo genuinamente útil: un asistente que puede ejecutar tareas reales en un ordenador real, conectarse a plataformas de mensajería (WhatsApp, Telegram) y operar con autonomía total. 

**El objetivo:** Un asistente personal omnipotente que sea fácil de usar, que soporte múltiples plataformas y canales, y que mantenga un equilibrio perfecto entre la autonomía extrema ("Ejecución Implacable") y el control del usuario.

## Enfoque Actual

**Prioridades inmediatas:**
- Seguridad y valores predeterminados seguros en la ejecución de comandos de terminal.
- Corrección de errores y estabilidad del servidor FastAPI y el motor de IA.
- Fiabilidad en la configuración y experiencia de usuario (UX) en el primer uso, especialmente en la interfaz web y la terminal.

**Próximas prioridades:**
- Soporte nativo para todos los principales proveedores de modelos (actualmente enfocados en Nvidia/OpenAI y Ollama local).
- Mejorar el soporte para canales de mensajería importantes (actualmente WhatsApp y Telegram).
- Rendimiento y tiempos de respuesta ultra-bajos (especialmente para la generación de voz con ElevenLabs).
- Mejores capacidades de uso de PC y automatización (PyAutoGUI, Playwright).
- Ergonomía consistente entre la interfaz CLI y el frontend web.

## Reglas de Contribución
- Un PR (Pull Request) = un problema/tema. No agrupes múltiples correcciones o funciones no relacionadas.
- Los PRs extremadamente grandes serán revisados solo en circunstancias excepcionales.
- No abras grandes lotes de PRs diminutos a la vez; cada revisión tiene un costo de tiempo.
- Para correcciones pequeñas y relacionadas, se recomienda agruparlas en un solo PR enfocado.

## Compatibilidad de Configuración
El código de ejecución de Automyx lee únicamente el esquema de configuración actual. No mantenemos ramas de compatibilidad a largo plazo que acepten silenciosamente claves de configuración antiguas, renombradas o mal formadas. 
Si un cambio en la configuración hace que la de un usuario deje de ser válida, ese mismo cambio debe incluir una migración clara.

## Seguridad
La seguridad en Automyx es un compromiso deliberado: **valores predeterminados fuertes sin sacrificar la capacidad operativa**. El objetivo es mantener el poder necesario para el trabajo real, haciendo que las rutas arriesgadas sean explícitas y controladas por el operador.
Priorizamos la seguridad, pero también exponemos controles claros para flujos de trabajo de alto poder en los que se confía (como la ejecución autónoma de terminal).

## Herramientas y Plugins (Skills)
Automyx tiene una arquitectura basada en herramientas directas (Tools/Skills). El núcleo (Core) se mantiene ligero en `core/agent.py`; las capacidades opcionales o específicas de un dominio (ej. `video_tools.py`, `social_tools.py`, `web_tools.py`) se agrupan en módulos independientes.

Preferimos que las nuevas capacidades se implementen como herramientas modulares en la carpeta `tools/` y se registren dinámicamente en la API. Si una característica útil no puede construirse como una herramienta aislada, damos la bienvenida a discusiones de diseño que amplíen la API del agente en lugar de agregar comportamientos únicos al núcleo.

## Configuración y Setup
Automyx es **terminal-first** y **web-first** por diseño. Esto mantiene la configuración explícita: los usuarios ven el estado del servidor, los modelos y la postura de seguridad desde el principio en la TUI (Terminal User Interface) o en el panel de control web.
A largo plazo, queremos flujos de integración más sencillos, pero **no** queremos "wrappers" de conveniencia que oculten decisiones críticas de seguridad a los usuarios.

## ¿Por qué Python y FastAPI?
Automyx es principalmente un sistema de orquestación: prompts, herramientas, protocolos de red e integraciones de IA. Python fue elegido para mantener Automyx "hackeable" por defecto. Es el lenguaje rey de la IA, rápido para iterar, y fácil de leer, modificar y extender para cualquier desarrollador. FastAPI proporciona la velocidad y la concurrencia asíncrona necesarias para manejar llamadas web y agentes en tiempo real sin bloqueos.

## Lo que NO fusionaremos (Por ahora)
- Herramientas extremadamente específicas de un nicho comercial que no beneficien a la mayoría de los usuarios.
- Integraciones de servicios comerciales que no encajen claramente en la categoría de "proveedor de modelo" o "herramienta de utilidad general".
- Frameworks de jerarquía de agentes (ej. "manager-of-managers" o árboles anidados de planificadores) como arquitectura predeterminada; preferimos la simplicidad de un Agente Omnipotente con múltiples "personalidades".
- Capas de orquestación pesadas que dupliquen la infraestructura de agentes y herramientas que ya existe.

*Esta lista es una guía de ruta, no una ley física. Una fuerte demanda de los usuarios y una sólida justificación técnica pueden cambiarla.*