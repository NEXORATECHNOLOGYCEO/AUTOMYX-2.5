"""
Livestream Tools - Director Técnico de Transmisión
Controla OBS Studio vía obs-websocket v5, multistream RTMP, overlays dinámicos y moderación IA del chat.
"""
import os
import json
import time
import socket
import hashlib
import base64
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    import websocket  # websocket-client
except ImportError:
    websocket = None

try:
    import requests
except ImportError:
    requests = None


class LivestreamTools:
    """Director de streaming profesional con OBS-WebSocket v5."""

    _obs_ws = None
    _obs_password = None
    _moderation_rules: List[str] = []
    PRESETS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state", "livestream_presets.json")

    # ---------- OBS CONNECTION (WebSocket v5) ----------
    @staticmethod
    def obs_connect(host: str = "localhost", port: int = 4455, password: str = "") -> Dict[str, Any]:
        """Conecta a OBS Studio vía obs-websocket v5."""
        if websocket is None:
            return {"error": "Falta instalar websocket-client (pip install websocket-client)"}
        try:
            ws = websocket.create_connection(f"ws://{host}:{port}", timeout=10)
            hello = json.loads(ws.recv())
            auth = ""
            if "authentication" in hello.get("d", {}):
                if not password:
                    ws.close()
                    return {"error": "OBS requiere password pero no se proporcionó"}
                challenge = hello["d"]["authentication"]["challenge"]
                salt = hello["d"]["authentication"]["salt"]
                secret = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
                auth = base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()
            identify = {"op": 1, "d": {"rpcVersion": 1, "authentication": auth}}
            ws.send(json.dumps(identify))
            ws.recv()  # identified
            LivestreamTools._obs_ws = ws
            LivestreamTools._obs_password = password
            return {"connected": True, "host": host, "port": port}
        except Exception as e:
            return {"error": f"No se pudo conectar a OBS: {e}"}

    @staticmethod
    def _obs_request(request_type: str, request_data: Dict = None) -> Dict[str, Any]:
        ws = LivestreamTools._obs_ws
        if not ws:
            return {"error": "OBS no conectado. Usa livestream_obs_connect primero."}
        try:
            req_id = hashlib.md5(f"{request_type}{time.time()}".encode()).hexdigest()[:12]
            msg = {"op": 6, "d": {"requestType": request_type, "requestId": req_id, "requestData": request_data or {}}}
            ws.send(json.dumps(msg))
            resp = json.loads(ws.recv())
            return resp.get("d", {}).get("responseData", {"status": "ok"})
        except Exception as e:
            return {"error": f"Error OBS '{request_type}': {e}"}

    @staticmethod
    def obs_start_stream() -> Dict[str, Any]:
        return LivestreamTools._obs_request("StartStream")

    @staticmethod
    def obs_stop_stream() -> Dict[str, Any]:
        return LivestreamTools._obs_request("StopStream")

    @staticmethod
    def obs_start_recording() -> Dict[str, Any]:
        return LivestreamTools._obs_request("StartRecord")

    @staticmethod
    def obs_stop_recording() -> Dict[str, Any]:
        return LivestreamTools._obs_request("StopRecord")

    @staticmethod
    def obs_switch_scene(scene_name: str) -> Dict[str, Any]:
        return LivestreamTools._obs_request("SetCurrentProgramScene", {"sceneName": scene_name})

    @staticmethod
    def obs_get_scenes() -> Dict[str, Any]:
        return LivestreamTools._obs_request("GetSceneList")

    @staticmethod
    def obs_toggle_source(scene_name: str, source_name: str, visible: bool) -> Dict[str, Any]:
        # Necesita primero obtener el sceneItemId
        items = LivestreamTools._obs_request("GetSceneItemList", {"sceneName": scene_name})
        for item in items.get("sceneItems", []):
            if item.get("sourceName") == source_name:
                return LivestreamTools._obs_request("SetSceneItemEnabled", {
                    "sceneName": scene_name,
                    "sceneItemId": item["sceneItemId"],
                    "sceneItemEnabled": visible,
                })
        return {"error": f"Source '{source_name}' no encontrado en escena '{scene_name}'"}

    @staticmethod
    def obs_set_source_text(source_name: str, text: str) -> Dict[str, Any]:
        return LivestreamTools._obs_request("SetInputSettings", {
            "inputName": source_name,
            "inputSettings": {"text": text},
        })

    @staticmethod
    def obs_set_bitrate(bitrate_kbps: int) -> Dict[str, Any]:
        return LivestreamTools._obs_request("SetStreamServiceSettings", {
            "streamServiceType": "rtmp_custom",
            "streamServiceSettings": {"bitrate": bitrate_kbps},
        })

    @staticmethod
    def obs_get_status() -> Dict[str, Any]:
        stream = LivestreamTools._obs_request("GetStreamStatus")
        stats = LivestreamTools._obs_request("GetStats")
        return {"stream": stream, "stats": stats}

    # ---------- MULTISTREAM ----------
    @staticmethod
    def setup_multistream(platforms: List[Dict[str, str]], primary_rtmp: str = "rtmp://localhost/live") -> Dict[str, Any]:
        """Configura multistream local con nginx-rtmp.
        platforms = [{"name": "youtube", "rtmp": "rtmp://a.rtmp.youtube.com/live2/STREAM_KEY"}, ...]"""
        nginx_conf = ["rtmp {", "  server {", "    listen 1935;", "    application live {",
                      "      live on;"]
        for p in platforms:
            nginx_conf.append(f"      push {p.get('rtmp')};  # {p.get('name')}")
        nginx_conf += ["    }", "  }", "}"]
        config_str = "\n".join(nginx_conf)
        out_path = os.path.join(os.path.dirname(LivestreamTools.PRESETS_FILE), "nginx_rtmp.conf")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(config_str)
        return {
            "config_path": out_path,
            "platforms": [p.get("name") for p in platforms],
            "instruction": f"Reemplaza nginx.conf con este archivo y reinicia nginx. Apunta OBS a {primary_rtmp}.",
        }

    @staticmethod
    def get_stream_health() -> Dict[str, Any]:
        status = LivestreamTools.obs_get_status()
        stream = status.get("stream", {})
        stats = status.get("stats", {})
        return {
            "streaming": stream.get("outputActive", False),
            "duration_ms": stream.get("outputDuration", 0),
            "bytes_sent": stream.get("outputBytes", 0),
            "skipped_frames": stream.get("outputSkippedFrames", 0),
            "total_frames": stream.get("outputTotalFrames", 0),
            "cpu_usage": stats.get("cpuUsage", 0),
            "memory_usage": stats.get("memoryUsage", 0),
        }

    # ---------- OVERLAYS ----------
    @staticmethod
    def create_alert_overlay(alert_type: str, message: str, output_path: str = None) -> Dict[str, Any]:
        """Genera un HTML para Browser Source de OBS con animación."""
        color_map = {"donation": "#00f0ff", "subscriber": "#ff00aa", "raid": "#ffaa00", "follow": "#00ff66"}
        color = color_map.get(alert_type, "#ffffff")
        html = f"""<!DOCTYPE html><html><head><style>
body{{margin:0;background:transparent;font-family:'Rajdhani',sans-serif;}}
.alert{{position:fixed;top:40%;left:50%;transform:translate(-50%,-50%);
  padding:30px 60px;background:linear-gradient(135deg,#000,{color});
  color:#fff;border-radius:20px;font-size:42px;font-weight:bold;
  box-shadow:0 0 60px {color};animation:pop 0.5s ease,fade 6s 1s forwards;}}
@keyframes pop{{from{{transform:translate(-50%,-50%) scale(0)}}to{{transform:translate(-50%,-50%) scale(1)}}}}
@keyframes fade{{to{{opacity:0;transform:translate(-50%,-50%) scale(1.2)}}}}
</style></head><body><div class="alert">{message}</div></body></html>"""
        out = output_path or os.path.join(os.path.expanduser("~"), "Downloads", f"alert_{alert_type}.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        return {"path": out, "alert_type": alert_type, "instruction": f"Añade Browser Source en OBS apuntando a file:///{out}"}

    @staticmethod
    def update_ticker(scene_name: str, source_name: str, text: str) -> Dict[str, Any]:
        return LivestreamTools.obs_set_source_text(source_name, text)

    # ---------- CHAT MODERATION ----------
    @staticmethod
    def set_moderation_rules(rules: List[str]) -> Dict[str, Any]:
        LivestreamTools._moderation_rules = [r.lower() for r in rules]
        return {"rules_count": len(rules), "rules": rules}

    @staticmethod
    def moderate_chat(message: str, username: str = "", strict: bool = False) -> Dict[str, Any]:
        msg_low = message.lower()
        score = 0.0
        reasons = []
        toxic_words = ["idiota", "estúpido", "puta", "mierda", "kill yourself", "kys"] + LivestreamTools._moderation_rules
        for w in toxic_words:
            if w in msg_low:
                score += 0.4
                reasons.append(f"palabra prohibida: '{w}'")
        if msg_low.count("http") > 1:
            score += 0.3
            reasons.append("múltiples links (spam)")
        if len(message) > 200:
            score += 0.2
            reasons.append("mensaje muy largo")
        if msg_low == msg_low.upper() and len(message) > 10:
            score += 0.15
            reasons.append("todo en mayúsculas")

        action = "allow"
        if score >= 0.6 or (strict and score >= 0.4):
            action = "delete"
        if score >= 0.9:
            action = "timeout"
        return {
            "username": username,
            "message": message[:100],
            "score": min(round(score, 2), 1.0),
            "reasons": reasons,
            "action": action,
        }

    # ---------- PRESETS ----------
    @staticmethod
    def save_preset(preset_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(LivestreamTools.PRESETS_FILE), exist_ok=True)
        presets = {}
        if os.path.exists(LivestreamTools.PRESETS_FILE):
            with open(LivestreamTools.PRESETS_FILE, "r", encoding="utf-8") as f:
                presets = json.load(f)
        presets[preset_name] = config
        with open(LivestreamTools.PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
        return {"saved": preset_name, "total_presets": len(presets)}

    @staticmethod
    def load_preset(preset_name: str) -> Dict[str, Any]:
        if not os.path.exists(LivestreamTools.PRESETS_FILE):
            return {"error": "No hay presets guardados"}
        with open(LivestreamTools.PRESETS_FILE, "r", encoding="utf-8") as f:
            presets = json.load(f)
        if preset_name not in presets:
            return {"error": f"Preset '{preset_name}' no encontrado. Disponibles: {list(presets.keys())}"}
        return presets[preset_name]

    @staticmethod
    def schedule_scene(scene_name: str, delay_seconds: int) -> Dict[str, Any]:
        def _run():
            time.sleep(delay_seconds)
            LivestreamTools.obs_switch_scene(scene_name)
        threading.Thread(target=_run, daemon=True).start()
        return {"scheduled": scene_name, "in_seconds": delay_seconds}
