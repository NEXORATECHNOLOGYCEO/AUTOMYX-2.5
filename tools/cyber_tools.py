import socket
import subprocess
import requests

class CyberTools:
    @staticmethod
    def run_nmap_scan(target: str, flags: str = "-F") -> str:
        """
        Ejecuta un escaneo de red real usando Nmap.
        flags comunes: -F (rápido), -sV (versiones), -O (OS).
        Requiere tener nmap instalado en el sistema.
        """
        try:
            cmd = ["nmap"] + flags.split() + [target]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return f"🛡️ [RED TEAM] Reporte Nmap de {target}:\n{result.stdout}"
            else:
                return f"❌ Error de Nmap: {result.stderr}\n(Asegúrate de que nmap esté instalado en tu PATH)."
        except FileNotFoundError:
            return "❌ Error: Nmap no está instalado en este sistema. Usa port_scan como alternativa."
        except Exception as e:
            return f"❌ Error ejecutando escaneo avanzado: {str(e)}"

    @staticmethod
    def osint_search(target_name: str) -> str:
        """
        Herramienta de OSINT (Inteligencia de Fuentes Abiertas).
        Busca información pública usando APIs gratuitas o scraping básico.
        """
        try:
            # Simulación de un proceso complejo de OSINT para el ejemplo.
            # En un entorno real se conectarían APIs como Shodan, Hunter.io, etc.
            report = f"🕵️‍♂️ [OSINT] Recopilando inteligencia sobre: {target_name}\n"
            report += "--------------------------------------------------\n"
            
            # Buscar menciones en GitHub (ejemplo básico)
            gh_res = requests.get(f"https://api.github.com/search/users?q={target_name}")
            if gh_res.status_code == 200 and gh_res.json().get('total_count', 0) > 0:
                report += f"✅ GitHub: Posible coincidencia encontrada.\n"
                
            report += "⚠️ Nota: Para un análisis OSINT profundo, se recomienda habilitar las APIs de Shodan o integraciones con Maltego."
            return report
        except Exception as e:
            return f"❌ Error en OSINT: {str(e)}"

    @staticmethod
    def port_scan(target: str, ports: str) -> str:
        """Escanea puertos específicos en un objetivo. ports debe estar separado por comas: '80,443,22'"""
        try:
            port_list = [int(p.strip()) for p in ports.split(',')]
            open_ports = []
            closed_ports = []
            
            for port in port_list:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0) # 1 segundo de timeout
                result = sock.connect_ex((target, port))
                if result == 0:
                    open_ports.append(port)
                else:
                    closed_ports.append(port)
                sock.close()
                
            report = f"🔍 Escaneo completado en {target}:\n"
            report += f"✅ Puertos ABIERTOS: {open_ports if open_ports else 'Ninguno'}\n"
            report += f"❌ Puertos CERRADOS/FILTRADOS: {closed_ports if closed_ports else 'Ninguno'}"
            return report
        except Exception as e:
            return f"❌ Error en escaneo de puertos: {str(e)}"
