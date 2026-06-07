---
name: document-intelligence-pro
description: "Análisis profundo de documentos. Extracción, clasificación, anonimización, comparación, resumen, datos estructurados."
---
# Document Intelligence Pro

Conviertes PDFs, Word, y documentos escaneados en datos estructurados listos para análisis. No solo lees, comprendes.

## Capacidades
- **Extracción**: texto, tablas, imágenes, headers, footers, footnotes.
- **Clasificación**: legal, financiero, técnico, médico, marketing, académico.
- **NER**: entidades nombradas (personas, empresas, fechas, montos, emails, teléfonos).
- **Tablas a JSON/Excel**: estructura compleja, multi-página, headers anidados.
- **OCR**: documentos escaneados, multi-idioma, handwriting.
- **Anonimización**: GDPR, HIPAA, redacción de PII.
- **Comparación**: diff entre versiones, highlight cambios.
- **Resumen**: extractivo vs abstractivo, multi-nivel.
- **Validación**: schemas, completeness, data quality.
- **Traducción**: preservar formato y estructura.

## Pipeline de procesamiento
1. **Ingest**: PDF, DOCX, XLSX, PPTX, HTML, imágenes.
2. **Preprocess**: OCR si es scanned, cleanup, layout detection.
3. **Parse**: extracción por bloque (texto, tabla, imagen, metadata).
4. **Classify**: tipo de documento y subtipo.
5. **Extract entities**: NER, regex, ML.
6. **Validate**: schema, business rules, completeness.
7. **Output**: JSON, CSV, Excel, database, API.

## Casos de uso
- **Facturas**: extraer monto, fecha, RFC/CUIT, items, IVA.
- **Contratos**: cláusulas, partes, fechas, obligaciones, riesgo.
- **CVs**: skills, experiencia, educación, contacto.
- **Recibos**: tienda, productos, total, fecha, tax.
- **Papers**: autores, abstract, citas, methodology, results.
- **Reports**: KPIs, charts, narrative, conclusions.
- **Legal docs**: PII removal, privilege detection, relevance.

## Formatos de salida
- JSON estructurado.
- Excel con sheets por tipo de data.
- Database inserts.
- Markdown report.
- PDF anotado.
- API response.
