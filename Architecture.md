# Automyx Architecture & Engineering Principles

Este documento define las reglas de ingeniería y arquitectura del núcleo de Automyx. No es solo documentación; son los contratos técnicos que mantienen el sistema escalable, seguro y rápido, superando las bases de proyectos como OpenClaw.

## 1. El Núcleo (Core) y las Herramientas (Tools)
- **Core Agnóstico:** El núcleo de Automyx (`core/`) no debe tener conocimiento rígido de las herramientas. Las herramientas (`tools/`) se registran dinámicamente. El core solo maneja el bucle de razonamiento, la comunicación con el LLM y la inyección de contexto.
- **Fronteras Claras:** Las herramientas cruzan al núcleo únicamente a través de contratos definidos (SDK de plugins o registro de funciones). No hay código espagueti entre el core y el interior de las herramientas.
- **Canales como Transporte:** Los módulos de integración (WhatsApp, Telegram, Web) son puramente capas de transporte. No contienen lógica de negocio o de IA. Su único trabajo es enviar y recibir bytes, mapeando el estado nativo a un formato que el Gateway de Automyx entienda.

## 2. Almacenamiento y Estado (La Regla de SQLite)
- **Por defecto SQLite:** Todo el estado en tiempo de ejecución (agentes, tareas, cachés, registros, memoria) **DEBE** vivir en una base de datos SQLite (`state/automyx.sqlite`).
- **Cero JSONs para Estado:** Queda estrictamente prohibido usar archivos `.json`, `.txt` o sidecars dispersos para guardar estados del sistema.
- **Estado Canónico Único:** El entorno de ejecución (Runtime) lee y escribe únicamente en la base de datos canónica.
- **Archivos Físicos son Artefactos:** Los archivos en disco solo se usan si son el producto final (un video exportado, una imagen, un backup explícito).

## 3. Configuración y Compatibilidad (Doctor --fix)
- **Cero Compatibilidad Silenciosa:** El runtime lee solo la estructura de configuración más moderna. No aceptamos claves de configuración antiguas, renombradas o malformadas de forma silenciosa.
- **Migraciones Explícitas:** Si un cambio invalida la configuración o la base de datos de un usuario, el cambio DEBE incluir una migración en `automyx_cli.py doctor --fix`.
- **Reparación antes de Ejecución:** Todo estado heredado o corrupto se normaliza en el código del Doctor *antes* de que el runtime arranque.

## 4. Refactorización y Deuda Técnica
- **Una Sola Ruta Canónica:** Si se mejora una funcionalidad, se elimina la antigua. No mantenemos ramas de "fallback" o "shims" solo por si acaso.
- **Eliminación sobre Parche:** Frente a un fallo, prefiere una refactorización limpia que delimite la responsabilidad, en lugar de poner un parche rápido. Elimina abstracciones obsoletas y ramas muertas.
- **Código Magro (Lean):** No añadimos ramas defensivas para casos de uso hipotéticos. Programamos para estados de producción reales y documentados.

## 5. Rendimiento (Hot Paths) y Caché
- **Cero Polling en Caliente:** Las rutas de ejecución críticas (hot paths) no deben consultar repetidamente el disco (stat, read JSON, etc.). Los metadatos se preparan al inicio y se mantienen en memoria si es seguro.
- **Orden Determinista:** Los registros de herramientas, listas de plugins y cachés de prompts deben ordenarse de forma determinista antes de enviarse al LLM para optimizar el acierto en la caché del modelo.

## 6. Comentarios y Contexto
- **Comentarios In-line Obligatorios:** Las decisiones de arquitectura no obvias DEBEN documentarse in-line. 
- **Formato del Comentario:** 1-3 líneas cortas. Explica *por qué* existe esa rama, qué contrato protege y qué fallaría si se elimina. No narres la sintaxis básica de Python.

## 7. Interfaces (CLI y Web)
- **CLI como API Pública:** Los flujos de configuración del CLI (`automyx doctor`, `automyx start`) son contratos de API. Cualquier cambio debe ser compatible hacia atrás mediante flags o migraciones, ya que los instaladores y scripts dependen de ellos.

## 8. Habilidades Dinámicas (Skills) y Workshop
- **Separación de Lógica (SKILL.md):** Las habilidades que Automyx puede aprender de forma dinámica viven en la carpeta `skills/`, cada una definida en su propio archivo `SKILL.md`. Esto evita la sobrecarga del `Soul.md` principal y permite que la IA obtenga contexto "Just in Time" solo cuando lo necesita.
- **Aprendizaje Autónomo:** Automyx tiene herramientas integradas (`create_skill`, `read_skill`) para ser capaz de autogenerar sus propias macros documentadas a partir de instrucciones del usuario.

## 9. Subsistema de Memoria (Búsqueda Vectorial e Híbrida)
- **Memoria a Largo Plazo:** Las interacciones y conocimientos aprendidos que no sean habilidades procedimentales deben consolidarse en una memoria persistente en SQLite o bases vectoriales (como embeddings).
- **Decaimiento Temporal (Temporal Decay):** Los conocimientos antiguos pierden relevancia frente a los recientes para evitar que la memoria se sature de contexto obsoleto.