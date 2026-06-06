import os
from tools.pc_tools import PCTools

class HRTools:
    @staticmethod
    def read_pdf_text(file_path: str) -> str:
        try:
            import PyPDF2
            file_path = PCTools._resolve_path(file_path)
            if not os.path.exists(file_path): return f"❌ Archivo no encontrado: {file_path}"
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except ImportError:
            return "❌ PyPDF2 no está instalado. Por favor ejecuta: pip install PyPDF2"
        except Exception as e:
            return f"❌ Error leyendo PDF: {str(e)}"
        
    @staticmethod
    def read_all_cvs_in_folder(folder_path: str) -> str:
        try:
            folder_path = PCTools._resolve_path(folder_path)
            if not os.path.exists(folder_path): return f"❌ Carpeta no encontrada: {folder_path}"
            results = []
            for f in os.listdir(folder_path):
                if f.lower().endswith('.pdf'):
                    text = HRTools.read_pdf_text(os.path.join(folder_path, f))
                    # Limitamos el texto de cada CV para no desbordar la memoria
                    results.append(f"=== CV: {f} ===\n{text[:800]}...\n")
            return "\n".join(results) if results else "No se encontraron archivos PDF en la carpeta."
        except Exception as e:
            return f"❌ Error leyendo CVs: {str(e)}"
        
    @staticmethod
    def export_to_excel(data: str, output_path: str) -> str:
        try:
            import pandas as pd
            import json
            output_path = PCTools._resolve_path(output_path)
            
            try:
                parsed_data = json.loads(data)
                if not isinstance(parsed_data, list):
                    parsed_data = [parsed_data]
            except:
                parsed_data = [{"Información": data}]
            
            df = pd.DataFrame(parsed_data)
            df.to_excel(output_path, index=False)
            return f"✅ Datos exportados exitosamente a {output_path}"
        except ImportError:
            return "❌ Pandas u OpenPyXL no están instalados. Ejecuta: pip install pandas openpyxl"
        except Exception as e:
            return f"❌ Error exportando a Excel: {str(e)}"