"""
AUTOMYX TOOL REGISTRY - Centralized Tool Registration
======================================================
Single source of truth for all tool registrations.
Used by both the API gateway (api/main.py) and the terminal REPL (core/repl.py).
"""
from __future__ import annotations

import os
import sys
import logging
from typing import Any

logger = logging.getLogger("automyx.tools")


def _safe_import(module_path: str, class_name: str = None):
    """Safely import a module or class. Returns None on failure."""
    try:
        mod = __import__(module_path, fromlist=[class_name] if class_name else [])
        if class_name:
            return getattr(mod, class_name, None)
        return mod
    except Exception as e:
        logger.debug(f"Could not import {module_path}.{class_name or ''}: {e}")
        return None


def register_all_tools(agent: Any) -> int:
    """
    Register all available tools on the given agent.
    
    Returns the total number of tools registered.
    Silently skips tools whose dependencies are missing.
    """
    count = 0
    
    # ── PC Tools (core - always available) ─────────────────────────────
    PCTools = _safe_import("tools.pc_tools", "PCTools")
    if PCTools:
        for name, method in [
            ("execute_cmd", PCTools.execute_cmd),
            ("use_terminal_window", PCTools.use_terminal_window),
            ("list_directory", PCTools.list_directory),
            ("read_file", PCTools.read_file),
            ("write_file", PCTools.write_file),
            ("create_directory", PCTools.create_directory),
            ("copy_file", PCTools.copy_file),
            ("move_file", PCTools.move_file),
            ("delete_file", PCTools.delete_file),
            ("open_vscode", PCTools.open_vscode),
            ("open_program", PCTools.open_program),
            ("wait_seconds", PCTools.wait_seconds),
            ("press_key", PCTools.press_key),
            ("mouse_click", PCTools.mouse_click),
            ("find_and_click_image", PCTools.find_and_click_image),
            ("type_text", PCTools.type_text),
            ("screenshot", PCTools.screenshot),
            ("play_tiktok_desktop_video", PCTools.play_tiktok_desktop_video),
            ("generate_vyrex_video", PCTools.generate_vyrex_video),
            ("generate_gemini_image", PCTools.generate_gemini_image),
            ("generate_gemini_video", PCTools.generate_gemini_video),
            # ── Herramientas de ejecución avanzada ──
            ("check_port",          PCTools.check_port),
            ("kill_port",           PCTools.kill_port),
            ("wait_for_server",     PCTools.wait_for_server),
            ("npm_run",             PCTools.npm_run),
            ("run_python",          PCTools.run_python),
            ("open_browser",        PCTools.open_browser),
            ("get_system_info",     PCTools.get_system_info),
            ("find_in_files",       PCTools.find_in_files),
            ("download_file",       PCTools.download_file),
            ("get_running_processes", PCTools.get_running_processes),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Web Tools ──────────────────────────────────────────────────────
    WebTools = _safe_import("tools.web_tools", "WebTools")
    if WebTools:
        for name, method in [
            ("web_search", WebTools.web_search),
            ("open_website", WebTools.open_website),
            ("deep_web_scrape", WebTools.deep_web_scrape),
            ("ai_form_filler", WebTools.ai_form_filler),
            ("play_youtube_video", WebTools.play_youtube_video),
            ("create_web_preview", WebTools.create_web_preview),
            ("analyze_browser_screen", WebTools.analyze_browser_screen),
            ("get_current_browser_url", WebTools.get_current_browser_url),
            ("update_live_canvas", WebTools.update_live_canvas),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Social Tools ───────────────────────────────────────────────────
    SocialTools = _safe_import("tools.social_tools", "SocialTools")
    if SocialTools:
        for name, method in [
            ("send_whatsapp", SocialTools.send_whatsapp),
            ("upload_tiktok", SocialTools.upload_tiktok),
            ("post_facebook", SocialTools.post_facebook),
            ("send_telegram", SocialTools.send_telegram),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Video Tools ────────────────────────────────────────────────────
    VideoTools = _safe_import("tools.video_tools", "VideoTools")
    if VideoTools:
        for name, method in [
            ("trim_video", VideoTools.trim_video),
            ("professional_color_grading", VideoTools.professional_color_grading),
            ("advanced_transition", VideoTools.advanced_transition),
            ("professional_audio_mastering", VideoTools.professional_audio_mastering),
            ("add_intro_outro", VideoTools.add_intro_outro),
            ("composite_movie_sequence", VideoTools.composite_movie_sequence),
            ("add_music_to_video", VideoTools.add_music_to_video),
            ("apply_visual_effect", VideoTools.apply_visual_effect),
            ("create_tiktok_edit", VideoTools.create_tiktok_edit),
            ("add_dynamic_zoom", VideoTools.add_dynamic_zoom),
            ("advanced_video_editor", VideoTools.advanced_video_editor),
            ("analyze_video_content", VideoTools.analyze_video_content),
            ("smart_auto_edit", VideoTools.smart_auto_edit),
        ]:
            agent.register_tool(name, method)
            count += 1
        # auto_subtitles requires whisper
        agent.register_tool("auto_subtitles", VideoTools.auto_subtitles, requires=["whisper"])
        count += 1
    
    # ── Cyber Tools ────────────────────────────────────────────────────
    CyberTools = _safe_import("tools.cyber_tools", "CyberTools")
    if CyberTools:
        for name, method in [
            ("port_scan", CyberTools.port_scan),
            ("run_nmap_scan", CyberTools.run_nmap_scan),
            ("osint_search", CyberTools.osint_search),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Audio Tools ────────────────────────────────────────────────────
    AudioTools = _safe_import("tools.audio_tools", "AudioTools")
    if AudioTools:
        for name, method in [
            ("apply_autotune", AudioTools.apply_autotune),
            ("mix_music", AudioTools.mix_music),
            ("master_audio", AudioTools.master_audio),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Extra Tools ────────────────────────────────────────────────────
    ExtraTools = _safe_import("tools.extra_tools", "ExtraTools")
    if ExtraTools:
        agent.register_tool("extract_text_from_image", ExtraTools.extract_text_from_image, requires=["pytesseract", "PIL"])
        agent.register_tool("text_to_speech", ExtraTools.text_to_speech, requires=["edge_tts"])
        agent.register_tool("download_video", ExtraTools.download_video, requires=["yt_dlp"])
        count += 3
    
    # ── 3D Tools (Blender) ─────────────────────────────────────────────
    ThreeDTools = _safe_import("tools.three_d_tools", "ThreeDTools")
    if ThreeDTools:
        for name, method in [
            ("generate_3d_model", ThreeDTools.generate_3d_model),
            ("run_blender_script", ThreeDTools.run_blender_script),
            ("execute_blender_python_code", ThreeDTools.execute_blender_python_code),
            ("generate_professional_3d_video", ThreeDTools.generate_professional_3d_video),
            ("generate_cinematic_environment", ThreeDTools.generate_cinematic_environment),
            ("simulate_advanced_physics", ThreeDTools.simulate_advanced_physics),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Cron / Scheduler Tools ─────────────────────────────────────────
    CronTools = _safe_import("tools.cron_tools", "CronTools")
    if CronTools:
        for name, method in [
            ("schedule_task", CronTools.schedule_task),
            ("list_scheduled_tasks", CronTools.list_scheduled_tasks),
            ("cancel_task", CronTools.cancel_task),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Data Tools ─────────────────────────────────────────────────────
    DataTools = _safe_import("tools.data_tools", "DataTools")
    if DataTools:
        for name, method in [
            ("analyze_csv_data", DataTools.analyze_csv_data),
            ("generate_data_chart", DataTools.generate_data_chart),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── DevOps Tools ───────────────────────────────────────────────────
    DevOpsTools = _safe_import("tools.devops_tools", "DevOpsTools")
    if DevOpsTools:
        for name, method in [
            ("check_system_resources", DevOpsTools.check_system_resources),
            ("manage_docker_container", DevOpsTools.manage_docker_container),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Email Tools ────────────────────────────────────────────────────
    EmailTools = _safe_import("tools.email_tools", "EmailTools")
    if EmailTools:
        for name, method in [
            ("read_recent_emails", EmailTools.read_recent_emails),
            ("create_email_draft", EmailTools.create_email_draft),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── HR Tools ───────────────────────────────────────────────────────
    HRTools = _safe_import("tools.hr_tools", "HRTools")
    if HRTools:
        for name, method in [
            ("read_pdf_text", HRTools.read_pdf_text),
            ("read_all_cvs_in_folder", HRTools.read_all_cvs_in_folder),
            ("export_to_excel", HRTools.export_to_excel),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Skill Tools ────────────────────────────────────────────────────
    SkillTools = _safe_import("tools.skill_tools", "SkillTools")
    if SkillTools:
        for name, method in [
            ("create_skill", SkillTools.create_skill),
            ("list_skills", SkillTools.list_skills),
            ("read_skill", SkillTools.read_skill),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Blender Tools (direct Blender control) ─────────────────────────
    BlenderTools = _safe_import("tools.blender_tools", "BlenderTools")
    if BlenderTools:
        for name, method in [
            ("blender_open", BlenderTools.open_blender),
            ("blender_create_cube", BlenderTools.create_cube),
            ("blender_create_sphere", BlenderTools.create_sphere),
            ("blender_create_torus", BlenderTools.create_torus),
            ("blender_create_cylinder", BlenderTools.create_cylinder),
            ("blender_create_cone", BlenderTools.create_cone),
            ("blender_apply_material", BlenderTools.apply_material),
            ("blender_set_location", BlenderTools.set_object_location),
            ("blender_set_rotation", BlenderTools.set_object_rotation),
            ("blender_set_scale", BlenderTools.set_object_scale),
            ("blender_delete_object", BlenderTools.delete_object),
            ("blender_clear_scene", BlenderTools.clear_scene),
            ("blender_save_scene", BlenderTools.save_scene),
            ("blender_render_image", BlenderTools.render_image),
            ("blender_create_animation", BlenderTools.create_animation),
            ("blender_render_animation", BlenderTools.render_animation),
            ("blender_import_model", BlenderTools.import_model),
            ("blender_export_model", BlenderTools.export_model),
            ("blender_list_objects", BlenderTools.list_objects),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Photo Editor Tools ─────────────────────────────────────────────
    PhotoEditorTools = _safe_import("tools.photo_editor_tools", "PhotoEditorTools")
    if PhotoEditorTools:
        for name, method in [
            ("photo_open", PhotoEditorTools.open_image),
            ("photo_resize", PhotoEditorTools.resize_image),
            ("photo_crop", PhotoEditorTools.crop_image),
            ("photo_brightness", PhotoEditorTools.adjust_brightness),
            ("photo_contrast", PhotoEditorTools.adjust_contrast),
            ("photo_saturation", PhotoEditorTools.adjust_saturation),
            ("photo_filter", PhotoEditorTools.apply_filter),
            ("photo_rotate", PhotoEditorTools.rotate_image),
            ("photo_flip", PhotoEditorTools.flip_image),
            ("photo_convert", PhotoEditorTools.convert_image_format),
            ("photo_text_watermark", PhotoEditorTools.add_text_watermark),
            ("photo_image_watermark", PhotoEditorTools.add_image_watermark),
            ("photo_thumbnail", PhotoEditorTools.create_thumbnail),
            ("photo_collage", PhotoEditorTools.create_collage),
            ("photo_exposure", PhotoEditorTools.adjust_exposure),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Project Autopilot ──────────────────────────────────────────────
    ProjectAutopilot = _safe_import("tools.project_autopilot", "ProjectAutopilot")
    if ProjectAutopilot:
        for name, method in [
            ("autopilot_analyze_project", ProjectAutopilot.analyze_project),
            ("autopilot_detect_bugs", ProjectAutopilot.detect_bugs),
            ("autopilot_fix_bugs", ProjectAutopilot.fix_bugs),
            ("autopilot_generate_docs", ProjectAutopilot.generate_documentation),
            ("autopilot_auto_improve", ProjectAutopilot.auto_improve_project),
            ("autopilot_git_commit", ProjectAutopilot.git_commit),
            ("autopilot_git_push", ProjectAutopilot.git_push),
            ("autopilot_git_pull", ProjectAutopilot.git_pull),
            ("autopilot_full_run", ProjectAutopilot.full_autopilot_run),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Universal App Control ──────────────────────────────────────────
    UniversalAppControl = _safe_import("tools.universal_app_control", "UniversalAppControl")
    if UniversalAppControl:
        for name, method in [
            ("app_get_windows", UniversalAppControl.get_open_windows),
            ("app_activate_window", UniversalAppControl.activate_window),
            ("app_move_window", UniversalAppControl.move_window),
            ("app_close_window", UniversalAppControl.close_window),
            ("app_minimize_window", UniversalAppControl.minimize_window),
            ("app_maximize_window", UniversalAppControl.maximize_window),
            ("ui_click", UniversalAppControl.ui_click),
            ("ui_move", UniversalAppControl.ui_move),
            ("ui_type", UniversalAppControl.ui_type),
            ("ui_press", UniversalAppControl.ui_press),
            ("ui_hotkey", UniversalAppControl.ui_hotkey),
            ("ui_mouse_pos", UniversalAppControl.get_mouse_position),
            ("ui_screen_size", UniversalAppControl.get_screen_size),
            ("ui_screenshot_region", UniversalAppControl.screenshot_region),
            ("ui_find_image", UniversalAppControl.find_image_on_screen),
            ("ui_click_image", UniversalAppControl.click_image),
            ("ui_scroll", UniversalAppControl.scroll),
            ("ui_drag_to", UniversalAppControl.drag_to),
            ("app_automate_sequence", UniversalAppControl.automate_app_sequence),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Automation Pro (Workflow, Script, Memory, API, Chain) ──────────
    automation_pro = _safe_import("tools.automation_pro")
    if automation_pro:
        WorkflowManager = getattr(automation_pro, "WorkflowManager", None)
        ScriptEditorPro = getattr(automation_pro, "ScriptEditorPro", None)
        AdvancedMemory = getattr(automation_pro, "AdvancedMemory", None)
        APIIntegrationPro = getattr(automation_pro, "APIIntegrationPro", None)
        ChainOfThought = getattr(automation_pro, "ChainOfThought", None)
        
        if WorkflowManager:
            agent.register_tool("create_workflow", WorkflowManager.create_workflow)
            agent.register_tool("run_workflow", WorkflowManager.run_workflow)
            count += 2
        if ScriptEditorPro:
            agent.register_tool("create_and_run_script", ScriptEditorPro.create_and_run_script)
            count += 1
        if AdvancedMemory:
            agent.register_tool("log_conversation", AdvancedMemory.log_conversation)
            agent.register_tool("recall_conversation", AdvancedMemory.recall_conversation)
            count += 2
        if APIIntegrationPro:
            agent.register_tool("make_api_request", APIIntegrationPro.make_request)
            count += 1
        if ChainOfThought:
            agent.register_tool("create_plan", ChainOfThought.create_plan)
            count += 1
    
    # ── Aumformbring (Self-Learning) ───────────────────────────────────
    aumformbring_system = _safe_import("tools.aumformbring", "aumformbring_system")
    if aumformbring_system:
        for name, method in [
            ("aumformbring_store", aumformbring_system.store_conversation),
            ("aumformbring_get_skills", aumformbring_system.get_learned_skills),
            ("aumformbring_get_memory", aumformbring_system.get_conversation_memory),
            ("aumformbring_get_patterns", aumformbring_system.get_useful_patterns),
            ("aumformbring_recall", aumformbring_system.recall_similar_conversation),
            ("aumformbring_auto_improve", aumformbring_system.auto_improve),
            ("aumformbring_create_skill", aumformbring_system.create_custom_skill),
            ("aumformbring_search", aumformbring_system.search_memory),
            ("aumformbring_forget", aumformbring_system.forget_conversation),
            ("aumformbring_clear", aumformbring_system.clear_all_memory),
            ("aumformbring_stats", aumformbring_system.get_stats),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Nexus Core ─────────────────────────────────────────────────────
    nexus_core = _safe_import("tools.nexus_core", "nexus_core")
    if nexus_core:
        for name, method in [
            ("nexus_store", nexus_core.store_and_compress),
            ("nexus_search", nexus_core.search_memory),
            ("nexus_profile", nexus_core.get_user_profile),
            ("nexus_skill_stats", nexus_core.get_skill_stats),
            ("nexus_all_skills", nexus_core.get_all_skills),
            ("nexus_full_stats", nexus_core.get_full_stats),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Elite Skills ───────────────────────────────────────────────────
    elite_skills = _safe_import("tools.elite_skills")
    if elite_skills:
        GitHubTools = getattr(elite_skills, "GitHubTools", None)
        CloudDevOpsTools = getattr(elite_skills, "CloudDevOpsTools", None)
        DataScienceTools = getattr(elite_skills, "DataScienceTools", None)
        SmartHomeTools = getattr(elite_skills, "SmartHomeTools", None)
        CreativeTools = getattr(elite_skills, "CreativeTools", None)
        UniqueAutomyxTools = getattr(elite_skills, "UniqueAutomyxTools", None)
        
        if GitHubTools:
            agent.register_tool("github_inspect_repo", GitHubTools.github_inspect_repo)
            agent.register_tool("git_advanced_merge", GitHubTools.git_advanced_merge)
            count += 2
        if CloudDevOpsTools:
            agent.register_tool("docker_deploy_stack", CloudDevOpsTools.docker_deploy_stack)
            agent.register_tool("kubernetes_apply", CloudDevOpsTools.kubernetes_apply)
            count += 2
        if DataScienceTools:
            agent.register_tool("jupyter_live_kernel", DataScienceTools.jupyter_live_kernel)
            agent.register_tool("sql_execute_query", DataScienceTools.sql_execute_query)
            count += 2
        if SmartHomeTools:
            agent.register_tool("home_assistant_call", SmartHomeTools.home_assistant_call)
            count += 1
        if CreativeTools:
            agent.register_tool("generate_mermaid_diagram", CreativeTools.generate_mermaid_diagram)
            agent.register_tool("generate_ascii_art", CreativeTools.generate_ascii_art)
            count += 2
        if UniqueAutomyxTools:
            agent.register_tool("dark_web_breach_check", UniqueAutomyxTools.dark_web_breach_check)
            agent.register_tool("blockchain_smart_contract_audit", UniqueAutomyxTools.blockchain_smart_contract_audit)
            agent.register_tool("autonomous_codebase_healing", UniqueAutomyxTools.autonomous_codebase_healing)
            agent.register_tool("predictive_market_analysis", UniqueAutomyxTools.predictive_market_analysis)
            count += 4
    
    # ── Academic Tools ─────────────────────────────────────────────────
    AcademicTools = _safe_import("tools.academic_tools", "AcademicTools")
    if AcademicTools:
        for name, method in [
            ("academic_search_arxiv", AcademicTools.search_arxiv),
            ("academic_search_pubmed", AcademicTools.search_pubmed),
            ("academic_search_crossref", AcademicTools.search_crossref),
            ("academic_search_semantic_scholar", AcademicTools.search_semantic_scholar),
            ("academic_fetch_abstract", AcademicTools.fetch_abstract),
            ("academic_generate_citation", AcademicTools.generate_citation),
            ("academic_generate_literature_review", AcademicTools.generate_literature_review),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Accountant Tools ───────────────────────────────────────────────
    AccountantTools = _safe_import("tools.accountant_tools", "AccountantTools")
    if AccountantTools:
        for name, method in [
            ("accountant_parse_invoice_pdf", AccountantTools.parse_invoice_pdf),
            ("accountant_parse_invoice_xml", AccountantTools.parse_invoice_xml),
            ("accountant_bulk_import_folder", AccountantTools.bulk_import_folder),
            ("accountant_reconcile_bank_statement", AccountantTools.reconcile_bank_statement),
            ("accountant_calculate_tax", AccountantTools.calculate_tax),
            ("accountant_validate_tax_id", AccountantTools.validate_tax_id),
            ("accountant_generate_afip_report", AccountantTools.generate_afip_report),
            ("accountant_generate_sat_report", AccountantTools.generate_sat_report),
            ("accountant_generate_sunat_report", AccountantTools.generate_sunat_report),
            ("accountant_generate_aeat_report", AccountantTools.generate_aeat_report),
            ("accountant_generate_financial_report", AccountantTools.generate_financial_report),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Livestream Tools ───────────────────────────────────────────────
    LivestreamTools = _safe_import("tools.livestream_tools", "LivestreamTools")
    if LivestreamTools:
        for name, method in [
            ("livestream_obs_connect", LivestreamTools.obs_connect),
            ("livestream_obs_start_stream", LivestreamTools.obs_start_stream),
            ("livestream_obs_stop_stream", LivestreamTools.obs_stop_stream),
            ("livestream_obs_start_recording", LivestreamTools.obs_start_recording),
            ("livestream_obs_stop_recording", LivestreamTools.obs_stop_recording),
            ("livestream_obs_switch_scene", LivestreamTools.obs_switch_scene),
            ("livestream_obs_get_scenes", LivestreamTools.obs_get_scenes),
            ("livestream_obs_toggle_source", LivestreamTools.obs_toggle_source),
            ("livestream_obs_set_source_text", LivestreamTools.obs_set_source_text),
            ("livestream_obs_set_bitrate", LivestreamTools.obs_set_bitrate),
            ("livestream_obs_get_status", LivestreamTools.obs_get_status),
            ("livestream_setup_multistream", LivestreamTools.setup_multistream),
            ("livestream_get_stream_health", LivestreamTools.get_stream_health),
            ("livestream_create_alert_overlay", LivestreamTools.create_alert_overlay),
            ("livestream_update_ticker", LivestreamTools.update_ticker),
            ("livestream_set_moderation_rules", LivestreamTools.set_moderation_rules),
            ("livestream_moderate_chat", LivestreamTools.moderate_chat),
            ("livestream_save_preset", LivestreamTools.save_preset),
            ("livestream_load_preset", LivestreamTools.load_preset),
            ("livestream_schedule_scene", LivestreamTools.schedule_scene),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Swarm Orchestrator ─────────────────────────────────────────────
    SwarmOrchestrator = _safe_import("tools.swarm_tools", "SwarmOrchestrator")
    if SwarmOrchestrator:
        for name, method in [
            ("swarm_register_node", SwarmOrchestrator.register_node),
            ("swarm_list_nodes", SwarmOrchestrator.list_nodes),
            ("swarm_remove_node", SwarmOrchestrator.remove_node),
            ("swarm_health_check", SwarmOrchestrator.health_check),
            ("swarm_dispatch_task", SwarmOrchestrator.dispatch_task),
            ("swarm_dispatch_parallel", SwarmOrchestrator.dispatch_parallel),
            ("swarm_dispatch_map_reduce", SwarmOrchestrator.dispatch_map_reduce),
            ("swarm_pipeline", SwarmOrchestrator.pipeline),
            ("swarm_consensus", SwarmOrchestrator.consensus),
            ("swarm_get_task_status", SwarmOrchestrator.get_task_status),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Skill Forger ───────────────────────────────────────────────────
    SkillForger = _safe_import("tools.skill_forger", "SkillForger")
    if SkillForger:
        for name, method in [
            ("forger_analyze_patterns", SkillForger.analyze_patterns),
            ("forger_cluster_similar_requests", SkillForger.cluster_similar_requests),
            ("forger_forge_skill", SkillForger.forge_skill),
            ("forger_validate_skill", SkillForger.validate_skill),
            ("forger_track_skill_usage", SkillForger.track_skill_usage),
            ("forger_promote_skill", SkillForger.promote_skill),
            ("forger_demote_skill", SkillForger.demote_skill),
            ("forger_archive_skill", SkillForger.archive_skill),
            ("forger_list_forged_skills", SkillForger.list_forged_skills),
            ("forger_run_cycle", SkillForger.run_cycle),
            ("forger_check_duplicates", SkillForger.check_duplicates),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Stealth Browser Tools ──────────────────────────────────────────
    StealthBrowserTools = _safe_import("tools.stealth_browser_tools", "StealthBrowserTools")
    if StealthBrowserTools:
        for name, method in [
            ("stealth_launch_browser", StealthBrowserTools.launch_browser),
            ("stealth_goto", StealthBrowserTools.goto),
            ("stealth_human_click", StealthBrowserTools.human_click),
            ("stealth_human_type", StealthBrowserTools.human_type),
            ("stealth_human_scroll", StealthBrowserTools.human_scroll),
            ("stealth_solve_recaptcha_v2", StealthBrowserTools.solve_recaptcha_v2),
            ("stealth_solve_cloudflare", StealthBrowserTools.solve_cloudflare),
            ("stealth_save_session", StealthBrowserTools.save_session),
            ("stealth_load_session", StealthBrowserTools.load_session),
            ("stealth_scrape_selector", StealthBrowserTools.scrape_selector),
            ("stealth_screenshot_full_page", StealthBrowserTools.screenshot_full_page),
            ("stealth_set_proxy_pool", StealthBrowserTools.set_proxy_pool),
            ("stealth_test_proxy", StealthBrowserTools.test_proxy),
            ("stealth_rotate_fingerprint", StealthBrowserTools.rotate_fingerprint),
            ("stealth_close_browser", StealthBrowserTools.close_browser),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── RAG Memory Tools ───────────────────────────────────────────────
    RAGMemoryTools = _safe_import("tools.rag_memory_tools", "RAGMemoryTools")
    if RAGMemoryTools:
        for name, method in [
            ("rag_init_collection", RAGMemoryTools.init_collection),
            ("rag_list_collections", RAGMemoryTools.list_collections),
            ("rag_collection_stats", RAGMemoryTools.collection_stats),
            ("rag_delete_collection", RAGMemoryTools.delete_collection),
            ("rag_index_file", RAGMemoryTools.index_file),
            ("rag_index_folder", RAGMemoryTools.index_folder),
            ("rag_index_url", RAGMemoryTools.index_url),
            ("rag_index_conversation", RAGMemoryTools.index_conversation),
            ("rag_query", RAGMemoryTools.query),
            ("rag_answer", RAGMemoryTools.answer),
            ("rag_delete_document", RAGMemoryTools.delete_document),
            ("rag_sync_aumformbring", RAGMemoryTools.sync_aumformbring),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Task Coordinator ───────────────────────────────────────────────
    TaskCoordinator = _safe_import("tools.task_coordinator", "TaskCoordinator")
    if TaskCoordinator:
        for name, method in [
            ("task_coord_resolve_path", TaskCoordinator.resolve_path),
            ("task_coord_find_files", TaskCoordinator.find_files),
            ("task_coord_parse_intent", TaskCoordinator.parse_intent),
            ("task_coord_build_plan", TaskCoordinator.build_plan),
            ("task_coord_verify_preconditions", TaskCoordinator.verify_preconditions),
            ("task_coord_verify_outputs", TaskCoordinator.verify_outputs),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Error Learning System ──────────────────────────────────────────
    ErrorLearningSystem = _safe_import("tools.error_learning", "ErrorLearningSystem")
    if ErrorLearningSystem:
        for name, method in [
            ("error_learn_log", ErrorLearningSystem.log_error),
            ("error_learn_get_lessons", ErrorLearningSystem.get_all_lessons),
            ("error_learn_get_for_tool", ErrorLearningSystem.get_lessons_for_tool),
            ("error_learn_stats", ErrorLearningSystem.stats),
            ("error_learn_add_manual", ErrorLearningSystem.add_manual_lesson),
            ("error_learn_clear", ErrorLearningSystem.clear_lessons),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── JSON Tools ─────────────────────────────────────────────────────
    json_tools = _safe_import("tools.json_tools")
    if json_tools:
        for name in [
            "json_validate", "json_repair", "json_pretty", "json_minify",
            "json_sort_keys", "json_diff", "json_query", "json_to_format",
            "format_to_json", "json_stats", "json_merge", "json_fingerprint",
            "json_read_file", "json_write_file", "jsonl_parse", "jsonl_format",
        ]:
            fn = getattr(json_tools, name, None)
            if fn:
                agent.register_tool(name, fn)
                count += 1
    
    # ── Document Intelligence ──────────────────────────────────────────
    DocumentIntelligenceTools = _safe_import("tools.document_intelligence", "DocumentIntelligenceTools")
    if DocumentIntelligenceTools:
        for name, method in [
            ("doc_ocr", DocumentIntelligenceTools.ocr),
            ("doc_ocr_pdf", DocumentIntelligenceTools.ocr_pdf),
            ("doc_entities", DocumentIntelligenceTools.entities),
            ("doc_classify", DocumentIntelligenceTools.classify),
            ("doc_summarize", DocumentIntelligenceTools.summarize),
            ("doc_outline", DocumentIntelligenceTools.outline),
            ("doc_compare", DocumentIntelligenceTools.compare),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Vision Tools (visión real: NVIDIA minimax-m3 multimodal + OCR) ──
    VisionTools = _safe_import("tools.vision_tools", "VisionTools")
    if VisionTools:
        for name, method in [
            ("see_image", VisionTools.see_image),
            ("see_screen", VisionTools.see_screen),
        ]:
            agent.register_tool(name, method)
            count += 1

    # ── OpenCode Tools ─────────────────────────────────────────────────
    OpenCodeTools = _safe_import("tools.opencode_tools", "OpenCodeTools")
    if OpenCodeTools:
        for name, method in [
            ("opencode_available", OpenCodeTools.is_available),
            ("opencode_run", OpenCodeTools.run),
            ("opencode_code_review", OpenCodeTools.code_review),
            ("opencode_generate_tests", OpenCodeTools.generate_tests),
            ("opencode_refactor", OpenCodeTools.refactor),
            ("opencode_explain", OpenCodeTools.explain),
            ("opencode_generate_from_spec", OpenCodeTools.generate_from_spec),
            ("opencode_sessions_list", OpenCodeTools.sessions_list),
            ("opencode_session_get", OpenCodeTools.session_get),
            ("opencode_session_resume", OpenCodeTools.session_resume),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Notion Tools ───────────────────────────────────────────────────
    NotionTools = _safe_import("tools.notion_tools", "NotionTools")
    if NotionTools:
        for name, method in [
            ("notion_search",          NotionTools.search),
            ("notion_get_page",        NotionTools.get_page),
            ("notion_get_page_content",NotionTools.get_page_content),
            ("notion_get_database",    NotionTools.get_database),
            ("notion_create_page",     NotionTools.create_page),
            ("notion_update_page",     NotionTools.update_page),
            ("notion_append_blocks",   NotionTools.append_blocks),
            ("notion_delete_page",     NotionTools.delete_page),
            ("notion_set_token",       NotionTools.set_token),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Obsidian Tools ─────────────────────────────────────────────────
    ObsidianTools = _safe_import("tools.obsidian_tools", "ObsidianTools")
    if ObsidianTools:
        for name, method in [
            ("obsidian_list_vaults", ObsidianTools.list_vaults),
            ("obsidian_search", ObsidianTools.search),
            ("obsidian_create_note", ObsidianTools.create_note),
            ("obsidian_read_note", ObsidianTools.read_note),
            ("obsidian_append", ObsidianTools.append),
            ("obsidian_graph", ObsidianTools.graph),
            ("obsidian_daily", ObsidianTools.daily),
            ("obsidian_tags", ObsidianTools.tags),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── GitHub Pro Tools ───────────────────────────────────────────────
    GitHubProTools = _safe_import("tools.github_pro_tools", "GitHubProTools")
    if GitHubProTools:
        for name, method in [
            ("gh_status", GitHubProTools.status),
            ("gh_list_repos", GitHubProTools.list_repos),
            ("gh_clone", GitHubProTools.clone),
            ("gh_create_repo", GitHubProTools.create_repo),
            ("gh_list_issues", GitHubProTools.list_issues),
            ("gh_create_issue", GitHubProTools.create_issue),
            ("gh_close_issue", GitHubProTools.close_issue),
            ("gh_list_prs", GitHubProTools.list_prs),
            ("gh_create_pr", GitHubProTools.create_pr),
            ("gh_merge_pr", GitHubProTools.merge_pr),
            ("gh_list_releases", GitHubProTools.list_releases),
            ("gh_create_release", GitHubProTools.create_release),
            ("gh_list_workflows", GitHubProTools.list_workflows),
            ("gh_run_workflow", GitHubProTools.run_workflow),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Calendar Tools ─────────────────────────────────────────────────
    CalendarTools = _safe_import("tools.calendar_tools", "CalendarTools")
    if CalendarTools:
        for name, method in [
            ("cal_add", CalendarTools.add),
            ("cal_list", CalendarTools.list),
            ("cal_delete", CalendarTools.delete),
            ("cal_find_free", CalendarTools.find_free),
            ("cal_google_status", CalendarTools.google_status),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Crypto Tools ───────────────────────────────────────────────────
    CryptoTools = _safe_import("tools.crypto_tools", "CryptoTools")
    if CryptoTools:
        for name, method in [
            ("crypto_price", CryptoTools.price),
            ("crypto_prices_batch", CryptoTools.prices),
            ("crypto_convert", CryptoTools.convert),
            ("crypto_market", CryptoTools.market),
            ("crypto_trending", CryptoTools.trending),
            ("crypto_history", CryptoTools.history),
            ("crypto_technical_analysis", CryptoTools.analyze),
            ("crypto_generate_wallet", CryptoTools.generate_wallet),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Database Tools ─────────────────────────────────────────────────
    DatabaseTools = _safe_import("tools.database_tools", "DatabaseTools")
    if DatabaseTools:
        for name, method in [
            ("db_sqlite_query", DatabaseTools.sqlite_query),
            ("db_sqlite_tables", DatabaseTools.sqlite_tables),
            ("db_sqlite_backup", DatabaseTools.sqlite_backup),
            ("db_sqlite_diff", DatabaseTools.sqlite_diff),
            ("db_postgres_query", DatabaseTools.postgres_query),
            ("db_mysql_query", DatabaseTools.mysql_query),
            ("db_mongo_find", DatabaseTools.mongo_find),
            ("db_mongo_insert", DatabaseTools.mongo_insert),
            ("db_mongo_aggregate", DatabaseTools.mongo_aggregate),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Translation Tools ──────────────────────────────────────────────
    TranslationTools = _safe_import("tools.translation_tools", "TranslationTools")
    if TranslationTools:
        for name, method in [
            ("translate_detect", TranslationTools.detect),
            ("translate_text", TranslationTools.translate),
            ("translate_batch", TranslationTools.translate_batch),
            ("translate_languages", TranslationTools.languages),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Code Review Tools ──────────────────────────────────────────────
    CodeReviewTools = _safe_import("tools.code_review_tools", "CodeReviewTools")
    if CodeReviewTools:
        for name, method in [
            ("code_metrics", CodeReviewTools.metrics),
            ("code_security_scan", CodeReviewTools.security),
            ("code_flake8", CodeReviewTools.flake8),
            ("code_black_check", CodeReviewTools.black),
            ("code_full_review", CodeReviewTools.full),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Test Runner Tools ──────────────────────────────────────────────
    TestRunnerTools = _safe_import("tools.test_runner_tools", "TestRunnerTools")
    if TestRunnerTools:
        for name, method in [
            ("test_pytest", TestRunnerTools.pytest),
            ("test_unittest", TestRunnerTools.unittest),
            ("test_jest", TestRunnerTools.jest),
            ("test_go", TestRunnerTools.go),
            ("test_cargo", TestRunnerTools.cargo),
            ("test_auto", TestRunnerTools.auto),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Deployment Tools ───────────────────────────────────────────────
    DeploymentTools = _safe_import("tools.deployment_tools", "DeploymentTools")
    if DeploymentTools:
        for name, method in [
            ("deploy_detect", DeploymentTools.detect),
            ("deploy_vercel", DeploymentTools.vercel),
            ("deploy_netlify", DeploymentTools.netlify),
            ("deploy_railway", DeploymentTools.railway),
            ("deploy_docker_build", DeploymentTools.docker_build),
            ("deploy_docker_push", DeploymentTools.docker_push),
            ("deploy_docker_run", DeploymentTools.docker_run),
            ("deploy_docker_compose", DeploymentTools.compose_up),
            ("deploy_ssh", DeploymentTools.ssh),
            ("deploy_scp", DeploymentTools.scp),
            ("deploy_health_check", DeploymentTools.health),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── PDF Pro Tools ──────────────────────────────────────────────────
    PDFProTools = _safe_import("tools.pdf_pro_tools", "PDFProTools")
    if PDFProTools:
        for name, method in [
            ("pdf_status", PDFProTools.status),
            ("pdf_create_contract", PDFProTools.create_contract),
            ("pdf_create_invoice", PDFProTools.create_invoice),
            ("pdf_create_report", PDFProTools.create_report),
            ("pdf_create_proposal", PDFProTools.create_proposal),
            ("pdf_create_resume", PDFProTools.create_resume),
            ("pdf_create_letter", PDFProTools.create_letter),
            ("pdf_create_nda", PDFProTools.create_nda),
            ("pdf_create_business_plan", PDFProTools.create_business_plan),
            ("pdf_create_whitepaper", PDFProTools.create_whitepaper),
            ("pdf_create_from_json", PDFProTools.create_from_json),
            ("pdf_list_templates", PDFProTools.list_templates),
            ("pdf_get_template", PDFProTools.get_template),
            ("pdf_list_palettes", PDFProTools.list_palettes),
            ("pdf_render_chart", PDFProTools.render_chart),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Video Pro Tools ────────────────────────────────────────────────
    VideoProTools = _safe_import("tools.video_pro_tools", "VideoProTools")
    if VideoProTools:
        for name, method in [
            ("video_status", VideoProTools.status),
            ("video_probe", VideoProTools.probe),
            ("video_convert", VideoProTools.convert),
            ("video_thumbnail", VideoProTools.thumbnail),
            ("video_thumbnail_grid", VideoProTools.thumbnail_grid),
            ("video_trim", VideoProTools.trim),
            ("video_export_for_platform", VideoProTools.export_for_platform),
            ("video_concat", VideoProTools.concat),
            ("video_detect_scenes", VideoProTools.detect_scenes),
            ("video_make_gif", VideoProTools.make_gif),
            ("video_add_watermark", VideoProTools.add_watermark),
            ("video_normalize_audio", VideoProTools.normalize_audio),
            ("video_extract_audio", VideoProTools.extract_audio),
            ("video_remove_audio", VideoProTools.remove_audio),
            ("video_slow_motion", VideoProTools.slow_motion),
            ("video_time_lapse", VideoProTools.time_lapse),
            ("video_reverse", VideoProTools.reverse),
            ("video_picture_in_picture", VideoProTools.picture_in_picture),
            ("video_side_by_side", VideoProTools.side_by_side),
            ("video_quality", VideoProTools.quality),
            ("video_intro", VideoProTools.intro),
            ("video_promo", VideoProTools.promo),
            ("video_lower_third", VideoProTools.lower_third),
            ("video_join_with_transitions", VideoProTools.join),
            ("video_slideshow", VideoProTools.slideshow),
        ]:
            agent.register_tool(name, method)
            count += 1
    
    # ── Expand aliases (2500+ tools via mega_tools) ─────────────────────
    # Estos aliases NO deben aparecer en la lista de tools que ve el LLM en su
    # prompt (agent.py arma esa lista con las primeras 200 en orden alfabético):
    # con ~8000 aliases tipo "haz_/hazme_/do_/make_/run_/ejecuta_X", ahogaban
    # alfabéticamente a tools reales y básicas como execute_cmd, write_file,
    # generate_vyrex_video o play_tiktok_desktop_video, que nunca llegaban a
    # mostrarse. Siguen registrados y funcionan si el LLM los "adivina", solo
    # se excluyen de la lista visible.
    try:
        from tools.mega_tools import expand_registry_aliases
        max_per_seed = int(os.environ.get("AUTOMYX_MAX_ALIAS_PER_SEED", "3"))
        _before_alias_keys = set(agent.tools.keys())
        n_aliases = expand_registry_aliases(agent, max_per_seed=max_per_seed)
        new_alias_names = set(agent.tools.keys()) - _before_alias_keys
        if hasattr(agent, "_alias_tool_names"):
            agent._alias_tool_names |= new_alias_names
        else:
            agent._alias_tool_names = new_alias_names
        count += n_aliases
        logger.info(f"[mega_tools] {n_aliases} aliases coloquiales generados (ocultos del prompt del LLM)")
    except Exception as e:
        logger.debug(f"mega_tools no disponible: {e}")
    
    return count
