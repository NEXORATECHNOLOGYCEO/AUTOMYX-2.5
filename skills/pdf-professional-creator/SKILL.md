# PDF Professional Creator
## Descripción
Crea PDFs PERFECTOS, BIEN ESTRUCTURADOS y PROFESIONALES usando bibliotecas de Python como `fpdf2`.
## Instrucciones
### PASO 1: Analiza la solicitud del usuario
Determina qué tipo de PDF se necesita:
- Contrato (partes, cláusulas, fechas, firmas)
- Informe (título, índice, secciones, gráficos, tablas)
- Factura (número, fecha, cliente, conceptos, total)
- Currículum (datos personales, experiencia, educación, habilidades)
- Otro documento

### PASO 2: Instala la biblioteca necesaria (si no está instalada)
Ejecuta:
```
execute_cmd: pip install fpdf2
```

### PASO 3: Crea un script Python usando `fpdf2`
Escribe un script Python que genere el PDF con la estructura perfecta. El script debe incluir:
- Títulos en negrita, tamaños grandes
- Secciones y subsecciones organizadas
- Párrafos bien formateados
- Espaciado correcto
- Si es un contrato: espacios para firmas y fechas
- Si es un informe: tablas y listas

Ejemplo de script básico para un contrato:
```python
from fpdf import FPDF

class PDFContract(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 18)
        self.cell(200, 10, 'CONTRATO DE SERVICIOS', ln=True, align='C')
        self.ln(10)

pdf = PDFContract()
pdf.add_page()
pdf.set_font('Arial', '', 12)

# Sección 1: Partes del contrato
pdf.set_font('Arial', 'B', 14)
pdf.cell(200, 10, '1. PARTES DEL CONTRATO', ln=True)
pdf.set_font('Arial', '', 12)
pdf.cell(200, 10, 'CONTRATISTA: [Nombre completo del contratista]', ln=True)
pdf.cell(200, 10, 'CONTRATANTE: [Nombre completo del contratante]', ln=True)
pdf.ln(5)

# Sección 2: Objeto del contrato
pdf.set_font('Arial', 'B', 14)
pdf.cell(200, 10, '2. OBJETO DEL CONTRATO', ln=True)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 10, 'El contratista se obliga a prestar los siguientes servicios: [Descripción detallada de los servicios]')
pdf.ln(5)

# Sección 3: Duración
pdf.set_font('Arial', 'B', 14)
pdf.cell(200, 10, '3. DURACIÓN', ln=True)
pdf.set_font('Arial', '', 12)
pdf.cell(200, 10, 'El contrato tendrá una duración de [Número] meses, contados a partir de la fecha de firma.', ln=True)
pdf.ln(10)

# Espacio para firmas
pdf.set_font('Arial', 'B', 12)
pdf.cell(90, 10, '_________________________', ln=False)
pdf.cell(10, 10, '', ln=False)
pdf.cell(90, 10, '_________________________', ln=True)
pdf.cell(90, 10, 'Firma del Contratista', ln=False)
pdf.cell(10, 10, '', ln=False)
pdf.cell(90, 10, 'Firma del Contratante', ln=True)
pdf.cell(90, 10, 'Fecha: _______________', ln=False)
pdf.cell(10, 10, '', ln=False)
pdf.cell(90, 10, 'Fecha: _______________', ln=True)

pdf.output('contrato_profesional.pdf')
```

### PASO 4: Guarda el script
Usa `write_file` para guardar el script Python.

### PASO 5: Ejecuta el script
Usa `execute_cmd` para ejecutar el script Python y generar el PDF.

### PASO 6: Verifica el resultado
El PDF se generará perfectamente formateado y listo para usar.
