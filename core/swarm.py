"""
AUTOMYX — SWARM ENGINE (trabajos masivos estilo enterprise)
============================================================
Cola masiva de tareas (10.000+ items) atendidas en paralelo contra el modelo
activo: multichat real con límite de concurrencia, reintentos con backoff,
resultados incrementales en JSONL (reanudable), dashboard en vivo y plantillas
para los usos más comunes de empresas.

A diferencia del orquestador multi-agente (agentes completos con Soul.md,
~90k tokens c/u), cada worker del swarm es una llamada DIRECTA al modelo
(~0.5-2k tokens por item) — es lo único que hace viable procesar miles.
"""
from __future__ import annotations

import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.text import Text
    RICH = True
except ImportError:
    RICH = False

MAX_ITEMS       = 50_000
MAX_CONCURRENCY = 128
DEF_CONCURRENCY = 8

_B = "#00AAFF"
_G = "#5EE6A8"
_R = "#FF4444"
_D = "#4A6A8A"
_W = "#F0F6FF"
_T = "#00D4AA"


# ── Plantillas enterprise (lo que más usan empresas de todo tipo) ─────────────
TEMPLATES: Dict[str, Dict[str, str]] = {
    "soporte_cliente": {
        "desc": "Responde tickets/quejas de clientes con empatía y solución",
        "prompt": "Eres un agente de soporte al cliente excelente. Responde este ticket con empatía, solución concreta y tono profesional. Ticket:\n{item}",
    },
    "clasificar_leads": {
        "desc": "Clasifica leads de ventas: caliente/tibio/frío + razón",
        "prompt": "Clasifica este lead de ventas como CALIENTE, TIBIO o FRIO y explica en una línea por qué. Responde JSON {{\"clase\": \"...\", \"razon\": \"...\"}}. Lead:\n{item}",
    },
    "email_frio": {
        "desc": "Email de ventas en frío personalizado por prospecto",
        "prompt": "Escribe un email de ventas en frío, corto (máx 120 palabras), personalizado y sin sonar a spam, para este prospecto:\n{item}",
    },
    "descripcion_producto": {
        "desc": "Descripción de producto lista para ecommerce (SEO)",
        "prompt": "Escribe una descripción de producto para ecommerce: título atractivo, 2 párrafos vendedores, 5 bullets de beneficios y keywords SEO. Producto:\n{item}",
    },
    "traducir": {
        "desc": "Traducción profesional (indica idioma destino en la instrucción)",
        "prompt": "Traduce el siguiente texto de forma natural y profesional. {extra}\nTexto:\n{item}",
    },
    "resumen_documento": {
        "desc": "Resumen ejecutivo de documento/texto largo",
        "prompt": "Haz un resumen ejecutivo de máximo 5 bullets con lo esencial y accionable de este texto:\n{item}",
    },
    "sentimiento_reviews": {
        "desc": "Análisis de sentimiento de reseñas: positivo/negativo/neutro + tema",
        "prompt": "Analiza esta reseña. Responde JSON {{\"sentimiento\": \"positivo|negativo|neutro\", \"tema\": \"...\", \"accion_sugerida\": \"...\"}}. Reseña:\n{item}",
    },
    "post_redes": {
        "desc": "Post para redes sociales con hook + CTA + hashtags",
        "prompt": "Crea un post viral para redes sociales sobre el tema dado: hook potente en la primera línea, cuerpo breve, CTA y 5 hashtags. Tema:\n{item}",
    },
    "extraer_datos": {
        "desc": "Extrae datos estructurados (facturas, contactos, pedidos) a JSON",
        "prompt": "Extrae todos los datos estructurados de este texto (nombres, fechas, montos, emails, teléfonos, items) y responde SOLO JSON. Texto:\n{item}",
    },
    "cv_screening": {
        "desc": "RRHH: evalúa CV vs puesto → apto/no apto + fortalezas",
        "prompt": "Como reclutador, evalúa este candidato. Responde JSON {{\"apto\": true/false, \"puntaje\": 0-10, \"fortalezas\": [...], \"riesgos\": [...]}}. {extra}\nCandidato:\n{item}",
    },
    "responder_reviews": {
        "desc": "Responde reseñas públicas (Google/Amazon) cuidando la marca",
        "prompt": "Responde esta reseña pública como la marca: agradece, resuelve si hay queja, tono humano y corto. Reseña:\n{item}",
    },
    "faq": {
        "desc": "Genera pregunta frecuente + respuesta a partir de un tema",
        "prompt": "Genera la mejor respuesta clara y completa para esta pregunta frecuente de clientes:\n{item}",
    },
}


