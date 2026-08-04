import os
import secrets
import asyncio
import logging
import ipaddress
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Security, Depends
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader, APIKeyQuery
from faster_whisper import WhisperModel
import uvicorn

logger = logging.getLogger("WebBridge")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict, exclude: WebSocket = None):
        disconnected = []
        for connection in self.active_connections:
            if connection == exclude:
                continue
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"WebSocket Broadcast Error: {e}")
                disconnected.append(connection)
                
        for connection in disconnected:
            self.disconnect(connection)

class WebBridge:
    def __init__(self, interface_signals, auth_token: str = None):
        self.app = FastAPI(docs_url=None, redoc_url=None)
        self.signals = interface_signals
        self.manager = ConnectionManager()
        
        self.auth_token = auth_token or secrets.token_urlsafe(16)
        logger.info(f"WebBridge Auth Token initialized: {self.auth_token}")
        
        self.app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_dir = os.path.dirname(self.app_dir)
        
        self.setup_middleware()
        self.setup_routes()
        self.hook_interface_signals()

    def hook_interface_signals(self):
        self.signals.web_bridge = self

    def setup_middleware(self):
        @self.app.middleware("http")
        async def validate_host_header(request: Request, call_next):
            host_header = (request.headers.get("host") or "").split(":")[0]
            if host_header in ("localhost", "127.0.0.1", ""):
                return await call_next(request)
            try:
                ipaddress.ip_address(host_header)
            except ValueError:
                return PlainTextResponse("Forbidden: Invalid Host Header", status_code=400)
            return await call_next(request)

        @self.app.middleware("http")
        async def check_auth_token(request: Request, call_next):
            path = request.url.path
            if path in ["/", "/favicon.ico"] or path.startswith("/static") or path.startswith("/vrm") or path.startswith("/assets"):
                return await call_next(request)

            token_header = request.headers.get("X-SOW-Token")
            token_query = request.query_params.get("token")
            
            if (token_header and secrets.compare_digest(token_header, self.auth_token)) or \
               (token_query and secrets.compare_digest(token_query, self.auth_token)):
                return await call_next(request)

            return PlainTextResponse("Unauthorized: Invalid Token", status_code=401)

    def setup_routes(self):
        web_client_dir = os.path.join(self.app_dir, "web_client")
        vrm_dir = os.path.join(self.app_dir, "utils", "emotions", "vrm")
        
        if not os.path.exists(web_client_dir):
            os.makedirs(web_client_dir, exist_ok=True)
            
        self.app.mount("/static", StaticFiles(directory=web_client_dir), name="static")
        self.app.mount("/assets", StaticFiles(directory=os.path.join(self.project_dir, "assets")), name="assets")
        
        if os.path.exists(vrm_dir):
            self.app.mount("/vrm", StaticFiles(directory=vrm_dir), name="vrm")

        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            index_path = os.path.join(web_client_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return HTMLResponse("<h1>Web Client Not Found</h1>")

        @self.app.get("/api/config")
        async def get_config():
            char_name = self.signals.current_active_character or "None"
            return {
                "active_character": char_name,
                "user_name": "User"
            }

        @self.app.get("/api/avatar_config/{char_name}")
        async def get_avatar_config(char_name: str):
            config = await asyncio.to_thread(self.signals.configuration_characters.load_configuration)
            char_info = config["character_list"].get(char_name, {})
            
            mode = char_info.get("current_sow_system_mode", "Nothing")
            img_folder = char_info.get("expression_images_folder", "")
            l2d_folder = char_info.get("live2d_model_folder", "")
            vrm_file = char_info.get("vrm_model_file", "")
            
            if img_folder: img_folder = "/" + os.path.relpath(img_folder, self.project_dir).replace("\\", "/")
            if l2d_folder:
                for file in os.listdir(l2d_folder):
                    if file.endswith(".model3.json") or file.endswith(".model.json"):
                        l2d_folder = "/" + os.path.relpath(os.path.join(l2d_folder, file), self.project_dir).replace("\\", "/")
                        break
            if vrm_file: vrm_file = "/" + os.path.relpath(vrm_file, self.project_dir).replace("\\", "/")

            return {
                "mode": mode,
                "expression_images_folder": img_folder,
                "live2d_model_file": l2d_folder,
                "vrm_model_file": vrm_file
            }

        @self.app.get("/api/characters")
        async def get_characters():
            config = await asyncio.to_thread(self.signals.configuration_characters.load_configuration)
            chars = list(config.get("character_list", {}).keys())
            return {"characters": chars}

        @self.app.post("/api/character/switch")
        async def switch_character(request: Request):
            data = await request.json()
            char_name = data.get("character")
            if char_name:
                asyncio.create_task(self.signals.open_chat(char_name))
                await self.manager.broadcast({
                    "type": "character_changed",
                    "character": char_name
                })
                return {"status": "ok"}
            return {"status": "error"}

        @self.app.get("/api/background")
        async def get_background():
            bg_path = await asyncio.to_thread(self.signals.configuration_settings.get_main_setting, "chat_background_image")
            if bg_path and bg_path != "None" and os.path.exists(bg_path):
                return FileResponse(bg_path)
            return HTMLResponse("No background", status_code=404)

        @self.app.get("/api/history/{char_name}")
        async def get_history(char_name: str, offset: int = 0, limit: int = 50):
            config = await asyncio.to_thread(self.signals.configuration_characters.load_configuration)
            char_info = config["character_list"].get(char_name, {})
            current_chat = char_info.get("current_chat", "default")
            chat_content = char_info.get("chats", {}).get(current_chat, {}).get("chat_content", {})
            
            user_name = self.signals.configuration_settings.get_user_data("user_name") or "User"
            
            messages = []
            for msg_id, msg_data in sorted(chat_content.items(), key=lambda x: x[1].get("sequence_number", 0)):
                current_variant_id = msg_data.get("current_variant_id", "default")
                text = next(
                    (v["text"] for v in msg_data.get("variants", []) if v["variant_id"] == current_variant_id),
                    ""
                )
                
                processed_text = (text.replace("{{user}}", user_name)
                                      .replace("{{char}}", char_name)
                                      .replace("{{User}}", user_name)
                                      .replace("{{Char}}", char_name)
                                      .replace("<USER>", user_name)
                                      .replace("<CHAR>", char_name))
                
                messages.append({
                    "id": msg_id,
                    "is_user": msg_data.get("is_user", True),
                    "text": processed_text
                })
            
            if messages:
                total = len(messages)
                start_idx = max(0, total - offset - limit)
                end_idx = total - offset
                history_slice = messages[start_idx:end_idx]
            else:
                history_slice = []
                
            return {"history": history_slice}

        @self.app.delete("/api/messages/{message_id}")
        async def delete_message_api(message_id: str, request: Request):
            data = await request.json()
            char_name = data.get("character")
            
            config = await asyncio.to_thread(self.signals.configuration_characters.load_configuration)
            char_info = config["character_list"].get(char_name, {})
            conv_method = char_info.get("conversation_method", "Local LLM")
            
            asyncio.create_task(self.signals.delete_message(char_name, conv_method, message_id))
            
            await self.manager.broadcast({"type": "message_deleted", "id": message_id})
            return {"status": "ok"}

        @self.app.patch("/api/messages/{message_id}")
        async def edit_message_api(message_id: str, request: Request):
            data = await request.json()
            char_name = data.get("character")
            new_text = data.get("text")
            
            config = await asyncio.to_thread(self.signals.configuration_characters.load_configuration)
            char_info = config.get("character_list", {}).get(char_name, {})
            current_chat = char_info.get("current_chat", "default")
            chats = char_info.get("chats", {})
            
            updated_on_disk = False
            if current_chat in chats:
                chat_content = chats[current_chat].get("chat_content", {})
                if message_id in chat_content:
                    msg_data = chat_content[message_id]
                    current_variant_id = msg_data.get("current_variant_id", "default")
                    
                    for variant in msg_data.get("variants", []):
                        if variant["variant_id"] == current_variant_id:
                            variant["text"] = new_text
                            updated_on_disk = True
                            break
            
            if updated_on_disk:
                await asyncio.to_thread(self.signals.configuration_characters.save_configuration, config)
                
                if message_id in self.signals.messages:
                    processed_text = self.signals.markdown_to_html(new_text)
                    user_name = self.signals.configuration_settings.get_user_data("user_name") or "User"
                    processed_text = (processed_text.replace("{{user}}", user_name)
                                .replace("{{char}}", char_name)
                                .replace("{{User}}", user_name)
                                .replace("{{Char}}", char_name))
                    
                    self.signals.messages[message_id]["label"].setText(processed_text)
                    self.signals.messages[message_id]["text"] = new_text
                
                await self.manager.broadcast({"type": "message_edited", "id": message_id, "text": new_text})
                return {"status": "ok"}
                
            return {"status": "error", "message": "Message not found in database"}

        @self.app.post("/api/messages/{message_id}/regenerate")
        async def regenerate_message_api(message_id: str, request: Request):
            data = await request.json()
            char_name = data.get("character")
            
            config = await asyncio.to_thread(self.signals.configuration_characters.load_configuration)
            char_info = config["character_list"].get(char_name, {})
            conv_method = char_info.get("conversation_method", "Local LLM")
            
            asyncio.create_task(self.signals.regenerate_message(conv_method, char_name, message_id))
            return {"status": "ok"}

        @self.app.post("/api/generation/stop")
        async def stop_generation_api():
            self.signals.stop_generation()
            return {"status": "ok"}

        @self.app.post("/api/voice/stt")
        async def stt_api(request: Request):
            form = await request.form()
            audio_file = form.get("audio")
            char_name = form.get("character")
            
            if not audio_file or not char_name:
                return {"status": "error", "message": "Missing audio or character"}

            audio_bytes = await audio_file.read()
            temp_path = os.path.join(self.app_dir, "cache", f"web_stt_{os.getpid()}.webm")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)
                
            config = await asyncio.to_thread(self.signals.configuration_characters.load_configuration)
            char_info = config["character_list"].get(char_name, {})
            conv_method = char_info.get("conversation_method", "Local LLM")

            def _transcribe():
                if not hasattr(self, "_whisper_model"):
                    self._whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
                
                segments, info = self._whisper_model.transcribe(temp_path, beam_size=5)
                full_text = "".join([segment.text for segment in segments])
                return full_text.strip()

            try:
                text = await asyncio.to_thread(_transcribe)
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"Web STT Error: {e}")
                return {"status": "error", "message": str(e)}

            if text and len(text) > 2:
                self.signals.textEdit_write_user_message.setPlainText(text)
                
                await self.manager.broadcast({
                    "type": "user_message",
                    "text": text
                })
                
                asyncio.create_task(
                    self.signals.handle_user_message(char_name, conv_method)
                )
                
            return {"status": "ok", "text": text}

        @self.app.get("/api/avatar/{char_name}")
        async def get_avatar(char_name: str):
            config = await asyncio.to_thread(self.signals.configuration_characters.load_configuration)
            char_info = config["character_list"].get(char_name, {})
            path = char_info.get("character_avatar")
            if path and os.path.exists(path):
                return FileResponse(path)
            
            fallback_path = os.path.join(self.app_dir, "gui", "icons", "logotype.png")
            if os.path.exists(fallback_path):
                return FileResponse(fallback_path)
            return HTMLResponse("Avatar not found", status_code=404)

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            token = websocket.query_params.get("token")
            if not token or not secrets.compare_digest(token, self.auth_token):
                await websocket.close(code=1008)
                return

            await self.manager.connect(websocket)
            try:
                while True:
                    data = await websocket.receive_json()
                    if data.get("type") == "user_input":
                        char_name = data.get("character")
                        text = data.get("text")
                        
                        if text and char_name:
                            self.signals.textEdit_write_user_message.setPlainText(text)
                            
                            config = await asyncio.to_thread(self.signals.configuration_characters.load_configuration)
                            char_info = config["character_list"].get(char_name, {})
                            conv_method = char_info.get("conversation_method", "Local LLM")
                            
                            await self.manager.broadcast({
                                "type": "user_message",
                                "text": text
                            }, exclude=websocket)
                            
                            asyncio.create_task(
                                self.signals.handle_user_message(char_name, conv_method)
                            )

            except WebSocketDisconnect:
                self.manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket Error: {e}")
                self.manager.disconnect(websocket)

    async def broadcast_chunk(self, chunk: str):
        await self.manager.broadcast({"type": "chunk", "text": chunk})
        
    async def broadcast_message_start(self):
        await self.manager.broadcast({"type": "message_start"})
        
    async def broadcast_message_end(self):
        await self.manager.broadcast({"type": "message_end"})

    async def broadcast_character_change(self, new_char: str):
        await self.manager.broadcast({"type": "character_changed", "character": new_char})

    async def broadcast_audio(self, b64_audio: str):
        await self.manager.broadcast({"type": "audio", "data": b64_audio})

async def run_web_server(interface_signals, host="127.0.0.1", port=8000, auth_token=None):
    bridge = WebBridge(interface_signals, auth_token=auth_token)
    config = uvicorn.Config(bridge.app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
