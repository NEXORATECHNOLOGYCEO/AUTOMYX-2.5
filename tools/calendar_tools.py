"""
Calendar Tools - Google Calendar, Outlook, iCal
================================================
Crea eventos, lista próximos, busca disponibilidad. Usa iCal como fallback
y stubs para Google/Outlook via OAuth.
"""
from __future__ import annotations

import os
import re
import json
import uuid
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from icalendar import Calendar, Event
    ICAL_AVAILABLE = True
except ImportError:
    ICAL_AVAILABLE = False

ICS_FILE = Path(__file__).parent.parent / "state" / "calendar.ics"


def _ensure_storage():
    ICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ICS_FILE.exists():
        cal = Calendar()
        cal.add("prodid", "-//AUTOMYX//Calendar//ES")
        cal.add("version", "2.0")
        ICS_FILE.write_bytes(cal.to_ical())


# ---------------------------------------------------------------------------
# iCal local
# ---------------------------------------------------------------------------
def add_event(title: str, start: str, end: Optional[str] = None, *,
              description: str = "", location: str = "", all_day: bool = False,
              attendees: Optional[List[str]] = None, recurrence: Optional[str] = None) -> Dict[str, Any]:
    """Añade un evento al calendario iCal local."""
    if not ICAL_AVAILABLE:
        return {"ok": False, "error": "instala icalendar (pip install icalendar)"}
    _ensure_storage()

    try:
        start_dt = _parse_dt(start)
    except Exception as e:
        return {"ok": False, "error": f"start datetime inválido: {e}"}

    if end:
        try:
            end_dt = _parse_dt(end)
        except Exception as e:
            return {"ok": False, "error": f"end datetime inválido: {e}"}
    else:
        end_dt = start_dt + timedelta(hours=1)

    cal = Calendar.from_ical(ICS_FILE.read_bytes())
    ev = Event()
    ev.add("summary", title)
    ev.add("description", description)
    ev.add("location", location)
    ev.add("dtstart", start_dt.date() if all_day else start_dt)
    ev.add("dtend", end_dt.date() + timedelta(days=1) if all_day else end_dt)
    ev.add("uid", f"{uuid.uuid4()}@automyx")
    ev.add("dtstamp", datetime.utcnow())
    for a in attendees or []:
        ev.add("attendee", f"mailto:{a}")
    if recurrence:
        ev.add("rrule", recurrence)
    cal.add_component(ev)
    ICS_FILE.write_bytes(cal.to_ical())

    return {
        "ok": True,
        "title": title,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "uid": str(ev.get("uid")),
    }


