# AUTOMYX MULTI-AGENT SYSTEM

## ✅ Implementación Completada

He implementado un sistema completo de **orquestación multi-agente** para Automyx, permitiendo la ejecución paralela de tareas complejas con múltiples agentes especializados.

---

## 🎯 Características Principales

### 1. **Descomposición Inteligente de Tareas**
- El LLM analiza la tarea principal y la divide en subtareas independientes
- Cada subtarea se asigna a un agente especializado
- Ejemplo: "Crear web profesional" → 4 subtareas (diseño, contenido, desarrollo, hosting)

### 2. **Ejecución Paralela**
- Usa `ThreadPoolExecutor` para ejecutar agentes simultáneamente
- Cada agente trabaja de forma independiente
- Máximo 4 agentes por defecto (configurable)

### 3. **Visualización en Tiempo Real**
- Panel de progreso con Rich
- Estado de cada agente (Pending, Running, Completed, Failed)
- Barras de progreso individuales
- Duración por agente

### 4. **Agregación de Resultados**
- Combina resultados de todos los agentes
- Genera reporte final en Markdown
- Muestra errores si algún agente falla

---

## 📦 Módulos Creados

### `core/multi_agent.py` (391 líneas)

**Clases principales:**

#### `AgentStatus` (Enum)
```python
PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
```

#### `AgentTask` (Dataclass)
Representa una tarea asignada a un agente:
- `agent_id`: Identificador del agente
- `task_description`: Descripción de la subtarea
- `status`: Estado actual
- `result`: Resultado de la ejecución
- `error`: Error si falló
- `start_time`, `end_time`: Timestamps
- `progress`: Progreso (0.0 - 1.0)

#### `MultiAgentPlan` (Dataclass)
Representa un plan con múltiples agentes:
- `plan_id`: ID único del plan
- `main_task`: Tarea principal
- `agents`: Lista de AgentTask
- `start_time`, `end_time`: Timestamps
- Propiedades: `duration`, `completed_agents`, `failed_agents`

#### `MultiAgentOrchestrator` (Class)
Orquesta la ejecución de múltiples agentes:

**Métodos principales:**

1. **`decompose_task(task, num_agents)`**
   - Usa el LLM para descomponer la tarea en subtareas
   - Retorna lista de strings con las subtareas
   - Fallback: genera subtareas genéricas si el LLM falla

2. **`create_plan(main_task, subtasks)`**
   - Crea un MultiAgentPlan a partir de las subtareas
   - Asigna IDs únicos a cada agente

3. **`execute_agent(agent_task, context)`**
   - Ejecuta una tarea individual
   - Crea instancia de AutomyxAgent
   - Registra herramientas
   - Ejecuta la tarea y captura resultado

4. **`execute_parallel(plan, context)`**
   - Ejecuta todos los agentes en paralelo
   - Usa ThreadPoolExecutor
   - Muestra progreso en tiempo real con Rich Live
   - Retorna el plan actualizado

5. **`aggregate_results(plan)`**
   - Combina resultados de todos los agentes
   - Genera reporte en Markdown
   - Incluye resumen de ejecución

6. **`_create_progress_display(plan)`**
   - Crea panel de progreso visual
   - Tabla con estado de cada agente
   - Barras de progreso individuales

7. **`_display_plan_completion(plan)`**
   - Muestra resumen final
   - Tabla con duración por agente
   - Contador de éxitos/fallos

---

## 🚀 Uso en el REPL

### Comando `/parallel`

```bash
# Sintaxis básica
/parallel <tarea> [--agents N]

# Ejemplos
/parallel crear una web profesional sobre IA
/parallel crear una web profesional --agents 4
/parallel analizar datos y generar reporte --agents 3
```

### Flujo de Ejecución

1. **Descomposición**
   ```
   ❯ /parallel crear una web profesional sobre IA
   
   Decomposing task into 4 subtasks...
   ```

2. **Visualización de Subtareas**
   ```
   Subtasks:
     1. Diseñar la arquitectura del sitio y crear wireframes
     2. Redactar y recopilar todo el contenido textual y visual
     3. Desarrollar el frontend con HTML5, CSS3 y JavaScript
     4. Configurar el hosting y probar el sitio web
   ```

