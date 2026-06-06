import time
import sys
import threading
import colorama
from colorama import Fore, Style, init

# Inicializar colorama para que funcione en CMD de Windows
init(autoreset=True)

def print_tui_banner():
    """Imprime el banner estilo TUI de OpenClaw/Automyx y actualiza el contador."""
    # Ocultar el cursor
    sys.stdout.write('\033[?25l')
    
    start_time = time.time()
    frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    try:
        # Imprimir la primera línea (que será estática, los tokens y config)
        print(f"\n{Fore.LIGHTBLACK_EX}agent main | session main (automyx-tui) | openai/gpt-oss-120b | think high | verbose full | reasoning | tokens 14k/128k (10%){Style.RESET_ALL}\n")
        print(f"{Fore.LIGHTBLACK_EX}────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────{Style.RESET_ALL}")
        
        while True:
            for frame in frames:
                elapsed = int(time.time() - start_time)
                # Construir la línea dinámica con colores RGB aproximados usando colorama
                # Naranja: Fore.LIGHTYELLOW_EX o \033[38;2;255;184;108m
                naranja = "\033[38;2;255;184;108m"
                gris = "\033[38;2;139;148;158m"
                reset = "\033[0m"
                
                # Mover el cursor hacia arriba 3 líneas, limpiar y reescribir
                sys.stdout.write('\033[3A')
                sys.stdout.write('\033[2K\n') # limpia linea de arriba (espacio)
                
                # La línea animada
                sys.stdout.write(f"\r{naranja}{frame} streaming {gris}•{naranja} {elapsed}s {gris}|{naranja} connected{reset}\n")
                
                # Bajar de nuevo el cursor
                sys.stdout.write('\033[1B')
                
                sys.stdout.flush()
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        # Mostrar el cursor de nuevo si se detiene
        sys.stdout.write('\033[?25h')
        print("\n\nSaliendo...")

if __name__ == "__main__":
    print_tui_banner()