def _parse_dt(s: str) -> datetime:
    """Parsea un datetime en formatos comunes."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # ISO format
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception as e:
        raise ValueError(f"formato no reconocido: {s}") from e


def list_events(*, days_ahead: int = 30, max_events: int = 50) -> Dict[str, Any]:
    """Lista los próximos N días de eventos."""
    if not ICAL_AVAILABLE:
        return {"ok": False, "error": "icalendar no instalado"}
    _ensure_storage()

    cal = Calendar.from_ical(ICS_FILE.read_bytes())
    now = datetime.utcnow()
    horizon = now + timedelta(days=days_ahead)
    events: List[Dict[str, Any]] = []

    for component in cal.walk("VEVENT"):
        start = component.get("dtstart").dt
        if isinstance(start, datetime):
            start_dt = start
        else:
            start_dt = datetime.combine(start, datetime.min.time())
        if start_dt < now - timedelta(days=1):
            continue
        if start_dt > horizon:
            continue
        end = component.get("dtend").dt if component.get("dtend") else None
        events.append({
            "uid": str(component.get("uid")),
            "summary": str(component.get("summary", "")),
            "description": str(component.get("description", "")),
            "location": str(component.get("location", "")),
            "start": start_dt.isoformat(),
            "end": end.isoformat() if end else None,
        })

    events.sort(key=lambda e: e["start"])
    return {"ok": True, "count": len(events), "events": events[:max_events]}


def delete_event(uid: str) -> Dict[str, Any]:
    """Elimina un evento por UID."""
    if not ICAL_AVAILABLE:
        return {"ok": False, "error": "icalendar no instalado"}
    _ensure_storage()

    cal = Calendar.from_ical(ICS_FILE.read_bytes())
    to_remove = []
    for component in cal.walk("VEVENT"):
        if str(component.get("uid")) == uid:
            to_remove.append(component)
    for c in to_remove:
        cal.subcomponent(c)
    if not to_remove:
        return {"ok": False, "error": f"evento {uid} no encontrado"}
    ICS_FILE.write_bytes(cal.to_ical())
    return {"ok": True, "deleted": len(to_remove), "uid": uid}


def find_free_slot(duration_minutes: int = 60, *, days_ahead: int = 7,
                   work_start: int = 9, work_end: int = 18) -> Dict[str, Any]:
    """Encuentra un slot libre en horario laboral."""
    if not ICAL_AVAILABLE:
        return {"ok": False, "error": "icalendar no instalado"}
    events_result = list_events(days_ahead=days_ahead, max_events=200)
    if not events_result["ok"]:
        return events_result

    # Indexar ocupados por día
    busy: Dict[str, List[tuple]] = {}
    for ev in events_result["events"]:
        try:
            s = datetime.fromisoformat(ev["start"])
            e = datetime.fromisoformat(ev["end"]) if ev["end"] else s + timedelta(hours=1)
            day = s.date().isoformat()
            busy.setdefault(day, []).append((s, e))
        except Exception:
            continue

    # Buscar slot
    for i in range(days_ahead):
        day = (datetime.utcnow() + timedelta(days=i)).date()
        if day.weekday() >= 5:  # fin de semana
            continue
        day_str = day.isoformat()
        day_busy = sorted(busy.get(day_str, []))
        for hour in range(work_start, work_end):
            slot_start = datetime.combine(day, datetime.min.time()).replace(hour=hour)
            slot_end = slot_start + timedelta(minutes=duration_minutes)
            if slot_end.hour > work_end:
                break
            conflict = any(s < slot_end and e > slot_start for s, e in day_busy)
            if not conflict:
                return {"ok": True, "start": slot_start.isoformat(), "end": slot_end.isoformat(), "day": day_str}
    return {"ok": False, "error": "no hay slots libres en los próximos días hábiles"}


# ---------------------------------------------------------------------------
# Google Calendar (stub con instrucciones)
# ---------------------------------------------------------------------------
def google_calendar_status() -> Dict[str, Any]:
    return {
        "ok": os.environ.get("GOOGLE_CALENDAR_CREDENTIALS") is not None,
        "configured": bool(os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")),
        "instructions": (
            "Para Google Calendar: 1) crea OAuth2 credentials en console.cloud.google.com, "
            "2) descarga credentials.json, 3) export GOOGLE_CALENDAR_CREDENTIALS=/ruta/creds.json"
        ),
    }


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------
class CalendarTools:
    @staticmethod
    def add(title: str, start: str, end: Optional[str] = None, description: str = "", location: str = "") -> Dict[str, Any]:
        return add_event(title, start, end=end, description=description, location=location)

    @staticmethod
    def list(days_ahead: int = 30) -> Dict[str, Any]:
        return list_events(days_ahead=days_ahead)

    @staticmethod
    def delete(uid: str) -> Dict[str, Any]:
        return delete_event(uid)

    @staticmethod
    def find_free(duration_minutes: int = 60, days_ahead: int = 7) -> Dict[str, Any]:
        return find_free_slot(duration_minutes=duration_minutes, days_ahead=days_ahead)

    @staticmethod
    def google_status() -> Dict[str, Any]:
        return google_calendar_status()
