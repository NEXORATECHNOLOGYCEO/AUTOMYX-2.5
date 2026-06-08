"""
Gateway Profesional para Automyx
Inspirado en la arquitectura de OpenClaw
- WebSocket para control en tiempo real
- Health checks
- Autenticación segura
- Manejo de sesiones
"""
import asyncio
import json
import time
from typing import Dict, Any, List
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn
from colorama import Fore, Style

from fastapi.middleware.cors import CORSMiddleware
from core.config import config
from core.banner import print_automyx_banner


class GatewayMessage(BaseModel):
    """Estructura de mensajes para el Gateway"""
    type: str  # req, res, event
    id: str = None
    method: str = None
    params: Dict[str, Any] = None
    ok: bool = None
    payload: Dict[str, Any] = None
    error: str = None
    event: str = None


class Session:
    """Manejo de sesiones por usuario/remitente"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.history = []
        self.last_active = datetime.now()


class ConnectionManager:
    """Gestor de conexiones WebSocket"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.sessions: Dict[str, Session] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass
    
    def get_or_create_session(self, session_id: str) -> Session:
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(session_id)
        session = self.sessions[session_id]
        session.last_active = datetime.now()
        return session


class AutomyxGateway:
    """Gateway principal de Automyx"""
    
    def __init__(self, app: FastAPI, agent):
        self.app = app
        self.agent = agent
        self.manager = ConnectionManager()
        self.start_time = time.time()
        self._setup_routes()
    
    def _setup_routes(self):
        """Configura todas las rutas del Gateway"""
        
        @self.app.get("/health")
        async def health_check():
            """Endpoint de health check"""
            return {
                "status": "ok",
                "uptime": time.time() - self.start_time,
                "version": config.get("version"),
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/api/gateway/status")
        async def gateway_status():
            """Estado del Gateway"""
            return {
                "status": "online",
                "uptime": time.time() - self.start_time,
                "connections": len(self.manager.active_connections),
                "sessions": len(self.manager.sessions),
                "config": {
                    "host": config.get("gateway.host"),
                    "port": config.get("gateway.port"),
                    "auth_mode": config.get("gateway.auth.mode")
                }
            }

        @self.app.get("/api/agent/status")
        async def agent_status():
            """Estado en tiempo real del agente (para frontend)"""
            from core.agent import agent_status
            return agent_status

        @self.app.get("/api/multitask/stats")
        async def multitask_stats():
            try:
                from core.multi_task import get_dispatcher
                d = get_dispatcher()
                return d.stats()
            except Exception:
                return {"total": 0, "active": 0, "max_workers": 0, "by_status": {}}

        @self.app.get("/api/multitask/list")
        async def multitask_list():
            try:
                from core.multi_task import get_dispatcher
                d = get_dispatcher()
                return {"tasks": d.list_tasks()}
            except Exception:
                return {"tasks": []}

        @self.app.post("/api/multitask/submit")
        async def multitask_submit(data: dict):
            try:
                prompt = data.get("prompt", "")
                agent_id = data.get("agent_id", "main")
                if not prompt:
                    return {"ok": False, "detail": "No prompt provided"}
                from core.multi_task import get_dispatcher
                d = get_dispatcher()
                task = d.submit(prompt, agent=self.agent, agent_id=agent_id)
                return {"ok": True, "task_id": task.task_id}
            except Exception as e:
                return {"ok": False, "detail": str(e)}

        @self.app.delete("/api/multitask/task/{task_id}")
        async def multitask_cancel(task_id: str):
            try:
                from core.multi_task import get_dispatcher
                d = get_dispatcher()
                d.cancel(task_id)
                return {"ok": True, "task_id": task_id}
            except Exception:
                return {"ok": False}

        @self.app.get("/api/skills/catalog")
        async def skills_catalog():
            try:
                from core.intent_engine import SKILLS_CATALOG, count_skills, count_tools_in_catalog
                return {
                    "total_skills": count_skills(),
                    "total_tools_in_catalog": count_tools_in_catalog(),
                    "categories": SKILLS_CATALOG,
                }
            except Exception as e:
                return {"error": str(e), "total_skills": 0, "total_tools_in_catalog": 0, "categories": {}}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket, token: str = None):
            """Endpoint WebSocket principal"""
            
            # Verificar autenticación
            auth_mode = config.get("gateway.auth.mode")
            if auth_mode == "token":
                expected_token = config.get_gateway_token()
                if token != expected_token:
                    await websocket.close(code=1008, reason="Token inválido")
                    return
            
            await self.manager.connect(websocket)

            # Registrar listener de multi-task para esta conexion
            _mt_listener_cb = None
            _mt_session_id = None
            try:
                from core.multi_task import get_dispatcher
                _mt_dispatcher = get_dispatcher()
                _mt_session_id = f"ws_{id(websocket)}_{time.time()}"
                def _mt_progress_listener(payload):
                    """Envia progreso de multi-task por WebSocket (payload es dict)."""
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.manager.send_personal_message({
                                "type": "event",
                                "event": "multitask_progress",
                                "payload": {
                                    "task_id": payload.get("task_id", ""),
                                    "status": payload.get("status", ""),
                                    "phase": payload.get("phase", ""),
                                    "action": payload.get("action", ""),
                                    "progress": payload.get("progress", 0),
                                    "result_preview": payload.get("result_preview", ""),
                                }
                            }, websocket),
                            asyncio.get_event_loop()
                        )
                    except Exception:
                        pass
                _mt_listener_cb = _mt_progress_listener
                _mt_dispatcher.add_session_listener(_mt_session_id, _mt_listener_cb)
            except Exception:
                pass

            try:
                # Enviar mensaje de bienvenida
                await self.manager.send_personal_message({
                    "type": "event",
                    "event": "hello",
                    "payload": {
                        "version": config.get("version"),
                        "gateway": "Automyx",
                        "status": "connected"
                    }
                }, websocket)
                
                # Enviar estado inicial
                await self._send_presence(websocket)
                
                # Loop de mensajes
                while True:
                    data = await websocket.receive_json()
                    await self._handle_message(data, websocket)
            
            except WebSocketDisconnect:
                self.manager.disconnect(websocket)
            except Exception as e:
                print(f"[GATEWAY] Error en WebSocket: {e}")
                self.manager.disconnect(websocket)
            finally:
                # Limpiar listener de multi-task
                if _mt_session_id and _mt_listener_cb:
                    try:
                        from core.multi_task import get_dispatcher
                        get_dispatcher().remove_session_listener(_mt_session_id, _mt_listener_cb)
                    except Exception:
                        pass
    
    async def _handle_message(self, data: dict, websocket: WebSocket):
        """Maneja mensajes entrantes del WebSocket"""
        try:
            msg_type = data.get("type")
            msg_id = data.get("id")
            
            if msg_type == "req":
                method = data.get("method")
                params = data.get("params", {})
                await self._handle_request(msg_id, method, params, websocket)
        
        except Exception as e:
            error_msg = {
                "type": "res",
                "id": data.get("id"),
                "ok": False,
                "error": str(e)
            }
            await self.manager.send_personal_message(error_msg, websocket)
    
    async def _handle_request(self, msg_id: str, method: str, params: dict, websocket: WebSocket):
        """Maneja solicitudes (req)"""
        
        response = {"type": "res", "id": msg_id}
        
        try:
            if method == "health":
                response["ok"] = True
                response["payload"] = {
                    "status": "ok",
                    "uptime": time.time() - self.start_time
                }
            
            elif method == "status":
                response["ok"] = True
                response["payload"] = {
                    "agent_active": self.agent is not None,
                    "sessions": len(self.manager.sessions)
                }
            
            elif method == "agent":
                # Ejecutar agente SIN bloquear el WebSocket
                user_input = params.get("message", "")
                session_id = params.get("session_id", "default")
                
                response["ok"] = True
                response["payload"] = {
                    "status": "accepted",
                    "run_id": msg_id
                }
                await self.manager.send_personal_message(response, websocket)
                
                # Ejecutar en executor para no bloquear el loop de WebSocket
                loop = asyncio.get_event_loop()
                
                # Crear progress_callback que envía updates vía WebSocket
                async def _send_progress(phase, msg, **kw):
                    try:
                        await self.manager.send_personal_message({
                            "type": "event",
                            "event": "agent_progress",
                            "payload": {
                                "run_id": msg_id,
                                "phase": phase,
                                "message": msg,
                                "step": kw.get("step"),
                                "tool_name": kw.get("tool_name"),
                                "plan": kw.get("plan"),
                            }
                        }, websocket)
                    except Exception:
                        pass
                
                def _progress_callback(phase, msg, **kw):
                    """Callback síncrono que programa el envío asíncrono."""
                    try:
                        asyncio.run_coroutine_threadsafe(
                            _send_progress(phase, msg, **kw), loop
                        )
                    except Exception:
                        pass
                
                try:
                    result = await loop.run_in_executor(
                        None,
                        lambda: self.agent.run(user_input, progress_callback=_progress_callback, max_iterations=15)
                    )
                    await self.manager.send_personal_message({
                        "type": "event",
                        "event": "agent",
                        "payload": {
                            "run_id": msg_id,
                            "status": "completed",
                            "content": result
                        }
                    }, websocket)
                except Exception as e:
                    await self.manager.send_personal_message({
                        "type": "event",
                        "event": "agent",
                        "payload": {
                            "run_id": msg_id,
                            "status": "error",
                            "error": str(e)
                        }
                    }, websocket)
            
            elif method == "send":
                # Enviar mensaje a canal
                channel = params.get("channel", "webchat")
                message = params.get("message", "")
                response["ok"] = True
                response["payload"] = {"status": "sent", "channel": channel}

            elif method == "intent":
                # Detectar intent sin ejecutar el agente
                text = params.get("text", "")
                try:
                    from core.intent_engine import understand
                    u = understand(text)
                    response["ok"] = True
                    response["payload"] = {
                        "intent": u.get("intent"),
                        "confidence": u.get("intent_confidence", 0.0),
                        "matched_keyword": u.get("matched_keyword"),
                    }
                except Exception as e:
                    response["ok"] = False
                    response["error"] = str(e)

            elif method == "ping":
                response["ok"] = True
                response["payload"] = {"pong": True, "ts": time.time()}
            
            else:
                response["ok"] = False
                response["error"] = f"Método desconocido: {method}"
            
            if method != "agent":  # agent ya envió respuesta
                await self.manager.send_personal_message(response, websocket)
        
        except Exception as e:
            response["ok"] = False
            response["error"] = str(e)
            await self.manager.send_personal_message(response, websocket)
    
    async def _send_presence(self, websocket: WebSocket):
        """Envía estado de presencia"""
        await self.manager.send_personal_message({
            "type": "event",
            "event": "presence",
            "payload": {
                "status": "online",
                "timestamp": datetime.now().isoformat()
            }
        }, websocket)
    
    async def emit_event(self, event_name: str, payload: dict):
        """Emite un evento a todos los clientes conectados"""
        await self.manager.broadcast({
            "type": "event",
            "event": event_name,
            "payload": payload
        })
    
    def start(self, host: str = None, port: int = None):
        """Inicia el servidor Gateway"""
        host = host or config.get("gateway.host")
        port = port or config.get("gateway.port")
        
        # Imprimir banner oficial de Automyx
        print_automyx_banner(model_name=self.agent.model_name if hasattr(self.agent, 'model_name') else "nvidia/gpt-oss-120b")
        
        print(f"\n{Fore.CYAN}🌐 Panel de control: http://{host}:{port}/")
        print(f"{Fore.CYAN}🔗 WebSocket: ws://{host}:{port}/ws")
        print(f"{Fore.YELLOW}🔑 Token: {config.get_gateway_token()}{Style.RESET_ALL}\n")
        
        uvicorn.run(self.app, host=host, port=port, log_level="info")


def create_gateway_app(agent):
    """Crea una instancia de la app FastAPI con Gateway"""
    app = FastAPI(title="Automyx Gateway")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    gateway = AutomyxGateway(app, agent)
    return app, gateway
