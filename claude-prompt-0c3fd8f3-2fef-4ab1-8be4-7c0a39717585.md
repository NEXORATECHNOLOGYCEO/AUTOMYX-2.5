puedes autocrear esta habilidad y guardar en tu memoria esto, eres un programador senior profesional, y vas a trabajr con este proyecto: # Automyx 2.5 - Proyecto de Agente Autónomo (Contexto para Claude Code)

Este documento contiene el contexto de desarrollo del proyecto **Automyx 2.5** para que Claude Code entienda la arquitectura, el diseño y las últimas implementaciones, facilitando futuras mejoras.

## 📌 ¿Qué es Automyx?
Automyx 2.5 es un agente de IA autónomo ("Terminal-First") de élite diseñado para rivalizar y superar a herramientas como OpenClaw, Devin o el propio Claude Code. 

Está construido en Python y se ejecuta localmente. Sus características principales son:
- **Ejecución Autónoma de Tareas Complejas:** Capacidad de razonar y desglosar tareas multi-pasos.
- **Multi-Agente:** Sistema para dividir tareas grandes en sub-agentes ejecutándose en paralelo.
- **Sistema de Permisos (Permissions):** Validación de seguridad interactiva antes de ejecutar comandos shell o eliminar archivos.
- **Herramientas Nativas (Tools/Skills):** Manejo de sistema de archivos, ejecución de comandos, búsquedas web y cientos de skills conectadas.
- **Interfaz de Consola de Alta Gama:** Uso exhaustivo de la librería `rich` y `prompt_toolkit`/`questionary` para una UI estilo Hacker (temática "Transformers" en naranja, azul y rojo).

## 🛠️ Últimas Mejoras y Rediseño de UI
Se han aplicado mejoras masivas al diseño y al comportamiento de la terminal para imitar el flujo silencioso, fluido y profesional de Claude Code:

1. **Inline Shell y Prompting (core/repl.py):**
   - El prompt es minimalista e inmersivo.
   - Tiene una barra separadora azul superior con el nombre del proyecto (` AUTOMIX 2.5win, mac, rasberry pi `).
   - El input utiliza un chevron tricolor (`▶▶▶` en Naranja, Rojo y Azul).
   - El menú de autocompletado muestra todos los comandos (`/help`, `/model`, etc.) al escribir `/` y dar enter.

2. **Spinner Dinámico y Silencioso:**
   - Durante la ejecución se utiliza `rich.live.Live` y `rich.spinner.Spinner`.
   - Se muestra un auto-diálogo (`rationale`) en tiempo real donde el agente "habla consigo mismo" en color gris tenue (`dim`), diciendo por qué va a ejecutar algo.
   - No hay spam en la consola al completar tareas; si una tarea es exitosa, simplemente salta al siguiente paso en silencio o a la fase de "Pensando...".
   - En caso de errores o ejecución de comandos, se usan indicadores `L` o `✗` en colores rojos y azules.

3. **Ejecución Paralela de Planes (core/agent.py):**
   - El agente detecta cuando el LLM genera un JSON con `"plan_id"` y `"steps"`.
   - Se procesan las herramientas en grupos paralelos y secuenciales.
   - Se implementó un parser JSON súper robusto (Capa 0 y Fallbacks) que usa expresiones regulares para extraer planes estructurados, limpiando "trailing commas" y alucinaciones de la IA para que siempre se ejecute correctamente.
   - Durante los planes en paralelo, se muestra una barra de progreso estilo hacker (usando colores azul y rojo).

4. **Sistema de Permisos Interactivo (core/permissions.py):**
   - Antes de correr comandos peligrosos, se lanza un menú interactivo usando la librería `questionary`.
   - El menú se controla con flechas del teclado, permitiendo aceptar (una o siempre) o denegar, respetando los colores del tema.

## 📂 Estructura Principal
- `automyx_cli.py`: Punto de entrada, CLI parser y Welcome Screen.
- `core/repl.py`: Bucle interactivo, captura de inputs, comandos `/` y sistema de renderizado en vivo (Live/Spinner).
- `core/agent.py`: Cerebro del agente. Orquestación con la API (OpenAI/Ollama/Nvidia), parseo de herramientas, ejecución de tool_calls y ejecución de planes en paralelo.
- `core/permissions.py`: Reglas de seguridad y menú interactivo de `questionary`.
- `core/multi_agent.py`: Orquestador avanzado para dividir tareas complejas en sub-tareas para distintos agentes (usando ThreadPool).
- `core/json_protocol.py`: Parser blindado para respuestas de LLM.

## 🎯 ¿Cómo puede Claude Code ayudar ahora?
1. Mejorar el uso de tokens y caché en `agent.py`.
2. Crear nuevas herramientas (`tools`) para edición multimedia, git o despliegue en la nube.
3. Ampliar el sistema `AutoLearningOrchestrator` y `aumformbring` (memoria y forja de skills).
4. Refinar los prompts de `core/autonomy.py` para que el agente maneje errores de forma más creativa.
5. Optimizar llamadas asíncronas para el servidor web/gateway o herramientas de scrapping.