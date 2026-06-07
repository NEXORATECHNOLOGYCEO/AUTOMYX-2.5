"""
Accountant Tools - Contador fiscal experto
Procesa facturas, concilia bancos, calcula impuestos y genera reportes oficiales para AFIP, SAT, SUNAT, AEAT.
"""
import os
import re
import csv
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


class AccountantTools:
    """Contador profesional con soporte multi-país."""

    AUDIT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexus_data", "accounting_audit.json")
    DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads", "Contabilidad")

    TAX_RATES = {
        "ar": {"iva_general": 0.21, "iva_reducido": 0.105, "iva_aumentado": 0.27, "iibb_caba": 0.035},
        "mx": {"iva_general": 0.16, "iva_frontera": 0.08, "ieps_general": 0.08, "isr_personas": 0.30},
        "pe": {"igv": 0.18, "isc": 0.10, "rta_4ta": 0.08},
        "co": {"iva_general": 0.19, "iva_reducido": 0.05, "ica": 0.00966, "retefuente": 0.04},
        "es": {"iva_general": 0.21, "iva_reducido": 0.10, "iva_super_reducido": 0.04, "irpf": 0.19},
    }

    # ---------- AUDIT ----------
    @staticmethod
    def _audit(action: str, payload: Dict[str, Any]):
        os.makedirs(os.path.dirname(AccountantTools.AUDIT_FILE), exist_ok=True)
        entry = {"timestamp": datetime.now().isoformat(), "action": action, "payload": payload}
        log = []
        if os.path.exists(AccountantTools.AUDIT_FILE):
            try:
                with open(AccountantTools.AUDIT_FILE, "r", encoding="utf-8") as f:
                    log = json.load(f)
            except Exception:
                log = []
        log.append(entry)
        with open(AccountantTools.AUDIT_FILE, "w", encoding="utf-8") as f:
            json.dump(log[-500:], f, ensure_ascii=False, indent=2)

    # ---------- INVOICE PARSING ----------
    @staticmethod
    def parse_invoice_pdf(file_path: str) -> Dict[str, Any]:
        """Extrae datos estructurados de una factura PDF."""
        if not os.path.exists(file_path):
            return {"error": f"Archivo no encontrado: {file_path}"}
        text = ""
        try:
            if pdfplumber:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text += (page.extract_text() or "") + "\n"
            elif PdfReader:
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text += (page.extract_text() or "") + "\n"
            else:
                return {"error": "Instala pdfplumber o PyPDF2 (pip install pdfplumber)"}
        except Exception as e:
            return {"error": f"Error leyendo PDF: {e}"}

        # Patrones típicos
        cuit = re.search(r"\b(\d{2}-?\d{8}-?\d)\b", text)
        rfc = re.search(r"\b([A-ZÃ‘&]{3,4}\d{6}[A-Z\d]{3})\b", text)
        ruc = re.search(r"\b(\d{11})\b", text)
        nif = re.search(r"\b([A-Z]?\d{8}[A-Z]?)\b", text)
        date = re.search(r"\b(\d{2}[-/]\d{2}[-/]\d{4})\b", text)
        total_match = re.search(r"(?:TOTAL|IMPORTE TOTAL|Total a pagar)[\s:$]*([\d.,]+)", text, re.IGNORECASE)
        iva_match = re.search(r"(?:IVA|I\.V\.A\.)[^\d]*(\d{1,2})%?[^\d]*([\d.,]+)", text, re.IGNORECASE)

        def parse_money(s: str) -> float:
            if not s:
                return 0.0
            s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 and s.count(".") > 0 else s.replace(",", ".")
            try:
                return round(float(re.sub(r"[^\d.]", "", s)), 2)
            except Exception:
                return 0.0

        result = {
            "file": file_path,
            "tax_id": (cuit or rfc or ruc or nif).group(1) if (cuit or rfc or ruc or nif) else "",
            "date": date.group(1) if date else "",
            "total": parse_money(total_match.group(1)) if total_match else 0.0,
            "iva_rate": int(iva_match.group(1)) if iva_match else None,
            "iva_amount": parse_money(iva_match.group(2)) if iva_match else 0.0,
            "raw_text_preview": text[:500],
        }
        AccountantTools._audit("parse_invoice_pdf", {"file": file_path, "total": result["total"]})
        return result

    @staticmethod
    def parse_invoice_xml(file_path: str) -> Dict[str, Any]:
        """Parsea CFDI (MX), FE (AR/PE), Facturae (ES)."""
        if not os.path.exists(file_path):
            return {"error": f"Archivo no encontrado: {file_path}"}
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            data = {"file": file_path, "root_tag": root.tag, "attributes": dict(root.attrib)}
            # Extracción genérica
            for el in root.iter():
                tag = el.tag.split("}")[-1].lower()
                if tag in {"total", "subtotal", "fecha", "rfc", "cuit", "ruc"}:
                    data[tag] = el.text or el.attrib.get("valor", "")
            return data
        except Exception as e:
            return {"error": f"Error parseando XML: {e}"}

    @staticmethod
    def bulk_import_folder(folder_path: str) -> Dict[str, Any]:
        """Procesa todas las facturas (PDF/XML) de una carpeta."""
        if not os.path.isdir(folder_path):
            return {"error": f"Carpeta no encontrada: {folder_path}"}
        results = []
        for root, _, files in os.walk(folder_path):
            for f in files:
                full = os.path.join(root, f)
                if f.lower().endswith(".pdf"):
                    results.append(AccountantTools.parse_invoice_pdf(full))
                elif f.lower().endswith(".xml"):
                    results.append(AccountantTools.parse_invoice_xml(full))
        total = sum(r.get("total", 0) for r in results if isinstance(r.get("total"), (int, float)))
        iva = sum(r.get("iva_amount", 0) for r in results if isinstance(r.get("iva_amount"), (int, float)))
        return {"count": len(results), "total_facturado": round(total, 2), "total_iva": round(iva, 2), "invoices": results}

    # ---------- BANK RECONCILIATION ----------
    @staticmethod
    def reconcile_bank_statement(statement_csv: str, invoices_json: str = None, tolerance: float = 0.01) -> Dict[str, Any]:
        """Concilia un extracto bancario con facturas."""
        if not os.path.exists(statement_csv):
            return {"error": f"CSV no encontrado: {statement_csv}"}
        movements = []
        with open(statement_csv, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                movements.append(row)

        invoices = []
        if invoices_json and os.path.exists(invoices_json):
            with open(invoices_json, "r", encoding="utf-8") as f:
                invoices = json.load(f)

        matched, unmatched_mov, unmatched_inv = [], [], list(invoices)
        for mov in movements:
            amount = None
            for key in ("amount", "monto", "importe", "Importe", "Monto"):
                if key in mov:
                    try:
                        amount = float(str(mov[key]).replace(",", "."))
                        break
                    except Exception:
                        pass
            if amount is None:
                continue
            match = next((inv for inv in unmatched_inv if abs(inv.get("total", 0) - abs(amount)) <= tolerance), None)
            if match:
                matched.append({"movement": mov, "invoice": match})
                unmatched_inv.remove(match)
            else:
                unmatched_mov.append(mov)
        result = {
            "matched_count": len(matched),
            "unmatched_movements": len(unmatched_mov),
            "unmatched_invoices": len(unmatched_inv),
            "matches": matched[:50],
            "pending_movements": unmatched_mov[:50],
            "pending_invoices": unmatched_inv[:50],
        }
        AccountantTools._audit("reconcile", {"matched": len(matched), "pending": len(unmatched_mov)})
        return result

    # ---------- TAX CALCULATION ----------
    @staticmethod
    def calculate_tax(country: str, tax_type: str, amount: float, period: str = None) -> Dict[str, Any]:
        """Calcula impuestos por país."""
        country = country.lower()
        rates = AccountantTools.TAX_RATES.get(country)
        if not rates:
            return {"error": f"País '{country}' no soportado. Disponibles: {list(AccountantTools.TAX_RATES.keys())}"}
        key = tax_type.lower().replace(" ", "_")
        rate = None
        for k, v in rates.items():
            if key in k or k.startswith(key):
                rate = v
                break
        if rate is None:
            return {"error": f"Impuesto '{tax_type}' no encontrado para {country}. Disponibles: {list(rates.keys())}"}
        tax = round(amount * rate, 2)
        return {
            "country": country,
            "tax_type": tax_type,
            "rate": rate,
            "base": amount,
            "tax_amount": tax,
            "total_with_tax": round(amount + tax, 2),
            "period": period or datetime.now().strftime("%Y-%m"),
        }

    @staticmethod
    def validate_tax_id(tax_id: str, country: str) -> Dict[str, Any]:
        """Valida CUIT (AR), RFC (MX), RUC (PE), NIF/CIF (ES)."""
        country = country.lower()
        tax_id = tax_id.replace("-", "").replace(" ", "").upper()

        if country == "ar" and len(tax_id) == 11 and tax_id.isdigit():
            mult = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
            total = sum(int(d) * m for d, m in zip(tax_id[:10], mult))
            chk = 11 - (total % 11)
            chk = 0 if chk == 11 else 9 if chk == 10 else chk
            return {"valid": chk == int(tax_id[10]), "country": "ar", "tax_id": tax_id}
        if country == "mx" and re.fullmatch(r"[A-ZÃ‘&]{3,4}\d{6}[A-Z\d]{3}", tax_id):
            return {"valid": True, "country": "mx", "tax_id": tax_id}
        if country == "pe" and len(tax_id) == 11 and tax_id.isdigit() and tax_id[0:2] in {"10", "15", "17", "20"}:
            return {"valid": True, "country": "pe", "tax_id": tax_id}
        if country == "es" and re.fullmatch(r"[A-Z]?\d{7,8}[A-Z0-9]", tax_id):
            return {"valid": True, "country": "es", "tax_id": tax_id}
        return {"valid": False, "country": country, "tax_id": tax_id, "reason": "formato inválido"}

    # ---------- REPORTS ----------
    @staticmethod
    def _save_report(country: str, report_name: str, content: str, extension: str = "txt") -> str:
        period = datetime.now().strftime("%Y/%m")
        out_dir = os.path.join(AccountantTools.DOWNLOADS, country.upper(), period)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{report_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.{extension}")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        return out_path

    @staticmethod
    def generate_afip_report(invoices: List[Dict[str, Any]], report_type: str = "iva_ventas") -> Dict[str, Any]:
        """Genera reporte AFIP (Argentina): Libro IVA Ventas/Compras."""
        lines = ["Tipo|PtoVenta|NroComp|FechaComp|CUIT|NetoGravado|IVA|Total"]
        for inv in invoices:
            lines.append(f"FA|0001|{inv.get('numero', '00000000')}|{inv.get('date', '')}|{inv.get('tax_id', '')}|"
                         f"{inv.get('total', 0) - inv.get('iva_amount', 0):.2f}|{inv.get('iva_amount', 0):.2f}|{inv.get('total', 0):.2f}")
        content = "\n".join(lines)
        path = AccountantTools._save_report("ar", f"AFIP_{report_type}", content, "txt")
        AccountantTools._audit("afip_report", {"type": report_type, "path": path, "rows": len(invoices)})
        return {"path": path, "rows": len(invoices), "type": report_type}

    @staticmethod
    def generate_sat_report(invoices: List[Dict[str, Any]], report_type: str = "diot") -> Dict[str, Any]:
        """Genera reporte SAT (México): DIOT, ContEle."""
        lines = ["RFC|Concepto|Base|IVA|Total"]
        for inv in invoices:
            lines.append(f"{inv.get('tax_id', '')}|{inv.get('concept', 'Servicios')}|"
                         f"{inv.get('total', 0) - inv.get('iva_amount', 0):.2f}|{inv.get('iva_amount', 0):.2f}|{inv.get('total', 0):.2f}")
        content = "\n".join(lines)
        path = AccountantTools._save_report("mx", f"SAT_{report_type}", content, "txt")
        return {"path": path, "rows": len(invoices), "type": report_type}

    @staticmethod
    def generate_sunat_report(invoices: List[Dict[str, Any]], report_type: str = "ple_ventas") -> Dict[str, Any]:
        """Genera PLE SUNAT (Perú)."""
        lines = []
        for inv in invoices:
            period = (inv.get("date", "")[:7] or datetime.now().strftime("%Y-%m")).replace("-", "")
            lines.append(f"{period}00|M00001|01|{inv.get('numero', '')}|{inv.get('date', '')}|"
                         f"6|{inv.get('tax_id', '')}|{inv.get('total', 0):.2f}|{inv.get('iva_amount', 0):.2f}")
        content = "\n".join(lines)
        path = AccountantTools._save_report("pe", f"SUNAT_{report_type}", content, "txt")
        return {"path": path, "rows": len(invoices), "type": report_type}

    @staticmethod
    def generate_aeat_report(invoices: List[Dict[str, Any]], report_type: str = "modelo_303") -> Dict[str, Any]:
        """Genera Modelo 303/390 AEAT (España)."""
        total_base = sum(inv.get("total", 0) - inv.get("iva_amount", 0) for inv in invoices)
        total_iva = sum(inv.get("iva_amount", 0) for inv in invoices)
        content = (f"AEAT {report_type.upper()} - Periodo {datetime.now().strftime('%Y-%m')}\n"
                   f"Base imponible: {total_base:.2f} EUR\n"
                   f"IVA repercutido: {total_iva:.2f} EUR\n"
                   f"Total facturas: {len(invoices)}\n")
        path = AccountantTools._save_report("es", f"AEAT_{report_type}", content, "txt")
        return {"path": path, "rows": len(invoices), "type": report_type, "iva_total": total_iva}

    @staticmethod
    def generate_financial_report(invoices: List[Dict[str, Any]], expenses: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Estado de Resultados ejecutivo."""
        expenses = expenses or []
        ingresos = sum(inv.get("total", 0) for inv in invoices)
        iva_repercutido = sum(inv.get("iva_amount", 0) for inv in invoices)
        gastos = sum(e.get("total", 0) for e in expenses)
        iva_soportado = sum(e.get("iva_amount", 0) for e in expenses)
        utilidad = ingresos - gastos
        content = (f"# Estado de Resultados\n\n"
                   f"## Ingresos\nTotal facturado: ${ingresos:,.2f}\nIVA repercutido: ${iva_repercutido:,.2f}\n\n"
                   f"## Gastos\nTotal gastos: ${gastos:,.2f}\nIVA soportado: ${iva_soportado:,.2f}\n\n"
                   f"## Resultado\n**Utilidad bruta: ${utilidad:,.2f}**\n"
                   f"**IVA a pagar/devolver: ${iva_repercutido - iva_soportado:,.2f}**\n")
        path = AccountantTools._save_report("general", "estado_resultados", content, "md")
        return {"path": path, "ingresos": ingresos, "gastos": gastos, "utilidad": utilidad}
