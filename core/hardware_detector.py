import platform
import os
import sys
import subprocess
import logging

logger = logging.getLogger("HardwareDetector")

class HardwareConfig:
    def __init__(self):
        self.os_name = platform.system()
        self.arch = platform.machine().lower()
        self.gpu_vendor = "none"
        self.device = "cpu"
        self.dtype = "float32"
        self.acceleration_backend = "none"
        
        self.user_home = os.path.expanduser("~")
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self._detect_hardware()

    def _detect_hardware(self):
        if self.os_name == "Darwin":
            self._detect_mac()
        elif self.os_name == "Windows":
            self._detect_windows()
        elif self.os_name == "Linux":
            if "arm" in self.arch or "aarch64" in self.arch:
                self._detect_raspberry_pi()
            else:
                self._detect_linux()

    def _detect_mac(self):
        if self.arch == "arm64":
            self.gpu_vendor = "apple"
            self.device = "mps"
            self.dtype = "float16" # MPS handles float16 faster on Apple Silicon
            self.acceleration_backend = "mps"
            logger.info("Detected Apple Silicon (M-series). Using MPS for acceleration.")
        else:
            self.gpu_vendor = "intel_mac"
            self.device = "cpu"
            self.acceleration_backend = "cpu"
            logger.info("Detected Intel Mac. Using CPU.")

    def _detect_windows(self):
        try:
            # Check for NVIDIA
            smi_output = subprocess.check_output("nvidia-smi", shell=True, stderr=subprocess.STDOUT).decode()
            if "NVIDIA" in smi_output:
                self.gpu_vendor = "nvidia"
                self.device = "cuda"
                self.dtype = "float16"
                self.acceleration_backend = "cuda"
                logger.info("Detected NVIDIA GPU on Windows. Using CUDA (FP16).")
                return
        except Exception:
            pass

        try:
            # Try to detect AMD or Intel via wmic or PowerShell
            ps_cmd = 'Get-WmiObject win32_VideoController | Select-Object -ExpandProperty Name'
            gpu_info = subprocess.check_output(["powershell", "-Command", ps_cmd]).decode().lower()
            
            if "amd" in gpu_info or "radeon" in gpu_info:
                self.gpu_vendor = "amd"
                self.device = "dml" # DirectML for Windows AMD
                self.dtype = "float16"
                self.acceleration_backend = "directml"
                logger.info("Detected AMD GPU on Windows. Using DirectML.")
            elif "intel" in gpu_info or "arc" in gpu_info or "hd graphics" in gpu_info:
                self.gpu_vendor = "intel"
                self.device = "cpu" # Intel extension for PyTorch / OpenVINO
                self.acceleration_backend = "openvino"
                logger.info("Detected Intel CPU/iGPU on Windows. Optimizing for OpenVINO / Intel Extension.")
            else:
                self.device = "cpu"
                logger.info("No specific GPU detected on Windows. Using CPU.")
        except Exception:
            self.device = "cpu"

    def _detect_linux(self):
        try:
            # Check for NVIDIA
            smi_output = subprocess.check_output("nvidia-smi", shell=True, stderr=subprocess.STDOUT).decode()
            if "NVIDIA" in smi_output:
                self.gpu_vendor = "nvidia"
                self.device = "cuda"
                self.dtype = "float16"
                self.acceleration_backend = "cuda"
                logger.info("Detected NVIDIA GPU on Linux. Using CUDA (FP16).")
                return
        except Exception:
            pass
            
        try:
            gpu_info = subprocess.check_output("lspci | grep VGA", shell=True).decode().lower()
            if "amd" in gpu_info or "radeon" in gpu_info:
                self.gpu_vendor = "amd"
                self.device = "cuda" # PyTorch ROCm maps to 'cuda' device string
                self.dtype = "float16"
                self.acceleration_backend = "rocm"
                logger.info("Detected AMD GPU on Linux. Using ROCm.")
            elif "intel" in gpu_info:
                self.gpu_vendor = "intel"
                self.device = "cpu"
                self.acceleration_backend = "openvino"
                logger.info("Detected Intel GPU on Linux. Optimizing for OpenVINO.")
        except Exception:
            self.device = "cpu"

    def _detect_raspberry_pi(self):
        self.gpu_vendor = "broadcom"
        self.device = "cpu"
        self.dtype = "float32"
        self.acceleration_backend = "tflite"
        logger.info("Detected Raspberry Pi (ARM). Optimizing for low-power edge compute.")

    def get_torch_device(self):
        """Returns the appropriate PyTorch device string."""
        import torch
        if self.device == "cuda" and torch.cuda.is_available():
            return "cuda"
        elif self.device == "mps" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        elif self.acceleration_backend == "directml":
            try:
                import torch_directml
                return torch_directml.device()
            except ImportError:
                return "cpu"
        return "cpu"
        
    def get_torch_dtype(self):
        import torch
        if self.dtype == "float16":
            return torch.float16
        elif self.dtype == "bfloat16":
            return torch.bfloat16
        return torch.float32

# Singleton instance
hw_config = HardwareConfig()
