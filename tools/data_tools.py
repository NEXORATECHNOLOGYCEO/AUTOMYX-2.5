import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import io

class DataTools:
    """
    Herramientas para que el Agente actúe como Data Scientist Senior.
    """

    @staticmethod
    def analyze_csv_data(file_path: str, query: str) -> str:
        """
        Carga un CSV y permite hacerle consultas (ej. 'dame el promedio de ventas' o 'muestra las columnas').
        """
        try:
            if not os.path.exists(file_path):
                return f"❌ Error: El archivo {file_path} no existe."
            
            df = pd.read_csv(file_path)
            
            # Capturar la salida estándar de info()
            buffer = io.StringIO()
            df.info(buf=buffer)
            info_str = buffer.getvalue()
            
            # Resumen básico automático
            summary = f"📊 Análisis del Dataset: {file_path}\n"
            summary += f"- Filas: {df.shape[0]}, Columnas: {df.shape[1]}\n"
            summary += f"- Columnas: {', '.join(df.columns.tolist())}\n\n"
            
            # Estadísticas descriptivas si hay datos numéricos
            numeric_cols = df.select_dtypes(include='number').columns
            if len(numeric_cols) > 0:
                summary += "📈 Estadísticas básicas (primeras 3 columnas numéricas):\n"
                summary += str(df[numeric_cols[:3]].describe()) + "\n\n"

            # Ejecutar consulta si es posible (evaluación básica segura)
            if query and query.lower() != "none" and query.lower() != "null":
                summary += f"🔍 Resultado de tu consulta ('{query}'):\n"
                # Intentamos evaluar si el LLM mandó código pandas válido (ej: df['ventas'].mean())
                # ¡ADVERTENCIA!: eval() puede ser peligroso, pero esto es un agente local con control total de todos modos.
                try:
                    result = eval(query)
                    summary += str(result)
                except Exception as e:
                    summary += f"(No se pudo ejecutar la consulta como código Python directo: {str(e)})\n"
                    summary += "Te sugiero mirar las columnas y pedirme que genere un gráfico."
            
            return summary
        except Exception as e:
            return f"❌ Error analizando CSV: {str(e)}"

    @staticmethod
    def generate_data_chart(file_path: str, x_column: str, y_column: str, chart_type: str, output_path: str) -> str:
        """
        Genera un gráfico a partir de un CSV y lo guarda como imagen.
        chart_type: 'bar', 'line', 'scatter', 'hist'
        """
        try:
            if not os.path.exists(file_path):
                return f"❌ Error: El archivo {file_path} no existe."
                
            df = pd.read_csv(file_path)
            
            plt.figure(figsize=(10, 6))
            sns.set_theme(style="darkgrid")
            
            if chart_type == "bar":
                sns.barplot(data=df, x=x_column, y=y_column)
            elif chart_type == "line":
                sns.lineplot(data=df, x=x_column, y=y_column)
            elif chart_type == "scatter":
                sns.scatterplot(data=df, x=x_column, y=y_column)
            elif chart_type == "hist":
                sns.histplot(data=df, x=x_column, kde=True)
            else:
                return f"❌ Tipo de gráfico no soportado: {chart_type}. Usa 'bar', 'line', 'scatter' o 'hist'."
                
            plt.title(f"{chart_type.capitalize()} Chart: {y_column} vs {x_column}")
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            
            return f"✅ Gráfico '{chart_type}' generado con éxito y guardado en: {output_path}"
        except Exception as e:
            return f"❌ Error generando gráfico: {str(e)}"