def load_items(source: str) -> List[str]:
    """Carga items desde .txt (línea por item), .csv (fila por item) o .jsonl."""
    p = Path(source)
    if not p.exists():
        raise FileNotFoundError(source)
    ext = p.suffix.lower()
    items: List[str] = []
    if ext == ".jsonl":
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                items.append(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False))
            except Exception:
                items.append(line)
    elif ext == ".csv":
        with open(p, encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                items.append(json.dumps(row, ensure_ascii=False))
    else:
        items = [l.strip() for l in p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    return items[:MAX_ITEMS]


class SwarmEngine:
    """Multichat masivo: N items → llamadas directas al modelo con semáforo."""

    def __init__(self, model: str, concurrency: int = DEF_CONCURRENCY,
                 console: Optional[Any] = None, max_tokens: int = 700):
        self.model = model
        self.concurrency = max(1, min(int(concurrency), MAX_CONCURRENCY))
        self.console = console
        self.max_tokens = max_tokens
        from core.agent import ModelProvider
        client = ModelProvider.get_client(model)
        self._base = str(client.base_url).rstrip("/")
        self._key = client.api_key
        self._model_id = ModelProvider.get_display_name(model)
        self.stats = {"done": 0, "fail": 0, "in_tok": 0, "out_tok": 0,
                      "running": 0, "t0": 0.0, "last": []}

    # ── worker ────────────────────────────────────────────────────────────────
    async def _one(self, hx, sem: asyncio.Semaphore, idx: int, prompt: str,
                   out_fh, lock: asyncio.Lock) -> None:
        async with sem:
            self.stats["running"] += 1
            rec: Dict[str, Any] = {"id": idx, "ok": False}
            for attempt in range(3):
                try:
                    r = await hx.post(
                        f"{self._base}/chat/completions",
                        json={"model": self._model_id,
                              "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": self.max_tokens},
                        headers={"Authorization": f"Bearer {self._key}"},
                        timeout=180)
                    if r.status_code in (429, 500, 502, 503, 504):
                        await asyncio.sleep(2 * (attempt + 1) + idx % 3)
                        continue
                    r.raise_for_status()
                    d = r.json()
                    rec["ok"] = True
                    rec["result"] = (d["choices"][0]["message"]["content"] or "").strip()
                    u = d.get("usage") or {}
                    self.stats["in_tok"] += u.get("prompt_tokens", 0)
                    self.stats["out_tok"] += u.get("completion_tokens", 0)
                    break
                except Exception as e:
                    rec["error"] = str(e)[:200]
                    await asyncio.sleep(1.5 * (attempt + 1))
            self.stats["running"] -= 1
            if rec["ok"]:
                self.stats["done"] += 1
                prev = rec["result"].replace("\n", " ")[:70]
            else:
                self.stats["fail"] += 1
                prev = f"✗ {rec.get('error', '?')[:60]}"
            self.stats["last"] = (self.stats["last"] + [(idx, rec["ok"], prev)])[-3:]
            async with lock:
                out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out_fh.flush()

    async def _run_async(self, prompts: Dict[int, str], out_path: Path) -> None:
        import httpx
        sem = asyncio.Semaphore(self.concurrency)
        lock = asyncio.Lock()
        limits = httpx.Limits(max_connections=self.concurrency + 8,
                              max_keepalive_connections=self.concurrency)
        with open(out_path, "a", encoding="utf-8") as out_fh:
            async with httpx.AsyncClient(limits=limits) as hx:
                await asyncio.gather(*(self._one(hx, sem, i, p, out_fh, lock)
                                       for i, p in prompts.items()))

    # ── dashboard ─────────────────────────────────────────────────────────────
    def _render(self, total: int) -> "Text":
        s = self.stats
        el = max(time.time() - s["t0"], 0.001)
        done_all = s["done"] + s["fail"]
        rate = done_all / el
        eta = (total - done_all) / rate if rate > 0 else 0
        cost = self._cost(s["in_tok"], s["out_tok"])
        t = Text()
        t.append(f"\n  ⚡ SWARM  ", style=f"bold {_T}")
        t.append(f"{done_all}/{total}", style=f"bold {_W}")
        t.append(f"  ·  {s['running']} en vuelo", style=f"bold {_B}")
        if s["fail"]:
            t.append(f"  ·  {s['fail']} fallos", style=f"bold {_R}")
        t.append(f"  ·  {rate:.1f} items/s  ·  ETA {int(eta // 60)}m{int(eta % 60):02d}s", style=f"dim {_D}")
        t.append(f"\n     ↕ {(s['in_tok'] + s['out_tok']) / 1000:.1f}k tokens  ·  ${cost:.3f}", style=f"dim {_D}")
        bar_w, frac = 40, (done_all / total if total else 0)
        t.append(f"\n     [{'█' * int(bar_w * frac)}{'░' * (bar_w - int(bar_w * frac))}] {frac * 100:.0f}%\n", style=_T)
        for idx, ok, prev in s["last"]:
            t.append(f"     {'✓' if ok else '✗'} ", style=f"bold {_G if ok else _R}")
            t.append(f"#{idx}  {prev}\n", style=f"dim {_D}")
        return t

    def _cost(self, itok: int, otok: int) -> float:
        try:
            from core.token_tracker import _cost_for
            return _cost_for(self.model, itok, otok)
        except Exception:
            return (itok + otok) / 1_000_000 * 0.5

    @staticmethod
    def estimate(n_items: int, model: str) -> tuple:
        """(tokens, usd) estimados: ~1.5k tokens por item (1k in + 500 out)."""
        itok, otok = 1000 * n_items, 500 * n_items
        try:
            from core.token_tracker import _cost_for
            usd = _cost_for(model, itok, otok)
        except Exception:
            usd = (itok + otok) / 1_000_000 * 0.5
        return itok + otok, usd

    # ── entrada principal ─────────────────────────────────────────────────────
    def run(self, items: List[str], instruction: str = "",
            template: str = "", out_dir: Optional[str] = None) -> Dict[str, Any]:
        items = items[:MAX_ITEMS]
        total = len(items)
        if not total:
            return {"ok": False, "error": "sin items"}

        if template and template in TEMPLATES:
            tpl = TEMPLATES[template]["prompt"]
            prompts = {i: tpl.format(item=it, extra=instruction or "")
                       for i, it in enumerate(items)}
        elif instruction:
            base = instruction if "{item}" in instruction else instruction + "\n\n{item}"
            prompts = {i: base.replace("{item}", it).replace("{i}", str(i)).strip()
                       for i, it in enumerate(items)}
        else:
            prompts = {i: it for i, it in enumerate(items)}

        run_dir = Path(out_dir or os.getcwd()) / "swarm_results" / time.strftime("swarm_%Y%m%d_%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / "results.jsonl"

        # reanudar: saltar ids ya presentes si el archivo existe
        done_ids = set()
        if out_path.exists():
            for line in out_path.read_text(encoding="utf-8").splitlines():
                try:
                    done_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
            prompts = {i: p for i, p in prompts.items() if i not in done_ids}

        self.stats.update({"done": len(done_ids), "t0": time.time()})

        if RICH and self.console:
            with Live(self._render(total), console=self.console,
                      refresh_per_second=4, transient=False) as live:
                async def _tick():
                    task = asyncio.ensure_future(self._run_async(prompts, out_path))
                    while not task.done():
                        live.update(self._render(total))
                        await asyncio.sleep(0.25)
                    await task
                    live.update(self._render(total))
                asyncio.run(_tick())
        else:
            asyncio.run(self._run_async(prompts, out_path))

        s = self.stats
        cost = self._cost(s["in_tok"], s["out_tok"])
        summary = {
            "ok": True, "total": total, "done": s["done"], "fail": s["fail"],
            "tokens": s["in_tok"] + s["out_tok"], "cost_usd": round(cost, 4),
            "elapsed_s": round(time.time() - s["t0"], 1),
            "results_file": str(out_path), "dir": str(run_dir),
        }
        (run_dir / "resumen.json").write_text(
            json.dumps({**summary, "instruction": instruction, "template": template},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
