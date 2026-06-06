import os
import sys
import platform
import subprocess
import shutil

def run_cmd(cmd, shell=True):
    print(f"Ejecutando: {cmd}")
    subprocess.check_call(cmd, shell=shell)

def get_hardware_info():
    os_name = platform.system()
    arch = platform.machine().lower()
    gpu_vendor = "none"

    if os_name == "Windows" or os_name == "Linux":
        try:
            smi = subprocess.check_output("nvidia-smi", shell=True, stderr=subprocess.STDOUT).decode()
            if "NVIDIA" in smi:
                gpu_vendor = "nvidia"
        except:
            pass

        if gpu_vendor == "none" and os_name == "Windows":
            try:
                ps_cmd = 'Get-WmiObject win32_VideoController | Select-Object -ExpandProperty Name'
                gpu_info = subprocess.check_output(["powershell", "-Command", ps_cmd]).decode().lower()
                if "amd" in gpu_info or "radeon" in gpu_info:
                    gpu_vendor = "amd"
                elif "intel" in gpu_info or "arc" in gpu_info or "hd graphics" in gpu_info:
                    gpu_vendor = "intel"
            except:
                pass

        if gpu_vendor == "none" and os_name == "Linux" and "x86" in arch:
            try:
                gpu_info = subprocess.check_output("lspci | grep VGA", shell=True).decode().lower()
                if "amd" in gpu_info or "radeon" in gpu_info:
                    gpu_vendor = "amd"
                elif "intel" in gpu_info:
                    gpu_vendor = "intel"
            except:
                pass

    elif os_name == "Darwin":
        if "arm64" in arch:
            gpu_vendor = "apple"
        else:
            gpu_vendor = "intel_mac"
            
    elif os_name == "Linux" and ("arm" in arch or "aarch64" in arch):
        gpu_vendor = "raspberry"

    return os_name, arch, gpu_vendor

def install_dependencies():
    print("==================================================")
    print("    INSTALADOR MULTI-PLATAFORMA AUTOMYX v2.5      ")
    print("  CON AUMFORMBRING Y NEXUS CORE - ¡ULTRA IMPACTANTE!  ")
    print("==================================================")

    os_name, arch, gpu_vendor = get_hardware_info()
    
    print(f"Sistema Detectado: {os_name}")
    print(f"Arquitectura: {arch}")
    print(f"Acelerador Gráfico / Procesador: {gpu_vendor.upper()}")
    print("==================================================")

    # 1. Instalar requerimientos base (ignorando torch para instalarlo custom)
    print("Instalando dependencias base...")
    base_reqs = "fastapi uvicorn openai playwright pyautogui mss Pillow python-telegram-bot pywhatkit python-multipart jinja2 pydantic pytesseract edge-tts yt-dlp requests beautifulsoup4 pyperclip openai-whisper"
    run_cmd(f"{sys.executable} -m pip install --upgrade pip")
    run_cmd(f"{sys.executable} -m pip install {base_reqs}")

    # 2. Instalar Playwright browsers
    print("Instalando navegadores de Playwright...")
    run_cmd(f"{sys.executable} -m playwright install")

    # 3. Instalación de PyTorch adaptada al hardware
    print("Configurando motor de IA (PyTorch) optimizado para tu hardware...")
    if os_name == "Darwin":
        if gpu_vendor == "apple":
            print("Optimizando para Apple Silicon (M1/M2/M3/M4) usando Metal Performance Shaders (MPS)...")
            run_cmd(f"{sys.executable} -m pip install --pre torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/nightly/cpu")
        else:
            print("Optimizando para Mac Intel (CPU)...")
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio")
            
    elif os_name == "Windows":
        if gpu_vendor == "nvidia":
            print("Optimizando para Windows NVIDIA usando CUDA 12.1...")
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        elif gpu_vendor == "amd":
            print("Optimizando para Windows AMD usando DirectML...")
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio")
            run_cmd(f"{sys.executable} -m pip install torch-directml")
        elif gpu_vendor == "intel":
            print("Optimizando para Windows Intel Core Ultra / iGPU usando OpenVINO / Intel Extension...")
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio")
            run_cmd(f"{sys.executable} -m pip install intel_extension_for_pytorch")
        else:
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio")

    elif os_name == "Linux":
        if gpu_vendor == "raspberry":
            print("Optimizando para Raspberry Pi (ARM)...")
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")
        elif gpu_vendor == "nvidia":
            print("Optimizando para Linux NVIDIA usando CUDA 12.1...")
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        elif gpu_vendor == "amd":
            print("Optimizando para Linux AMD usando ROCm...")
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.6")
        elif gpu_vendor == "intel":
            print("Optimizando para Linux Intel usando Intel Extension...")
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio")
            run_cmd(f"{sys.executable} -m pip install intel_extension_for_pytorch")
        else:
            run_cmd(f"{sys.executable} -m pip install torch torchvision torchaudio")

    print("\n¡Instalación completada exitosamente!")
    print("Puedes iniciar Automyx ejecutando: python api/main.py")

if __name__ == "__main__":
    install_dependencies()
