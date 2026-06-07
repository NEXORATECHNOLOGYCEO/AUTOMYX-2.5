"""
AUTOMYX Mega Tool Aliases v2.5
==============================
Genera 2500+ aliases para tools registrados. Cada tool del agente
puede ser invocado con docenas de nombres coloquiales (español, inglés,
typos, slang) sin que el LLM tenga que recordar el nombre canónico.

Uso:
    from tools.mega_tools import expand_registry_aliases
    expand_registry_aliases(agent)
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Set, Callable, Any
from difflib import get_close_matches

# ---------------------------------------------------------------------------
# Plantillas para generar aliases automáticamente
# Formato: (prefijo_/_sufijo, descripción)
# ---------------------------------------------------------------------------
PREFIXES_ES = [
    "haz", "hazme", "ejecuta", "corre", "inicia", "arranca",
    "abre", "crea", "genera", "busca", "encuentra",
    "muestra", "lista", "obten", "trae", "carga",
    "despliega", "cancela", "para", "verifica", "valida",
    "guarda", "actualiza", "mueve", "copia", "borra",
    "combina", "compara", "ordena", "filtra", "transforma",
    "comprime", "lee", "escribe", "captura", "graba",
    "reproduce", "sube", "baja", "comparte", "envia",
    "diseña", "calcula", "simula", "predice", "indexa",
    "analiza", "sugiere", "diagnostica", "renderiza", "configura",
    "instala", "clona", "traduce", "transcribe", "sintetiza",
]

PREFIXES_EN = [
    "do", "make", "run", "execute", "open", "launch", "start",
    "create", "generate", "build", "find", "search", "show",
    "list", "get", "fetch", "deploy", "publish", "cancel",
    "verify", "check", "validate", "save", "update", "move",
    "copy", "delete", "remove", "merge", "compare", "sort",
    "filter", "transform", "compress", "read", "write", "capture",
    "play", "upload", "download", "send", "analyze", "install",
    "configure", "translate", "transcribe", "render", "diagnose",
    "simulate", "predict", "monitor", "notify", "index", "compress",
]

# Categorías de tools con sus "semillas" (keywords) para auto-generar aliases
TOOL_SEEDS: Dict[str, List[str]] = {
    # --- File system ---
    "write_file": ["write_file", "guardar_archivo", "crear_archivo", "escribir_archivo", "save", "create_file", "make_file", "put_file", "save_text", "create_document", "nuevo_archivo", "guarda_texto", "file_write", "file_save", "text_write"],
    "read_file": ["read_file", "leer_archivo", "abrir_archivo", "ver_archivo", "mostrar_archivo", "cat", "open", "view", "show_file", "file_read", "file_open", "file_view", "leer_fichero", "abre_texto"],
    "list_directory": ["list_directory", "listar_directorio", "listar_carpeta", "ls", "dir", "listar_archivos", "list_folder", "show_directory", "mostrar_carpeta", "contenido_carpeta", "file_list", "folder_list"],
    "create_directory": ["create_directory", "crear_carpeta", "nueva_carpeta", "make_dir", "mkdir", "create_folder", "new_folder", "new_directory", "mkdir_p", "carpeta_nueva", "folder_create"],
    "delete_file": ["delete_file", "borrar_archivo", "eliminar_archivo", "delete", "remove", "rm", "del", "borrar", "eliminar", "remove_file", "file_delete", "file_remove", "trash_file"],
    "copy_file": ["copy_file", "copiar_archivo", "duplicar_archivo", "copy", "cp", "duplicate_file", "file_copy", "clone_file"],
    "move_file": ["move_file", "mover_archivo", "mover", "mv", "rename_to", "trasladar", "relocate", "file_move", "file_relocate"],
    "execute_cmd": ["execute_cmd", "ejecutar_comando", "correr_comando", "cmd", "shell", "bash", "powershell", "run_cmd", "command", "terminal_cmd", "exec", "system_exec", "sh"],
    "use_terminal_window": ["use_terminal_window", "abrir_terminal", "terminal", "consola", "open_terminal", "shell_window", "new_terminal", "console", "lanzar_terminal"],

    # --- System ---
    "open_program": ["open_program", "abrir_programa", "lanzar_app", "ejecutar_app", "abrir_app", "open_app", "launch_app", "start_app", "run_app", "iniciar_app", "app_open", "program_open", "app_launch"],
    "screenshot": ["screenshot", "captura", "screenshot_pc", "captura_pantalla", "tomar_captura", "snap", "capture", "screen_grab", "screen_capture", "imagen_pantalla", "pantallazo"],
    "press_key": ["press_key", "presionar_tecla", "pulsar_tecla", "press", "push_key", "key_press", "press_button", "key", "keypress", "key_press_event"],
    "type_text": ["type_text", "escribir_texto", "tipear", "teclear", "type", "input_text", "send_text", "key_type", "write_input", "text_input"],
    "mouse_click": ["mouse_click", "click_mouse", "click", "clic", "mouse", "click_xy", "click_position", "click_at", "mouse_press"],
    "press_hotkey": ["press_hotkey", "atajo_teclado", "combinacion_teclas", "hotkey", "shortcut", "key_combo", "key_combo_press", "key_combination", "atajo"],
    "find_and_click_image": ["find_and_click_image", "click_imagen", "click_por_imagen", "image_click", "find_click", "click_template", "click_visual"],
    "wait_seconds": ["wait_seconds", "esperar", "espera", "wait", "sleep", "pause", "delay", "wait_time", "segundos_espera"],

    # --- Web ---
    "open_website": ["open_website", "abrir_web", "abrir_pagina", "ir_a", "navegar", "open_url", "goto", "visit", "web_open", "site_open", "navigate", "abrir_url", "abrir_link"],
    "web_search": ["web_search", "buscar_google", "google", "search", "search_web", "google_search", "investigar", "buscar_internet", "internet_search", "web_find"],
    "deep_web_scrape": ["deep_web_scrape", "scrape", "scrapear", "raspar_web", "scrap", "web_scrape", "extract_web", "scrape_page", "web_extract"],
    "download_video": ["download_video", "descargar_video", "bajar_video", "video_download", "fetch_video", "get_video", "save_video"],
    "play_youtube_video": ["play_youtube_video", "reproducir_youtube", "play_youtube", "yt_play", "youtube_play", "video_play", "music_play", "play_music", "play_song", "reproducir_musica", "pon_musica", "play_video"],
    "play_tiktok_desktop_video": ["play_tiktok_desktop_video", "reproducir_tiktok", "tiktok_play", "play_tiktok", "tiktok_video", "play_tt", "reproducir_tt", "ver_tiktok"],
    "analyze_browser_screen": ["analyze_browser_screen", "analizar_pantalla", "ver_pantalla", "screen_analyze", "browser_analyze", "analyze_screen", "visual_inspect"],
    "get_current_browser_url": ["get_current_browser_url", "url_actual", "current_url", "browser_url", "url_browser", "get_url", "show_url"],
    "create_web_preview": ["create_web_preview", "preview_web", "web_preview", "render_web", "html_preview", "render_preview", "open_html"],
    "ai_form_filler": ["ai_form_filler", "rellenar_formulario", "form_fill", "auto_form", "fill_form", "form_ai", "form_helper"],

    # --- Social ---
    "send_whatsapp": ["send_whatsapp", "enviar_whatsapp", "mandar_whatsapp", "wsp_send", "whatsapp_send", "send_wsp", "send_wa", "mandar_wsp"],
    "send_telegram": ["send_telegram", "enviar_telegram", "telegram_send", "tg_send", "mandar_telegram"],
    "post_facebook": ["post_facebook", "publicar_facebook", "fb_post", "facebook_post", "post_fb"],
    "upload_tiktok": ["upload_tiktok", "subir_tiktok", "tiktok_upload", "publicar_tiktok", "post_tiktok", "tt_upload"],

    # --- Video ---
    "trim_video": ["trim_video", "recortar_video", "trim", "cut_video", "video_trim", "video_cut", "split_video", "cortar_video"],
    "composite_movie_sequence": ["composite_movie_sequence", "componer_secuencia", "composite_movie", "compose_movie", "make_movie", "build_sequence"],
    "auto_subtitles": ["auto_subtitles", "subtitulos_auto", "subtitulos", "subtitles", "auto_captions", "captions", "transcribe_video"],
    "create_tiktok_edit": ["create_tiktok_edit", "edit_tiktok", "tiktok_edit", "make_tiktok", "haz_tiktok", "create_reel"],
    "advanced_video_editor": ["advanced_video_editor", "editor_video_pro", "video_editor", "editor_profesional", "video_advanced"],
    "smart_auto_edit": ["smart_auto_edit", "auto_edit", "edit_auto", "auto_video_edit", "smart_edit"],
    "add_music_to_video": ["add_music_to_video", "agregar_musica", "add_music", "music_video", "musica_a_video"],
    "apply_visual_effect": ["apply_visual_effect", "aplicar_efecto", "efecto_visual", "visual_effect", "vfx", "filter_video"],
    "add_intro_outro": ["add_intro_outro", "agregar_intro", "intro_outro", "intro", "outro", "video_intro"],
    "advanced_transition": ["advanced_transition", "transicion_avanzada", "transition", "transicion", "video_transition"],
    "professional_color_grading": ["professional_color_grading", "color_grading", "color_correction", "grading", "color_pro", "video_color"],
    "professional_audio_mastering": ["professional_audio_mastering", "audio_master", "master_audio", "audio_mastering", "audio_pro"],
    "analyze_video_content": ["analyze_video_content", "analizar_video", "video_analyze", "video_insight", "video_intel"],
    "add_dynamic_zoom": ["add_dynamic_zoom", "zoom_dinamico", "dynamic_zoom", "zoom_video", "ken_burns"],

    # --- Image ---
    "extract_text_from_image": ["extract_text_from_image", "ocr", "extraer_texto", "text_from_image", "image_to_text", "ocr_image", "read_image"],
    "generate_gemini_image": ["generate_gemini_image", "crear_imagen_ia", "generar_imagen", "dibujar", "ilustrar", "ai_image", "generate_image", "image_ai", "image_gen", "make_image", "create_picture"],
    "generate_gemini_video": ["generate_gemini_video", "crear_video_ia", "generar_video_ia", "ai_video", "generate_video", "video_ai", "video_gen", "make_video_ai"],
    "generate_vyrex_video": ["generate_vyrex_video", "video_cinematico", "cinematic_video", "video_ia_pro", "vyrex", "video_premium"],

    # --- Audio ---
    "text_to_speech": ["text_to_speech", "tts", "texto_a_voz", "speech", "voz", "synth", "say", "leer_voz", "hablar", "voice_synth"],
    "apply_autotune": ["apply_autotune", "autotune", "afinar_voz", "tune_voice", "voice_tune", "corregir_voz"],
    "mix_music": ["mix_music", "mezclar_musica", "music_mix", "mezcla", "audio_mix", "mezclar_audio"],
    "master_audio": ["master_audio", "masterizar", "audio_master", "finalizar_audio"],

    # --- 3D ---
    "generate_3d_model": ["generate_3d_model", "modelo_3d", "crear_3d", "make_3d", "3d_model", "model_3d", "generar_3d"],
    "run_blender_script": ["run_blender_script", "ejecutar_blender", "blender_script", "blender_run", "correr_blender"],
    "execute_blender_python_code": ["execute_blender_python_code", "blender_python", "python_blender", "blender_py", "blender_code"],
    "generate_professional_3d_video": ["generate_professional_3d_video", "video_3d_profesional", "3d_video", "video_3d", "professional_3d"],
    "generate_cinematic_environment": ["generate_cinematic_environment", "entorno_cinematografico", "cinematic_env", "ambiente_cine", "entorno_3d"],
    "simulate_advanced_physics": ["simulate_advanced_physics", "fisica_avanzada", "physics_sim", "simular_fisica", "physics_advanced"],
    "composite_movie_sequence": ["composite_movie_sequence", "componer_pelicula", "movie_sequence", "composite_movie", "compose_movie"],

    # --- PC / Apps ---
    "app_get_windows": ["app_get_windows", "listar_ventanas", "get_windows", "list_windows", "ventanas_abiertas", "open_windows"],
    "app_activate_window": ["app_activate_window", "activar_ventana", "focus_window", "bring_to_front", "activar_app"],
    "app_move_window": ["app_move_window", "mover_ventana", "move_window", "window_move", "posicionar_ventana"],
    "app_close_window": ["app_close_window", "cerrar_ventana", "close_window", "window_close"],
    "app_minimize_window": ["app_minimize_window", "minimizar_ventana", "minimize", "min_window"],
    "app_maximize_window": ["app_maximize_window", "maximizar_ventana", "maximize", "max_window", "fullscreen"],
    "ui_click": ["ui_click", "click_ui", "click_interfaz", "ui_tap", "ui_click_xy", "click_xy"],
    "ui_move": ["ui_move", "mover_mouse", "mover_cursor", "mouse_move", "cursor_move", "move_mouse"],
    "ui_type": ["ui_type", "escribir_ui", "type_ui", "ui_input", "ui_typing"],
    "ui_press": ["ui_press", "presionar_ui", "press_ui", "ui_button", "ui_key"],
    "ui_hotkey": ["ui_hotkey", "atajo_ui", "hotkey_ui", "ui_shortcut", "ui_combo"],
    "ui_mouse_pos": ["ui_mouse_pos", "posicion_mouse", "mouse_pos", "cursor_pos", "donde_mouse"],
    "ui_screen_size": ["ui_screen_size", "tamano_pantalla", "screen_size", "resolucion", "monitor_size"],
    "ui_screenshot_region": ["ui_screenshot_region", "captura_region", "region_screenshot", "screenshot_region"],
    "ui_find_image": ["ui_find_image", "buscar_imagen", "find_image", "image_find", "buscar_template"],
    "ui_click_image": ["ui_click_image", "click_imagen", "click_template", "image_click", "find_and_click"],
    "ui_scroll": ["ui_scroll", "scroll", "desplazar", "scroll_screen", "scroll_page"],
    "ui_drag_to": ["ui_drag_to", "arrastrar", "drag", "drag_to", "arrastrar_a"],
    "app_automate_sequence": ["app_automate_sequence", "automatizar_app", "app_sequence", "app_automate", "secuencia_app"],

    # --- Productivity / Docs ---
    "pdf_create_contract": ["pdf_create_contract", "crear_contrato", "make_contract", "contract_pdf", "contrato_pdf"],
    "pdf_create_invoice": ["pdf_create_invoice", "crear_factura", "make_invoice", "invoice_pdf", "factura_pdf"],
    "pdf_create_report": ["pdf_create_report", "crear_reporte", "make_report", "report_pdf", "reporte_pdf"],
    "pdf_create_proposal": ["pdf_create_proposal", "crear_propuesta", "make_proposal", "proposal_pdf", "propuesta_pdf"],
    "pdf_create_resume": ["pdf_create_resume", "crear_cv", "crear_curriculum", "make_resume", "cv_pdf", "resume_pdf"],
    "pdf_create_letter": ["pdf_create_letter", "crear_carta", "make_letter", "letter_pdf", "carta_pdf"],
    "pdf_create_nda": ["pdf_create_nda", "crear_nda", "make_nda", "nda_pdf"],
    "pdf_create_business_plan": ["pdf_create_business_plan", "plan_negocios", "business_plan", "plan_negocio_pdf"],
    "pdf_create_whitepaper": ["pdf_create_whitepaper", "whitepaper", "crear_whitepaper", "make_whitepaper"],
    "pdf_create_from_json": ["pdf_create_from_json", "pdf_desde_json", "json_to_pdf", "pdf_from_json"],
    "pdf_list_templates": ["pdf_list_templates", "listar_plantillas", "list_templates", "plantillas_pdf"],
    "pdf_get_template": ["pdf_get_template", "obtener_plantilla", "get_template", "show_template"],
    "pdf_list_palettes": ["pdf_list_palettes", "paletas_pdf", "list_palettes", "colores_pdf"],
    "pdf_render_chart": ["pdf_render_chart", "renderizar_grafico", "render_chart", "chart_pdf"],

    # --- Code ---
    "test_pytest": ["test_pytest", "pytest", "correr_pytest", "run_pytest", "test_python", "python_test"],
    "test_unittest": ["test_unittest", "unittest", "correr_unittest", "run_unittest"],
    "test_jest": ["test_jest", "jest", "correr_jest", "run_jest", "test_js"],
    "test_go": ["test_go", "go_test", "correr_go_test", "run_go_test"],
    "test_cargo": ["test_cargo", "cargo_test", "correr_cargo", "run_cargo"],
    "test_auto": ["test_auto", "auto_test", "detectar_test", "auto_detect_test"],
    "code_metrics": ["code_metrics", "metricas_codigo", "code_stats", "codigo_metricas"],
    "code_security_scan": ["code_security_scan", "escanear_seguridad", "security_scan", "scan_security"],
    "code_flake8": ["code_flake8", "flake8", "lint_python", "python_lint"],
    "code_black_check": ["code_black_check", "black", "black_format", "formatear_python"],
    "code_full_review": ["code_full_review", "revision_completa", "full_review", "code_review_full"],
    "opencode_run": ["opencode_run", "opencode_ejecutar", "oc_run", "opencode_exec"],
    "opencode_code_review": ["opencode_code_review", "oc_review", "opencode_review", "code_review"],
    "opencode_generate_tests": ["opencode_generate_tests", "oc_gen_tests", "opencode_tests", "generar_tests"],
    "opencode_refactor": ["opencode_refactor", "oc_refactor", "opencode_refactorizar", "refactor_code"],
    "opencode_explain": ["opencode_explain", "oc_explain", "opencode_explicar", "explain_code"],
    "opencode_generate_from_spec": ["opencode_generate_from_spec", "oc_gen_spec", "opencode_from_spec"],

    # --- GitHub ---
    "gh_status": ["gh_status", "github_status", "git_status", "status_repo"],
    "gh_list_repos": ["gh_list_repos", "listar_repos", "list_repos", "github_repos"],
    "gh_clone": ["gh_clone", "github_clone", "clone_repo", "git_clone"],
    "gh_create_repo": ["gh_create_repo", "crear_repo", "new_repo", "github_new"],
    "gh_list_issues": ["gh_list_issues", "listar_issues", "list_issues", "github_issues"],
    "gh_create_issue": ["gh_create_issue", "crear_issue", "new_issue", "github_new_issue"],
    "gh_close_issue": ["gh_close_issue", "cerrar_issue", "close_issue", "github_close_issue"],
    "gh_list_prs": ["gh_list_prs", "listar_prs", "list_prs", "github_prs"],
    "gh_create_pr": ["gh_create_pr", "crear_pr", "new_pr", "github_new_pr"],
    "gh_merge_pr": ["gh_merge_pr", "mergear_pr", "merge_pr", "github_merge"],
    "gh_list_releases": ["gh_list_releases", "listar_releases", "list_releases"],
    "gh_create_release": ["gh_create_release", "crear_release", "new_release"],
    "gh_list_workflows": ["gh_list_workflows", "listar_workflows", "list_workflows"],
    "gh_run_workflow": ["gh_run_workflow", "correr_workflow", "run_workflow"],

    # --- Deploy ---
    "deploy_detect": ["deploy_detect", "detectar_deploy", "detect_deploy", "auto_deploy"],
    "deploy_vercel": ["deploy_vercel", "vercel", "desplegar_vercel", "vercel_deploy"],
    "deploy_netlify": ["deploy_netlify", "netlify", "desplegar_netlify", "netlify_deploy"],
    "deploy_railway": ["deploy_railway", "railway", "desplegar_railway", "railway_deploy"],
    "deploy_docker_build": ["deploy_docker_build", "docker_build", "construir_docker", "build_docker"],
    "deploy_docker_push": ["deploy_docker_push", "docker_push", "subir_docker", "push_docker"],
    "deploy_docker_run": ["deploy_docker_run", "docker_run", "correr_docker", "run_docker"],
    "deploy_docker_compose": ["deploy_docker_compose", "docker_compose", "compose_up", "desplegar_compose"],
    "deploy_ssh": ["deploy_ssh", "ssh", "conectar_ssh", "ssh_connect"],
    "deploy_scp": ["deploy_scp", "scp", "copiar_scp", "scp_copy"],
    "deploy_health_check": ["deploy_health_check", "health_check", "chequear_salud", "check_health"],

    # --- Knowledge ---
    "academic_search_arxiv": ["academic_search_arxiv", "arxiv", "buscar_arxiv", "arxiv_search"],
    "academic_search_pubmed": ["academic_search_pubmed", "pubmed", "buscar_pubmed", "pubmed_search"],
    "academic_search_crossref": ["academic_search_crossref", "crossref", "buscar_crossref", "crossref_search"],
    "academic_search_semantic_scholar": ["academic_search_semantic_scholar", "semantic_scholar", "scholar_search"],
    "academic_fetch_abstract": ["academic_fetch_abstract", "fetch_abstract", "obtener_abstract", "get_abstract"],
    "academic_generate_citation": ["academic_generate_citation", "generar_cita", "citation", "make_citation"],

    # --- Accounting ---
    "accountant_parse_invoice_pdf": ["accountant_parse_invoice_pdf", "parsear_factura", "parse_invoice", "factura_parse"],
    "accountant_parse_invoice_xml": ["accountant_parse_invoice_xml", "parsear_xml_factura", "parse_xml", "xml_factura"],
    "accountant_bulk_import_folder": ["accountant_bulk_import_folder", "importar_facturas_carpeta", "bulk_import", "import_folder"],
    "accountant_reconcile_bank_statement": ["accountant_reconcile_bank_statement", "conciliar_banco", "reconcile_bank", "bank_reconcile"],
    "accountant_calculate_tax": ["accountant_calculate_tax", "calcular_impuesto", "calculate_tax", "tax_calc"],
    "accountant_validate_tax_id": ["accountant_validate_tax_id", "validar_rfc", "validate_tax_id", "rfc_check"],
    "accountant_generate_afip_report": ["accountant_generate_afip_report", "reporte_afip", "afip_report", "generar_afip"],
    "accountant_generate_sat_report": ["accountant_generate_sat_report", "reporte_sat", "sat_report", "generar_sat"],
    "accountant_generate_sunat_report": ["accountant_generate_sunat_report", "reporte_sunat", "sunat_report", "generar_sunat"],
    "accountant_generate_aeat_report": ["accountant_generate_aeat_report", "reporte_aeat", "aeat_report", "generar_aeat"],
    "accountant_generate_financial_report": ["accountant_generate_financial_report", "reporte_financiero", "financial_report"],

    # --- Crypto ---
    "crypto_price": ["crypto_price", "precio_crypto", "crypto_precio", "coin_price"],
    "crypto_prices_batch": ["crypto_prices_batch", "precios_batch", "batch_prices", "crypto_batch"],
    "crypto_convert": ["crypto_convert", "convertir_crypto", "convert_crypto", "crypto_calc"],
    "crypto_market": ["crypto_market", "mercado_crypto", "crypto_mercado", "market_crypto"],
    "crypto_trending": ["crypto_trending", "crypto_tendencia", "trending_crypto"],
    "crypto_history": ["crypto_history", "historial_crypto", "crypto_historial"],
    "crypto_technical_analysis": ["crypto_technical_analysis", "analisis_tecnico", "technical_analysis", "ta_crypto"],
    "crypto_generate_wallet": ["crypto_generate_wallet", "generar_wallet", "create_wallet", "wallet_create"],

    # --- RAG / Memory ---
    "rag_init_collection": ["rag_init_collection", "iniciar_coleccion", "init_collection"],
    "rag_list_collections": ["rag_list_collections", "listar_colecciones", "list_collections"],
    "rag_collection_stats": ["rag_collection_stats", "stats_coleccion", "collection_stats"],
    "rag_delete_collection": ["rag_delete_collection", "borrar_coleccion", "delete_collection"],
    "rag_index_file": ["rag_index_file", "indexar_archivo", "index_file"],
    "rag_index_folder": ["rag_index_folder", "indexar_carpeta", "index_folder"],
    "rag_index_url": ["rag_index_url", "indexar_url", "index_url"],
    "rag_index_conversation": ["rag_index_conversation", "indexar_conversacion", "index_conversation"],
    "rag_query": ["rag_query", "consultar_rag", "rag_consultar", "query_rag"],
    "rag_answer": ["rag_answer", "responder_rag", "rag_answer"],
    "rag_delete_document": ["rag_delete_document", "borrar_doc_rag", "delete_doc_rag"],
    "rag_sync_aumformbring": ["rag_sync_aumformbring", "sync_rag", "sincronizar_rag"],

    # --- Document Intelligence ---
    "doc_ocr": ["doc_ocr", "ocr_doc", "ocr_documento", "ocr_text"],
    "doc_ocr_pdf": ["doc_ocr_pdf", "ocr_pdf", "pdf_ocr"],
    "doc_entities": ["doc_entities", "entidades", "ner", "entities_doc"],
    "doc_classify": ["doc_classify", "clasificar_doc", "doc_clasificacion"],
    "doc_summarize": ["doc_summarize", "resumir_doc", "doc_resumen", "summarize_doc"],
    "doc_outline": ["doc_outline", "outline_doc", "esquema_doc"],
    "doc_compare": ["doc_compare", "comparar_doc", "doc_diferencia", "doc_diff"],

    # --- Notion / Obsidian ---
    "notion_search": ["notion_search", "buscar_notion", "search_notion"],
    "notion_get_page": ["notion_get_page", "obtener_pagina", "get_page"],
    "notion_create_page": ["notion_create_page", "crear_pagina_notion", "new_page_notion"],
    "notion_update_page": ["notion_update_page", "actualizar_pagina", "update_page"],
    "obsidian_search": ["obsidian_search", "buscar_obsidian", "search_obsidian"],
    "obsidian_create_note": ["obsidian_create_note", "crear_nota_obsidian", "new_note_obsidian"],
    "obsidian_read_note": ["obsidian_read_note", "leer_nota", "read_note_obsidian"],
    "obsidian_daily": ["obsidian_daily", "nota_diaria", "daily_note"],

    # --- Translation ---
    "translate_text": ["translate_text", "traducir_texto", "traduce", "translate", "traductor"],
    "translate_detect": ["translate_detect", "detectar_idioma", "detect_language"],
    "translate_batch": ["translate_batch", "traducir_batch", "batch_translate"],
    "translate_languages": ["translate_languages", "listar_idiomas", "list_languages"],

    # --- Calendar ---
    "cal_add": ["cal_add", "agregar_evento", "add_event", "nuevo_evento"],
    "cal_list": ["cal_list", "listar_eventos", "list_events", "calendario_lista"],
    "cal_delete": ["cal_delete", "borrar_evento", "delete_event"],
    "cal_find_free": ["cal_find_free", "encontrar_libre", "find_free_time", "tiempo_libre"],

    # --- Database ---
    "db_sqlite_query": ["db_sqlite_query", "query_sqlite", "consultar_sqlite"],
    "db_sqlite_tables": ["db_sqlite_tables", "tablas_sqlite", "list_tables_sqlite"],
    "db_postgres_query": ["db_postgres_query", "query_postgres", "consultar_postgres"],
    "db_mysql_query": ["db_mysql_query", "query_mysql", "consultar_mysql"],
    "db_mongo_find": ["db_mongo_find", "mongo_find", "buscar_mongo"],
    "db_mongo_insert": ["db_mongo_insert", "mongo_insert", "insertar_mongo"],

    # --- Cyber ---
    "port_scan": ["port_scan", "escanear_puertos", "scan_ports", "puertos_scan"],
    "run_nmap_scan": ["run_nmap_scan", "nmap", "escanear_nmap", "nmap_scan"],
    "osint_search": ["osint_search", "buscar_osint", "osint_find", "investigar_persona"],

    # --- Swarm ---
    "swarm_register_node": ["swarm_register_node", "registrar_nodo", "register_node"],
    "swarm_list_nodes": ["swarm_list_nodes", "listar_nodos", "list_nodes"],
    "swarm_dispatch_task": ["swarm_dispatch_task", "despachar_tarea", "dispatch_task"],
    "swarm_dispatch_parallel": ["swarm_dispatch_parallel", "despachar_paralelo", "dispatch_parallel"],
    "swarm_pipeline": ["swarm_pipeline", "pipeline_swarm", "pipeline_tareas"],
    "swarm_consensus": ["swarm_consensus", "consenso_swarm", "consensus"],

    # --- Forge ---
    "forger_analyze_patterns": ["forger_analyze_patterns", "analizar_patrones", "analyze_patterns"],
    "forger_forge_skill": ["forger_forge_skill", "forjar_skill", "forge_skill"],
    "forger_validate_skill": ["forger_validate_skill", "validar_skill", "validate_skill"],
    "forger_run_cycle": ["forger_run_cycle", "correr_ciclo", "run_cycle_forge"],
    "forger_list_forged_skills": ["forger_list_forged_skills", "listar_forjadas", "list_forged"],

    # --- Stealth Browser ---
    "stealth_launch_browser": ["stealth_launch_browser", "lanzar_navegador_oculto", "stealth_browser"],
    "stealth_goto": ["stealth_goto", "ir_stealth", "goto_stealth"],
    "stealth_human_click": ["stealth_human_click", "click_humano", "human_click"],
    "stealth_human_type": ["stealth_human_type", "escribir_humano", "human_type"],
    "stealth_solve_recaptcha_v2": ["stealth_solve_recaptcha_v2", "resolver_recaptcha", "solve_recaptcha"],
    "stealth_solve_cloudflare": ["stealth_solve_cloudflare", "resolver_cloudflare", "solve_cloudflare"],
    "stealth_screenshot_full_page": ["stealth_screenshot_full_page", "captura_completa", "full_screenshot"],
    "stealth_close_browser": ["stealth_close_browser", "cerrar_stealth", "close_stealth"],

    # --- Livestream ---
    "livestream_obs_connect": ["livestream_obs_connect", "conectar_obs", "obs_connect"],
    "livestream_obs_start_stream": ["livestream_obs_start_stream", "iniciar_stream", "start_stream"],
    "livestream_obs_stop_stream": ["livestream_obs_stop_stream", "parar_stream", "stop_stream"],
    "livestream_obs_start_recording": ["livestream_obs_start_recording", "iniciar_grabacion", "start_recording"],
    "livestream_obs_stop_recording": ["livestream_obs_stop_recording", "parar_grabacion", "stop_recording"],
    "livestream_obs_switch_scene": ["livestream_obs_switch_scene", "cambiar_escena", "switch_scene"],
    "livestream_set_moderation_rules": ["livestream_set_moderation_rules", "reglas_moderacion", "moderation_rules"],

    # --- Task Coordinator ---
    "task_coord_resolve_path": ["task_coord_resolve_path", "resolver_path", "resolve_path"],
    "task_coord_find_files": ["task_coord_find_files", "encontrar_archivos", "find_files"],
    "task_coord_parse_intent": ["task_coord_parse_intent", "parsear_intent", "parse_intent"],
    "task_coord_build_plan": ["task_coord_build_plan", "construir_plan", "build_plan"],
    "task_coord_verify_preconditions": ["task_coord_verify_preconditions", "verificar_precondiciones", "verify_preconditions"],
    "task_coord_verify_outputs": ["task_coord_verify_outputs", "verificar_outputs", "verify_outputs"],

    # --- Error Learning ---
    "error_learn_log": ["error_learn_log", "registrar_error", "log_error"],
    "error_learn_get_lessons": ["error_learn_get_lessons", "obtener_lecciones", "get_lessons"],
    "error_learn_stats": ["error_learn_stats", "stats_errores", "error_stats"],
    "error_learn_add_manual": ["error_learn_add_manual", "agregar_leccion", "add_lesson"],

    # --- Aumformbring ---
    "aumformbring_store": ["aumformbring_store", "almacenar_conversacion", "store_conversation"],
    "aumformbring_get_skills": ["aumformbring_get_skills", "obtener_skills", "get_learned_skills"],
    "aumformbring_get_memory": ["aumformbring_get_memory", "obtener_memoria", "get_memory"],
    "aumformbring_auto_improve": ["aumformbring_auto_improve", "auto_mejorar", "auto_improve"],
    "aumformbring_create_skill": ["aumformbring_create_skill", "crear_skill", "create_custom_skill"],
    "aumformbring_recall": ["aumformbring_recall", "recordar", "recall_similar"],
    "aumformbring_search": ["aumformbring_search", "buscar_memoria", "search_memory"],
    "aumformbring_stats": ["aumformbring_stats", "stats_memoria", "memory_stats"],

    # --- Nexus ---
    "nexus_store": ["nexus_store", "almacenar_nexus", "nexus_save"],
    "nexus_search": ["nexus_search", "buscar_nexus", "nexus_find"],
    "nexus_profile": ["nexus_profile", "perfil_usuario", "user_profile"],
    "nexus_skill_stats": ["nexus_skill_stats", "stats_skills", "skill_stats"],
    "nexus_all_skills": ["nexus_all_skills", "todas_skills", "all_skills"],

    # --- Cron / Tasks ---
    "schedule_task": ["schedule_task", "programar_tarea", "cron_task", "schedule"],
    "list_tasks": ["list_tasks", "listar_tareas", "show_tasks"],
    "delete_task": ["delete_task", "borrar_tarea", "cancel_task"],

    # --- JSON / Data ---
    "json_validate": ["json_validate", "validar_json", "validate_json", "json_check"],
    "json_repair": ["json_repair", "reparar_json", "repair_json", "fix_json"],
    "json_pretty": ["json_pretty", "embellecer_json", "pretty_json", "format_json"],
    "json_minify": ["json_minify", "minificar_json", "minify_json"],
    "json_query": ["json_query", "consultar_json", "jsonpath", "json_query_path"],
    "json_diff": ["json_diff", "diferencia_json", "compare_json"],
    "json_merge": ["json_merge", "fusionar_json", "merge_json"],
    "json_stats": ["json_stats", "estadisticas_json", "json_info"],

    # --- RAG: extender ---
    "rag_advanced": ["rag_advanced", "rag_pro", "rag_plus"],
    "rag_hybrid": ["rag_hybrid", "rag_hibrido"],

    # --- X (Twitter) / Instagram / FB ---
    "post_twitter": ["post_twitter", "twittear", "tweet", "publish_tweet"],
    "post_instagram": ["post_instagram", "postear_instagram", "ig_post", "instagram_post"],
    "post_linkedin": ["post_linkedin", "postear_linkedin", "li_post"],
    "post_youtube_video": ["post_youtube_video", "subir_youtube", "upload_yt", "yt_upload"],
    "post_twitch_clip": ["post_twitch_clip", "twitch_clip", "clip_twitch"],
    "send_email": ["send_email", "enviar_email", "mandar_correo", "email_send"],
    "send_sms": ["send_sms", "enviar_sms", "mandar_sms", "sms_send"],
    "send_discord": ["send_discord", "enviar_discord", "discord_send"],
    "send_slack": ["send_slack", "enviar_slack", "slack_send"],
    "send_matrix": ["send_matrix", "enviar_matrix", "matrix_send"],
    "send_signal": ["send_signal", "enviar_signal", "signal_send"],
    "send_imessage": ["send_imessage", "enviar_imessage", "imessage_send"],
    "send_line": ["send_line", "enviar_line", "line_send"],

    # --- Calendario extendido ---
    "cal_google_status": ["cal_google_status", "estado_google_calendar", "google_cal_status"],
    "cal_google_add": ["cal_google_add", "google_agregar", "google_add_event"],
    "cal_ical_export": ["cal_ical_export", "exportar_ical", "ical_export"],

    # --- Backup / Restore ---
    "backup_create": ["backup_create", "crear_backup", "make_backup"],
    "backup_restore": ["backup_restore", "restaurar_backup", "restore_backup"],
    "backup_list": ["backup_list", "listar_backups", "list_backups"],

    # --- Quick / Shortcuts ---
    "quick_screenshot": ["quick_screenshot", "screenshot_rapido", "snap_rapido"],
    "quick_search": ["quick_search", "busqueda_rapida", "fast_search"],
    "quick_note": ["quick_note", "nota_rapida", "fast_note", "quick_memo"],
    "quick_calendar": ["quick_calendar", "calendario_rapido", "fast_calendar"],
    "quick_email": ["quick_email", "email_rapido", "fast_email"],
    "quick_reminder": ["quick_reminder", "recordatorio_rapido", "fast_reminder"],

    # --- AI Smart ---
    "ai_summarize_url": ["ai_summarize_url", "resumir_url", "summarize_url"],
    "ai_summarize_pdf": ["ai_summarize_pdf", "resumir_pdf", "summarize_pdf"],
    "ai_summarize_video": ["ai_summarize_video", "resumir_video", "summarize_video"],
    "ai_translate_doc": ["ai_translate_doc", "traducir_doc", "translate_doc"],
    "ai_classify_image": ["ai_classify_image", "clasificar_imagen", "classify_image"],
    "ai_detect_objects": ["ai_detect_objects", "detectar_objetos", "detect_objects"],
    "ai_extract_text": ["ai_extract_text", "extraer_texto_ia", "ai_ocr"],
    "ai_face_detect": ["ai_face_detect", "detectar_caras", "face_detect"],
    "ai_moderate_content": ["ai_moderate_content", "moderar_contenido", "moderate"],
    "ai_grammar_check": ["ai_grammar_check", "corregir_gramatica", "grammar_check"],
    "ai_plagiarism_check": ["ai_plagiarism_check", "detectar_plagio", "plagiarism_check"],
    "ai_sentiment": ["ai_sentiment", "analisis_sentimiento", "sentiment"],

    # --- Multi-idioma (50+ variantes) ---
    "translate_en_es": ["translate_en_es", "ingles_espanol", "en_a_es", "english_to_spanish"],
    "translate_es_en": ["translate_es_en", "espanol_ingles", "es_a_en", "spanish_to_english"],
    "translate_en_fr": ["translate_en_fr", "ingles_frances", "en_a_fr", "english_to_french"],
    "translate_fr_en": ["translate_fr_en", "frances_ingles", "fr_a_en"],
    "translate_en_de": ["translate_en_de", "ingles_aleman", "en_a_de"],
    "translate_de_en": ["translate_de_en", "aleman_ingles", "de_a_en"],
    "translate_en_pt": ["translate_en_pt", "ingles_portugues", "en_a_pt"],
    "translate_pt_en": ["translate_pt_en", "portugues_ingles", "pt_a_en"],
    "translate_en_zh": ["translate_en_zh", "ingles_chino", "en_a_zh"],
    "translate_zh_en": ["translate_zh_en", "chino_ingles", "zh_a_en"],
    "translate_en_ja": ["translate_en_ja", "ingles_japones", "en_a_ja"],
    "translate_ja_en": ["translate_ja_en", "japones_ingles", "ja_a_en"],
    "translate_en_ko": ["translate_en_ko", "ingles_coreano", "en_a_ko"],
    "translate_ko_en": ["translate_ko_en", "coreano_ingles", "ko_a_en"],
    "translate_en_ru": ["translate_en_ru", "ingles_ruso", "en_a_ru"],
    "translate_ru_en": ["translate_ru_en", "ruso_ingles", "ru_a_en"],
    "translate_en_it": ["translate_en_it", "ingles_italiano", "en_a_it"],
    "translate_it_en": ["translate_it_en", "italiano_ingles", "it_a_en"],
    "translate_en_ar": ["translate_en_ar", "ingles_arabe", "en_a_ar"],
    "translate_ar_en": ["translate_ar_en", "arabe_ingles", "ar_a_en"],
    "translate_en_hi": ["translate_en_hi", "ingles_hindi", "en_a_hi"],
    "translate_hi_en": ["translate_hi_en", "hindi_ingles", "hi_a_en"],

    # --- Voice / TTS ---
    "tts_spanish": ["tts_spanish", "voz_espanol", "hablar_espanol"],
    "tts_english": ["tts_english", "voz_ingles", "hablar_ingles"],
    "tts_french": ["tts_french", "voz_frances", "hablar_frances"],
    "tts_german": ["tts_german", "voz_aleman", "hablar_aleman"],
    "tts_clone_voice": ["tts_clone_voice", "clonar_voz", "voice_clone"],

    # --- STT (Speech to text) ---
    "stt_spanish": ["stt_spanish", "transcribir_espanol", "speech_to_text_es"],
    "stt_english": ["stt_english", "transcribir_ingles", "speech_to_text_en"],
    "stt_auto": ["stt_auto", "transcribir_auto", "auto_stt"],

    # --- Weather ---
    "weather_current": ["weather_current", "clima_actual", "current_weather"],
    "weather_forecast": ["weather_forecast", "pronostico", "weather_7d"],
    "weather_alerts": ["weather_alerts", "alertas_clima", "weather_warnings"],

    # --- Maps / Geo ---
    "maps_search_place": ["maps_search_place", "buscar_lugar", "find_place", "place_search"],
    "maps_directions": ["maps_directions", "obtener_ruta", "get_directions", "route"],
    "maps_geocode": ["maps_geocode", "geocodificar", "geocode"],
    "maps_reverse_geocode": ["maps_reverse_geocode", "geocode_inverso", "reverse_geocode"],
    "maps_nearby": ["maps_nearby", "lugares_cercanos", "nearby_places"],
    "maps_distance": ["maps_distance", "calcular_distancia", "compute_distance"],

    # --- Productivity (extendido) ---
    "todo_add": ["todo_add", "agregar_tarea", "add_todo", "nueva_tarea"],
    "todo_list": ["todo_list", "listar_todos", "list_todos", "mis_tareas"],
    "todo_done": ["todo_done", "marcar_hecho", "complete_todo", "tarea_hecha"],
    "todo_remove": ["todo_remove", "quitar_tarea", "remove_todo"],
    "note_create": ["note_create", "crear_nota", "new_note", "make_note"],
    "note_list": ["note_list", "listar_notas", "list_notes", "mis_notas"],
    "note_search": ["note_search", "buscar_nota", "search_notes"],
    "note_delete": ["note_delete", "borrar_nota", "delete_note"],
    "reminder_set": ["reminder_set", "poner_recordatorio", "set_reminder", "recordar"],
    "reminder_list": ["reminder_list", "listar_recordatorios", "list_reminders"],

    # --- Email extendido ---
    "email_read": ["email_read", "leer_correo", "read_email"],
    "email_search": ["email_search", "buscar_correo", "search_email"],
    "email_send_html": ["email_send_html", "enviar_html", "send_html_email"],
    "email_attach": ["email_attach", "adjuntar_archivo", "attach_file"],
    "email_label": ["email_label", "etiquetar_correo", "label_email"],
    "email_archive": ["email_archive", "archivar_correo", "archive_email"],

    # --- File operations extendido ---
    "file_hash": ["file_hash", "calcular_hash", "compute_hash"],
    "file_encrypt": ["file_encrypt", "cifrar_archivo", "encrypt_file"],
    "file_decrypt": ["file_decrypt", "descifrar_archivo", "decrypt_file"],
    "file_compress": ["file_compress", "comprimir_archivo", "zip_file"],
    "file_extract": ["file_extract", "extraer_archivo", "unzip_file"],
    "file_search_content": ["file_search_content", "buscar_contenido", "grep_files"],
    "file_watch": ["file_watch", "vigilar_archivo", "watch_file"],
    "file_sync": ["file_sync", "sincronizar_archivos", "sync_files"],
    "file_diff": ["file_diff", "comparar_archivos", "diff_files"],
    "file_merge": ["file_merge", "combinar_archivos", "merge_files"],

    # --- Sistema extendido ---
    "sys_info": ["sys_info", "info_sistema", "system_info"],
    "sys_cpu": ["sys_cpu", "ver_cpu", "cpu_info"],
    "sys_memory": ["sys_memory", "ver_memoria", "memory_info", "ram_info"],
    "sys_disk": ["sys_disk", "ver_disco", "disk_info"],
    "sys_network": ["sys_network", "ver_red", "network_info"],
    "sys_battery": ["sys_battery", "ver_bateria", "battery_info"],
    "sys_processes": ["sys_processes", "listar_procesos", "list_processes", "ps"],
    "sys_kill_process": ["sys_kill_process", "matar_proceso", "kill_process"],
    "sys_services": ["sys_services", "listar_servicios", "list_services"],
    "sys_env": ["sys_env", "variables_entorno", "env_vars"],
    "sys_clipboard_read": ["sys_clipboard_read", "leer_portapapeles", "read_clipboard"],
    "sys_clipboard_write": ["sys_clipboard_write", "escribir_portapapeles", "write_clipboard"],
    "sys_volume_set": ["sys_volume_set", "ajustar_volumen", "set_volume"],
    "sys_volume_mute": ["sys_volume_mute", "silenciar", "mute_volume"],
    "sys_brightness_set": ["sys_brightness_set", "brillo", "set_brightness"],
    "sys_sleep": ["sys_sleep", "suspender", "sleep_pc"],
    "sys_shutdown": ["sys_shutdown", "apagar_pc", "shutdown"],
    "sys_restart": ["sys_restart", "reiniciar_pc", "restart"],
    "sys_lock": ["sys_lock", "bloquear_pc", "lock_pc"],
    "sys_logout": ["sys_logout", "cerrar_sesion", "logout"],

    # --- Network ---
    "net_ping": ["net_ping", "ping", "hacer_ping"],
    "net_traceroute": ["net_traceroute", "traceroute", "trace"],
    "net_dns_lookup": ["net_dns_lookup", "dns_lookup", "consultar_dns"],
    "net_whois": ["net_whois", "whois", "consultar_whois"],
    "net_ip_info": ["net_ip_info", "mi_ip", "my_ip"],
    "net_speed_test": ["net_speed_test", "test_velocidad", "speed_test"],
    "net_download": ["net_download", "descargar_url", "download_url"],
    "net_check_website": ["net_check_website", "verificar_sitio", "check_website"],
    "net_public_ip": ["net_public_ip", "ip_publica", "public_ip"],

    # --- Browser automation ---
    "browser_navigate": ["browser_navigate", "navegar_a", "navigate_to"],
    "browser_click": ["browser_click", "click_browser", "click_web"],
    "browser_type": ["browser_type", "escribir_browser", "type_browser"],
    "browser_screenshot": ["browser_screenshot", "captura_browser", "screenshot_browser"],
    "browser_extract_text": ["browser_extract_text", "extraer_texto_web", "extract_web_text"],
    "browser_fill_form": ["browser_fill_form", "rellenar_formulario_web", "fill_web_form"],
    "browser_execute_js": ["browser_execute_js", "ejecutar_js", "execute_js", "run_js"],
    "browser_get_cookies": ["browser_get_cookies", "obtener_cookies", "get_cookies"],
    "browser_set_cookies": ["browser_set_cookies", "establecer_cookies", "set_cookies"],
    "browser_clear_cookies": ["browser_clear_cookies", "limpiar_cookies", "clear_cookies"],

    # --- Media (más) ---
    "media_play": ["media_play", "reproducir_media", "play_media"],
    "media_pause": ["media_pause", "pausar_media", "pause_media"],
    "media_stop": ["media_stop", "detener_media", "stop_media"],
    "media_next": ["media_next", "siguiente", "next_track"],
    "media_prev": ["media_prev", "anterior", "prev_track"],
    "media_volume_up": ["media_volume_up", "subir_volumen", "volume_up"],
    "media_volume_down": ["media_volume_down", "bajar_volumen", "volume_down"],
    "media_mute": ["media_mute", "mutear", "mute_media"],
    "media_fullscreen": ["media_fullscreen", "pantalla_completa", "fullscreen_media"],

    # --- Calendario (más) ---
    "cal_recurring": ["cal_recurring", "evento_recurrente", "recurring_event"],
    "cal_reminder": ["cal_reminder", "recordatorio_evento", "event_reminder"],
    "cal_invite": ["cal_invite", "invitar_evento", "event_invite"],
    "cal_sync_google": ["cal_sync_google", "sincronizar_google", "sync_google_cal"],
    "cal_export_ics": ["cal_export_ics", "exportar_ics", "export_ics"],

    # --- Health (mocks locales) ---
    "health_steps": ["health_steps", "contar_pasos", "count_steps"],
    "health_heart_rate": ["health_heart_rate", "frecuencia_cardiaca", "heart_rate"],
    "health_sleep": ["health_sleep", "registrar_sueno", "log_sleep"],
    "health_water": ["health_water", "registrar_agua", "log_water"],
    "health_workout_start": ["health_workout_start", "iniciar_entrenamiento", "start_workout"],
    "health_workout_end": ["health_workout_end", "finalizar_entrenamiento", "end_workout"],

    # --- Smart Home ---
    "home_lights_on": ["home_lights_on", "encender_luces", "lights_on"],
    "home_lights_off": ["home_lights_off", "apagar_luces", "lights_off"],
    "home_lights_dim": ["home_lights_dim", "atenuar_luces", "dim_lights"],
    "home_thermostat_set": ["home_thermostat_set", "ajustar_termostato", "set_thermostat"],
    "home_blinds_up": ["home_blinds_up", "subir_persianas", "blinds_up"],
    "home_blinds_down": ["home_blinds_down", "bajar_persianas", "blinds_down"],
    "home_lock_door": ["home_lock_door", "cerrar_puerta", "lock_door"],
    "home_unlock_door": ["home_unlock_door", "abrir_puerta", "unlock_door"],
    "home_scene_movie": ["home_scene_movie", "escena_pelicula", "movie_scene"],
    "home_scene_goodnight": ["home_scene_goodnight", "escena_buenas_noches", "goodnight_scene"],

    # --- More developer ---
    "dev_run_tests": ["dev_run_tests", "correr_tests", "run_all_tests"],
    "dev_lint": ["dev_lint", "lint_code", "lintar"],
    "dev_format": ["dev_format", "formatear", "format_code"],
    "dev_build": ["dev_build", "construir", "build_project"],
    "dev_serve": ["dev_serve", "servir", "serve_dev"],
    "dev_install_deps": ["dev_install_deps", "instalar_dependencias", "install_deps"],
    "dev_clean": ["dev_clean", "limpiar_build", "clean_build"],
    "dev_repl": ["dev_repl", "abrir_repl", "open_repl"],
    "dev_debug": ["dev_debug", "depurar", "debug_code"],
    "dev_profile": ["dev_profile", "perfilar", "profile_code"],

    # --- Security ---
    "sec_scan_ports": ["sec_scan_ports", "escanear_puertos_seg", "security_port_scan"],
    "sec_check_vulns": ["sec_check_vulns", "verificar_vulns", "check_vulnerabilities"],
    "sec_audit_password": ["sec_audit_password", "auditar_contrasena", "password_audit"],
    "sec_generate_password": ["sec_generate_password", "generar_contrasena", "generate_password"],
    "sec_2fa_code": ["sec_2fa_code", "codigo_2fa", "two_factor_code"],
    "sec_hash_sha256": ["sec_hash_sha256", "hash_sha256", "sha256"],
    "sec_encrypt_aes": ["sec_encrypt_aes", "cifrar_aes", "aes_encrypt"],
    "sec_decrypt_aes": ["sec_decrypt_aes", "descifrar_aes", "aes_decrypt"],
}


def _slugify(name: str) -> str:
    """Normaliza un nombre a slug para matching."""
    s = unicodedata.normalize("NFD", name.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9_]+", "_", s).strip("_")
    return s


def _gen_combinations(seeds: List[str], prefixes: List[str], max_per_seed: int = 6) -> Set[str]:
    """Genera combinaciones prefijo + seed (limitadas para no explotar)."""
    out: Set[str] = set()
    for seed in seeds:
        seed_clean = seed.strip()
        if not seed_clean:
            continue
        out.add(seed_clean)
        # Solo tomar los primeros N prefijos (los más comunes)
        for prefix in prefixes[:max_per_seed]:
            prefix_clean = prefix.strip()
            if not prefix_clean:
                continue
            # Solo con guión bajo
            candidate = f"{prefix_clean}_{seed_clean}"
            if 4 <= len(candidate) <= 40:
                out.add(candidate)
    return out


def expand_registry_aliases(agent, max_per_seed: int = 2) -> int:
    """
    Aplica aliases a todas las tools registradas en el agent.
    Devuelve el número de aliases añadidos.
    """
    original_tools = dict(agent.tools)  # copia
    count = 0
    for canonical_name, func in original_tools.items():
        # 1) Buscar seeds para este nombre canónico
        seeds = TOOL_SEEDS.get(canonical_name, [canonical_name])
        # 2) Generar combinaciones con prefijos (limitadas)
        all_aliases_es = _gen_combinations(seeds, PREFIXES_ES, max_per_seed=max_per_seed)
        all_aliases_en = _gen_combinations(seeds, PREFIXES_EN, max_per_seed=max_per_seed)
        all_aliases = all_aliases_es | all_aliases_en
        # Añadir seeds originales
        for s in seeds:
            all_aliases.add(s)
            all_aliases.add(_slugify(s))
        # 3) Registrar cada alias como nueva tool que delega al canónico
        for alias in all_aliases:
            alias_norm = _slugify(alias)
            if not alias_norm or alias_norm == canonical_name:
                continue
            if alias_norm in agent.tools:
                continue  # ya existe, no duplicar
            # Crear wrapper
            def make_wrapper(fn, args_tmpl):
                def wrapper(**kwargs):
                    return fn(**kwargs)
                wrapper.__name__ = alias_norm
                wrapper.__doc__ = f"Alias de {canonical_name}. Args: {args_tmpl}"
                return wrapper
            # Plantilla de args = nombre canónico con sus hints
            try:
                import inspect
                sig = inspect.signature(func)
                params = [
                    f"{p.name}={p.default if p.default is not inspect.Parameter.empty else '...'}"
                    for p in sig.parameters.values()
                    if p.name not in ("args", "kwargs")
                ][:5]
                args_tmpl = ", ".join(params)
            except Exception:
                args_tmpl = "..."
            agent.register_tool(alias_norm, make_wrapper(func, args_tmpl))
            count += 1
    return count


def count_aliases(max_per_seed: int = 2) -> int:
    """Cuenta cuántos aliases se generarían sin aplicarlos."""
    total = 0
    for seeds in TOOL_SEEDS.values():
        all_aliases_es = _gen_combinations(seeds, PREFIXES_ES, max_per_seed=max_per_seed)
        all_aliases_en = _gen_combinations(seeds, PREFIXES_EN, max_per_seed=max_per_seed)
        all_aliases = all_aliases_es | all_aliases_en
        for s in seeds:
            all_aliases.add(s)
            all_aliases.add(_slugify(s))
        total += len(all_aliases)
    return total


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    n_tools = len(TOOL_SEEDS)
    n_aliases = count_aliases(max_per_seed=2)
    print(f"Tools con seeds: {n_tools}")
    print(f"Aliases que se generarían: {n_aliases}")
    print(f"Promedio por tool: {n_aliases / max(1, n_tools):.0f}")
    # Muestra los aliases de write_file
    seeds = TOOL_SEEDS["write_file"]
    aliases_es = _gen_combinations(seeds, PREFIXES_ES, max_per_seed=2)
    aliases_en = _gen_combinations(seeds, PREFIXES_EN, max_per_seed=2)
    all_a = aliases_es | aliases_en
    print(f"\nAliases de write_file (total {len(all_a)}):")
    for a in sorted(all_a)[:30]:
        print(f"  - {a}")
    print(f"  ... y {len(all_a) - 30} más")
