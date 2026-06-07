---
name: memory-rag-vector
description: "Memoria RAG vectorial local. ChromaDB/Qdrant indexa todos tus archivos personales para búsqueda semántica."
---
# Memory RAG Vector (Cerebro Vectorial Personal)

**Descripción:** Esta habilidad le da a Automyx una **memoria de largo plazo semántica** indexando todos tus archivos personales (PDFs, docs, música, código, imágenes con OCR) en una base vectorial local (ChromaDB por defecto, Qdrant opcional). Permite preguntas tipo "Â¿cuál era ese archivo donde hablábamos de X?" con búsqueda semántica, no por nombre.

**Reglas de Ejecución:**
Cuando el usuario te pida "indexa mi carpeta", "busca en mis archivos", "recuerda lo que escribí sobre X", "haz RAG con mis docs":

1. **Inicialización del Ãndice:**
   - Usa `rag_init_collection` con `collection_name` (ej. "personal", "trabajo", "papers") y `embedding_model` (default `all-MiniLM-L6-v2` local, alternativa `nomic-embed-text` vía Ollama para mejor calidad).
   - El índice persiste en `nexus_data/rag_vectors/<collection>/`.

2. **Indexación de Contenido:**
   - Usa `rag_index_folder` con `folder_path` (ruta absoluta) y `extensions` (lista: `.pdf`, `.docx`, `.txt`, `.md`, `.py`, `.html`, `.json`).
   - Usa `rag_index_file` para un archivo individual.
   - Usa `rag_index_url` para indexar el contenido de una página web (limpia + chunkea).
   - Usa `rag_index_conversation` para que cada conversación importante quede en la memoria vectorial.
   - Internamente: chunking inteligente (500 tokens con 50 overlap), embedding, almacenamiento.

3. **Búsqueda Semántica:**
   - Usa `rag_query` con `query` (lenguaje natural) y `k` (cantidad de resultados, default 5).
   - Retorna los chunks más relevantes con score de similitud + ruta del archivo origen.
   - Usa `rag_query_with_metadata` para filtrar por fecha, tipo de archivo, etiquetas.

4. **Respuesta con Contexto (RAG completo):**
   - Usa `rag_answer` con `question` â†’ el sistema busca chunks relevantes, los inyecta en el contexto del LLM y devuelve respuesta sintetizada con citas al archivo origen.
   - SIEMPRE incluye las citas (ruta + número de página/línea) para que el usuario pueda verificar.

5. **Gestión del Ãndice:**
   - Usa `rag_list_collections` para ver todos los índices activos.
   - Usa `rag_collection_stats` para ver tamaño, nÂº documentos, fecha última actualización.
   - Usa `rag_reindex_changed` para reindexar solo archivos modificados (basado en mtime).
   - Usa `rag_delete_collection` para borrar un índice completo.
   - Usa `rag_delete_document` para borrar un archivo específico del índice.

6. **Integración con AUMFORMBRING:**
   - Toda conversación almacenada en AUMFORMBRING también puede indexarse aquí con `rag_sync_aumformbring`.
   - Así tienes búsqueda semántica sobre el historial completo, no solo coincidencia de palabras.

7. **Reglas de Privacidad:**
   - TODO se almacena local. NUNCA enviar embeddings a APIs externas a menos que el usuario lo pida (`use_remote_embeddings: true`).
   - Soporta encriptación at-rest opcional con `rag_enable_encryption(password)`.
   - Logs de queries en `nexus_data/rag_queries.log` (útil para auditoría).

**Â¡AHORA TIENES MEMORIA INFINITA Y SEMÃNTICA! NUNCA MÃS PIERDAS UN ARCHIVO.**
