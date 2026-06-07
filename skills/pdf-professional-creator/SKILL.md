---
name: pdf-professional-creator
description: "Experto en generación de PDFs empresariales profesionales (contratos, facturas, informes, propuestas, CVs, NDAs, whitepapers, business plans) usando la clase PDFProTools con reportlab y 8 paletas corporativas."
---

# PDF Professional Creator (Nivel Empresarial)

Esta habilidad te permite generar PDFs de **calidad editorial real**, no solo documentos con un título. Usa la clase `PDFProTools` del módulo `tools/pdf_pro_tools.py` (basada en reportlab) con 9 funciones `create_*()` y 8 paletas corporativas.

## Capacidades (9 tipos de documento)

### 1. `pdf_create_contract` — Contratos profesionales
- **Tipos soportados**: `services` (servicios), `employment` (empleo), `nda` (NDA), `lease` (arrendamiento), `sales` (compraventa), `partnership` (asociación).
- **Estructura**: header corporativo, partes identificadas, objeto del contrato, obligaciones, duración, terminación, jurisdicción, espacios de firma con líneas, fecha de firma.
- **Args clave**: `output_path`, `contract_type`, `party_a`, `party_b`, `terms` (lista de cláusulas), `effective_date`, `duration`, `jurisdiction`.

### 2. `pdf_create_invoice` — Facturas con tabla
- Header corporativo con logo, datos del emisor.
- Tabla con: concepto, cantidad, precio unitario, subtotal, IVA, total destacado.
- Datos del cliente, número de factura, fecha, condiciones de pago.
- **Args clave**: `output_path`, `invoice_number`, `date`, `due_date`, `from_company`, `to_client`, `line_items` (lista de dicts), `tax_rate`, `currency`, `notes`.

### 3. `pdf_create_report` — Informes con TOC
- **Portada** con título, subtítulo, autor, fecha, logo.
- **Tabla de contenidos** (TOC) generada automáticamente.
- **Secciones jerárquicas** (H1/H2/H3) con numeración.
- **Tablas estilizadas** + **gráficos matplotlib** embebidos.
- **Conclusiones y referencias** al final.
- **Args clave**: `output_path`, `title`, `author`, `sections` (lista de dicts con `heading`, `level`, `content`, `tables`, `charts`).

### 4. `pdf_create_proposal` — Propuestas comerciales
- Hero section con título impactante.
- Resumen ejecutivo.
- **Deliverables** con descripción y timeline.
- **Pricing tiers** (básico/pro/enterprise).
- **Términos y condiciones**.
- **CTA claro** con contacto.
- **Args clave**: `output_path`, `client_name`, `project_title`, `deliverables`, `timeline_weeks`, `pricing_tiers`, `terms`.

### 5. `pdf_create_resume` — Currículums Vitae
- **Sidebar** con datos de contacto, habilidades, idiomas, certificaciones.
- **Main** con experiencia, educación, proyectos destacados.
- Layout moderno a una o dos páginas.
- **Args clave**: `output_path`, `name`, `contact`, `summary`, `experience`, `education`, `skills`, `languages`, `certifications`.

### 6. `pdf_create_letter` — Cartas formales
- Header con remitente, fecha, destinatario.
- Asunto, saludo, cuerpo con párrafos, despedida, firma.
- Tono formal o informal configurable.
- **Args clave**: `output_path`, `from_name`, `from_address`, `to_name`, `to_address`, `date`, `subject`, `body`, `signature`.

### 7. `pdf_create_nda` — Acuerdos de Confidencialidad
- Header con partes y propósito.
- **Cláusulas completas**: definición de información confidencial, excepciones, plazo, jurisdicción, penalización.
- Firmas con líneas y testigos opcionales.
- **Args clave**: `output_path`, `disclosing_party`, `receiving_party`, `purpose`, `duration_years`, `jurisdiction`.

### 8. `pdf_create_business_plan` — Planes de Negocio
- Executive summary, mercado objetivo, análisis competitivo, modelo de ingresos, equipo, proyecciones financieras, roadmap.
- **Args clave**: `output_path`, `company_name`, `executive_summary`, `market_analysis`, `competitors`, `revenue_model`, `team`, `financials`, `roadmap_quarters`.

### 9. `pdf_create_whitepaper` — Whitepapers Técnicos
- Abstract, problema, solución, arquitectura, implementación, benchmarks, **referencias numeradas** estilo académico.
- **Args clave**: `output_path`, `title`, `abstract`, `sections`, `references` (lista de citas).

## Funciones auxiliares

