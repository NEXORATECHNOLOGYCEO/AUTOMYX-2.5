"""
Banner oficial de Automyx para la terminal
"""
import sys
import io
from colorama import Fore, Style, init

# Forzar codificación UTF-8 para Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Inicializar colorama
init(autoreset=True)

def print_automyx_banner(model_name="nvidia/gpt-oss-120b", show_details=True):
    """Imprime el banner oficial de Automyx, estilo Hermes"""
    from datetime import datetime
    import os
    
    date_str = datetime.now().strftime("%Y.%m.%d")
    
    banner = f"""
{Fore.YELLOW}{Style.BRIGHT} █████╗ ██╗   ██╗████████╗████████╗████████╗██████╗ ██╗   ██╗██╗  ██╗
██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗██╔═════╝██╔══██╗╚██╗ ██╔╝╚██╗██╔╝
███████║██║   ██║   ██║   ██║   ██║████████╗██████╔╝ ╚████╔╝  ╚███╔╝ 
██╔══██║██║   ██║   ██║   ██║   ██║╚═════██║██╔══██╗  ╚██╔╝   ██╔██╗ 
██║  ██║╚██████╔╝   ██║   ████████║████████║██║  ██║   ██║   ██╔╝ ██╗
╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═══════╝╚═══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝{Style.RESET_ALL}

{Fore.YELLOW}Automyx Agent v2.5.0 ({date_str}) · upstream 0xA1B2C3{Style.RESET_ALL}

{Fore.CYAN}  {Style.BRIGHT}Available Tools{Style.RESET_ALL}
{Fore.YELLOW}  browser: {Fore.WHITE}deep_web_scrape, ai_form_filler, analyze_browser_screen, open_website, ...
{Fore.YELLOW}  code_execution: {Fore.WHITE}execute_cmd, use_terminal_window, check_system_resources
{Fore.YELLOW}  cronjob: {Fore.WHITE}schedule_task, list_scheduled_tasks, cancel_task
{Fore.YELLOW}  file: {Fore.WHITE}read_file, write_file, copy_file, move_file, delete_file, list_directory, ...
{Fore.YELLOW}  gui_automation: {Fore.WHITE}mouse_click, type_text, press_key, find_and_click_image, screenshot
{Fore.YELLOW}  memory: {Fore.WHITE}aumformbring_store, nexus_profile, create_skill, log_conversation, recall_conversation
{Fore.YELLOW}  orchestration: {Fore.WHITE}create_workflow, run_workflow, create_plan, make_api_request
  {Fore.LIGHTBLACK_EX}(and 24 more toolsets...){Style.RESET_ALL}

{Fore.CYAN}  {Style.BRIGHT}Available Skills{Style.RESET_ALL}
{Fore.YELLOW}  3d-blender: {Fore.WHITE}execute_blender_python_code, generate_professional_3d_video, generate_cinematic_environment, ...
{Fore.YELLOW}  audio-mlops: {Fore.WHITE}apply_autotune, mix_music, master_audio, text_to_speech, audiocraft-audio-generation
{Fore.YELLOW}  autonomous-ai: {Fore.WHITE}project_autopilot, openclaw-core, hermes-agent, auto_improve_project, claude-code
{Fore.YELLOW}  cyber-security: {Fore.WHITE}port_scan, run_nmap_scan, osint_search, godmode, red-teaming
{Fore.YELLOW}  data-science: {Fore.WHITE}analyze_csv_data, generate_data_chart, export_to_excel, jupyter-live-kernel
{Fore.YELLOW}  devops: {Fore.WHITE}manage_docker_container, webhook-subscriptions, codebase-inspection
{Fore.YELLOW}  media-gen: {Fore.WHITE}generate_vyrex_video, generate_gemini_video, generate_gemini_image, play_youtube_video
{Fore.YELLOW}  productivity: {Fore.WHITE}read_recent_emails, create_email_draft, read_pdf_text, read_all_cvs_in_folder, notion, ocr
{Fore.YELLOW}  social-media: {Fore.WHITE}send_whatsapp, send_telegram, post_facebook, upload_tiktok, play_tiktok_desktop_video, xitter
{Fore.YELLOW}  software-dev: {Fore.WHITE}open_vscode, open_program, create_and_run_script, detect_bugs, fix_bugs, requesting-code-review
{Fore.YELLOW}  video-editing: {Fore.WHITE}trim_video, auto_subtitles, create_tiktok_edit, advanced_video_editor, professional_color_grading
  
  {Fore.LIGHTBLACK_EX}108 tools · 56 skills · /help for commands{Style.RESET_ALL}

{Fore.CYAN}  {Style.BRIGHT}Agent Core{Style.RESET_ALL}
{Fore.YELLOW}  Model:{Fore.WHITE} {model_name}
{Fore.YELLOW}  Session:{Fore.WHITE} {datetime.now().strftime('%Y%m%d_%H%M%S')}
"""
    print(banner)