3. **Ejecución Paralela**
   ```
   Executing 4 agents in parallel...
   
   ┌─────────────────────────────────────────────────────────────┐
   │ Multi-Agent Execution - Plan e51ff25c                      │
   ├──────────┬──────────────────────────────────┬───────────────┤
   │ Agent    │ Task                             │ Status        │
   ├──────────┼──────────────────────────────────┼───────────────┤
   │ agent_1  │ Diseñar la arquitectura...       │ ✓ Completed   │
   │ agent_2  │ Redactar y recopilar...          │ ✓ Completed   │
   │ agent_3  │ Desarrollar el frontend...       │ Running       │
   │ agent_4  │ Configurar el hosting...         │ Pending       │
   └──────────┴──────────────────────────────────┴───────────────┘
   ```

4. **Reporte Final**
   ```
   # Multi-Agent Execution Report
   
   **Plan ID:** e51ff25c
   **Main Task:** crear una web profesional sobre IA
   **Duration:** 45.2s
   **Agents:** 4
   **Completed:** 4
   **Failed:** 0
   
   ---
   
   ## Agent Results
   
   ### agent_1: Diseñar la arquitectura...
   [Resultado del agente 1]
   
   ### agent_2: Redactar y recopilar...
   [Resultado del agente 2]
   
   ...
   
   ---
   
   ## Summary
   
   Todos los 4 agentes completaron sus tareas exitosamente en 45.2s.
   ```

---

## 🎨 Visualización

### Panel de Progreso en Tiempo Real

```
╭─────────────────────────────────────────────────────────────╮
│ Multi-Agent Execution - Plan e51ff25c                      │
├──────────┬──────────────────────────────────┬───────────────┤
│ Agent    │ Task                             │ Progress      │
├──────────┼──────────────────────────────────┼───────────────┤
│ agent_1  │ Diseñar la arquitectura...       │ ██████████ 100%│
│ agent_2  │ Redactar y recopilar...          │ ████████░░ 80% │
│ agent_3  │ Desarrollar el frontend...       │ █████░░░░░ 50% │
│ agent_4  │ Configurar el hosting...         │ ░░░░░░░░░░ 0%  │
└──────────┴──────────────────────────────────┴───────────────┘
Progreso: 1/4 completados | Tiempo: 23.5s
```

### Tabla de Resultados

```
╭──────────┬──────────────────────────────────┬───────────────┬──────────╮
│ Agent    │ Task                             │ Status        │ Duration │
├──────────┼──────────────────────────────────┼───────────────┼──────────┤
│ agent_1  │ Diseñar la arquitectura...       │ ✓ Completed   │ 12.3s    │
│ agent_2  │ Redactar y recopilar...          │ ✓ Completed   │ 15.7s    │
│ agent_3  │ Desarrollar el frontend...       │ ✓ Completed   │ 18.2s    │
│ agent_4  │ Configurar el hosting...         │ ✓ Completed   │ 10.5s    │
╰──────────┴──────────────────────────────────┴───────────────┴──────────╯

✓ Plan completado: 4/4 agentes exitosos en 45.2s
```

---

## 🔧 Configuración

### Parámetros

```python
orchestrator = MultiAgentOrchestrator(
    model="openai/gpt-oss-120b",  # Modelo a usar
    max_workers=4                   # Máximo de agentes en paralelo
)
```

### Contexto Adicional

Puedes pasar contexto adicional a los agentes:

```python
context = {
    "project_name": "Mi Proyecto",
    "technology_stack": "Python, FastAPI",
    "requirements": "Debe ser responsivo"
}

plan = orchestrator.execute_parallel(plan, context=context)
```

---

## 📊 Casos de Uso

### 1. **Desarrollo Web Completo**
```bash
/parallel crear una web profesional sobre IA --agents 4
```
- Agente 1: Diseño y wireframes
- Agente 2: Contenido textual y visual
- Agente 3: Desarrollo frontend
- Agente 4: Hosting y testing