- `pdf_create_from_json(output_path, data)`: detecta el tipo por las claves del dict y delega. Ideal para integración con agentes.
- `pdf_list_templates()`: lista plantillas pre-rellenadas (`contract_services`, `nda_standard`, `invoice_template`, `report_template`, `proposal_template`, `letter_formal`).
- `pdf_get_template(name)`: devuelve el JSON de una plantilla para personalizarla.
- `pdf_list_palettes()`: muestra las 8 paletas disponibles.
- `pdf_render_chart(data, labels, title, chart_type)`: genera gráfico matplotlib (bar, line, pie, scatter) para embeber en informes.

## Paletas disponibles (8)

1. **professional_blue**: azul corporativo (#1e3a8a) - banca, finanzas, legal
2. **corporate_gray**: gris carbón (#374151) - consultoría, corporativo
3. **tech_modern**: cian eléctrico (#0891b2) - tech, SaaS, startups
4. **elegant_gold**: dorado (#b45309) - lujo, hospitality, premium
5. **medical_clean**: azul médico (#0e7490) - salud, farma
6. **legal_classic**: verde legal (#166534) - bufetes, notaría
7. **creative_violet**: violeta (#7c3aed) - agencias, marketing, diseño
8. **eco_green**: verde natural (#15803d) - sostenibilidad, ONG

## Workflow de uso

### Paso 1: Identifica el tipo de documento
Analiza la solicitud del usuario y determina cuál de los 9 tipos encaja. Si el usuario dice "contrato" pero no especifica el subtipo, elige `services` por defecto.

### Paso 2: Recopila la información necesaria
Cada tipo requiere args específicos. Si faltan datos, pregunta al usuario O usa placeholders claros (ej. "[NOMBRE_EMPRESA]"). NO alucines datos críticos como CIF/NIF/RFC, importes o fechas.

### Paso 3: Llama a la función `pdf_create_*` correspondiente
```json
{
  "action": "pdf_create_invoice",
  "args": {
    "output_path": "C:\\Users\\COMPUMAX\\Downloads\\factura_001.pdf",
    "invoice_number": "INV-2026-001",
    "from_company": {"name": "ACME SL", "cif": "B12345678", "address": "Calle Mayor 1, Madrid"},
    "to_client": {"name": "Cliente SA", "address": "Av. Diagonal 100, Barcelona"},
    "line_items": [
      {"concept": "Servicios de consultoría", "quantity": 10, "unit_price": 150.00}
    ],
    "tax_rate": 0.21,
    "currency": "EUR"
  }
}
```

### Paso 4: Verifica el resultado
- Comprueba que el archivo existe con `task_coord_verify_outputs` o listando el directorio.
- El PDF generado tiene header, footer corporativo, número de página, tipografía consistente.

## Reglas de oro

- **USA SIEMPRE `PDFProTools` para PDFs** (9 funciones `create_*`).
- **NO generes PDFs con `write_file` plano** (eso es amateur).
- **NO uses fpdf2 con scripts desde cero** salvo que la skill lo pida explícitamente (es inferior a reportlab).
- **NO inventes datos críticos**: si falta CIF, dirección o importe, pregunta o usa placeholders `[COMPLETAR]`.
- **Resuelve rutas absolutas** con `task_coord_resolve_path` antes de guardar (ej. "descargas" → `C:\Users\COMPUMAX\Downloads`).
- **Elige la paleta según el sector** del cliente (no pongas medical_clean en un contrato de una startup tech).
- **Verifica que el archivo se creó** antes de informar al usuario que "el PDF está listo".

## Ejemplo: crear un contrato de servicios

```json
{
  "action": "pdf_create_contract",
  "args": {
    "output_path": "C:\\Users\\COMPUMAX\\Downloads\\contrato_servicios_2026.pdf",
    "contract_type": "services",
    "party_a": {"name": "ACME Consulting SL", "cif": "B12345678"},
    "party_b": {"name": "Tech Startup SRL", "cif": "B87654321"},
    "terms": [
      "Asesoramiento técnico en arquitectura cloud",
      "Reuniones semanales de seguimiento",
      "Entrega de informes mensuales",
      "Confidencialidad sobre la información del cliente"
    ],
    "duration": "12 meses",
    "effective_date": "2026-01-15",
    "jurisdiction": "Madrid, España"
  }
}
```

## Anti-patrones

- ❌ Crear el PDF con `write_file` + contenido textual plano.
- ❌ Generar scripts de 200 líneas con fpdf2 cuando PDFProTools ya tiene la función.
- ❌ Olvidar el header/footer corporativo.
- ❌ No verificar que el PDF se generó.
- ❌ Inventar datos del cliente (CIF, dirección, importes).
- ❌ Usar la misma paleta para todos los documentos sin importar el contexto.