### 2. **Análisis de Datos**
```bash
/parallel analizar datos de ventas y generar reporte --agents 3
```
- Agente 1: Limpieza y preprocessing
- Agente 2: Análisis estadístico
- Agente 3: Generación de visualizaciones

### 3. **Investigación**
```bash
/parallel investigar sobre machine learning --agents 4
```
- Agente 1: Papers académicos
- Agente 2: Artículos técnicos
- Agente 3: Casos de uso industriales
- Agente 4: Tendencias futuras

### 4. **Automatización**
```bash
/parallel automatizar proceso de deployment --agents 3
```
- Agente 1: Configurar CI/CD
- Agente 2: Crear scripts de deployment
- Agente 3: Testing y validación

---

## 🎯 Ventajas

### vs. Ejecución Secuencial

| Aspecto | Secuencial | Paralelo |
|---------|------------|----------|
| **Tiempo** | 4x más lento | 4x más rápido |
| **Eficiencia** | Baja | Alta |
| **Escalabilidad** | Limitada | Excelente |
| **Complejidad** | Simple | Moderada |

### vs. Multi-threading Manual

| Aspecto | Manual | Multi-Agent |
|---------|--------|-------------|
| **Orquestación** | Manual | Automática |
| **Progreso** | No visible | Visual en tiempo real |
| **Errores** | Difícil manejo | Manejo integrado |
| **Resultados** | Manual | Agregación automática |

---

## 🐛 Manejo de Errores

### Agente Falla
```
╭──────────┬──────────────────────────────────┬───────────────┬──────────╮
│ agent_3  │ Desarrollar el frontend...       │ ✗ Failed      │ 5.2s     │
╰──────────┴──────────────────────────────────┴───────────────┴──────────╯

⚠ Plan completado con errores: 3/4 exitosos, 1 fallidos en 45.2s
```

### Descomposición Falla
Si el LLM no puede descomponer la tarea, usa fallback:
```python
# Fallback: genera subtareas genéricas
subtasks = [f"{task} - Parte {i+1}" for i in range(num_agents)]
```

---

## 📚 API Reference

### `MultiAgentOrchestrator`

#### `__init__(model=None, max_workers=4)`
Inicializa el orquestador.

#### `decompose_task(task: str, num_agents: int = 4) -> List[str]`
Descompone una tarea en subtareas.

#### `create_plan(main_task: str, subtasks: List[str]) -> MultiAgentPlan`
Crea un plan a partir de subtareas.

#### `execute_parallel(plan: MultiAgentPlan, context=None) -> MultiAgentPlan`
Ejecuta todos los agentes en paralelo.

#### `aggregate_results(plan: MultiAgentPlan) -> str`
Agrega resultados en un reporte.

#### `get_plan(plan_id: str) -> Optional[MultiAgentPlan]`
Obtiene un plan por ID.

#### `list_plans() -> List[MultiAgentPlan]`
Lista todos los planes.

---

## 🔮 Futuras Mejoras

### 1. **Agentes Especializados**
- Agente de diseño (UI/UX)
- Agente de contenido (copywriting)
- Agente de código (desarrollo)
- Agente de testing (QA)

### 2. **Comunicación entre Agentes**
- Los agentes pueden compartir resultados
- Dependencias entre subtareas
- Sincronización de estados

### 3. **Optimización Dinámica**
- Ajustar número de agentes según complejidad
- Reasignar tareas si un agente falla
- Balanceo de carga automático

### 4. **Persistencia**
- Guardar planes en disco
- Retomar planes interrumpidos
- Historial de ejecuciones

---

## 🎉 Resultado Final

Automyx ahora tiene un sistema completo de **orquestación multi-agente** que permite:

✅ Descomponer tareas complejas automáticamente  
✅ Ejecutar múltiples agentes en paralelo  
✅ Visualizar progreso en tiempo real  
✅ Manejar errores de forma robusta  
✅ Agregar resultados en reportes profesionales  

---

**Made with ❤️ by Nexora Technology LLC**

**Automyx 2.5 — Multi-Agent System · Parallel Execution · World-Class AI**
