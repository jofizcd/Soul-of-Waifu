import os
import logging
import threading
import functools
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

logger = logging.getLogger("VRMServer")

class SecureVRMRequestHandler(SimpleHTTPRequestHandler):
    FORBIDDEN_PREFIXES = (
        "/app/configuration",
        "/.soul",
        "/logs",
        "/.git",
        "/.env",
        "/requirements.txt",
        "/main.py",
        "/patch.bat",
        "/start.bat",
        "/installer.bat"
    )

    ALLOWED_EXTENSIONS = (
        ".vrm", ".fbx", ".gltf", ".glb", ".js", ".html",
        ".css", ".png", ".jpg", ".jpeg", ".webp", ".json", ".wasm"
    )

    def do_GET(self):
        clean_path = self.path.split('?')[0]
        clean_path_lower = clean_path.lower()

        if any(clean_path_lower.startswith(prefix) for prefix in self.FORBIDDEN_PREFIXES):
            logger.warning(f"[VRM Server] Blocked unauthorized access: {clean_path}")
            self.send_error(403, "Access Denied")
            return

        if not any(clean_path_lower.endswith(ext) for ext in self.ALLOWED_EXTENSIONS):
            self.send_error(403, "File type not allowed")
            return

        full_path = self.translate_path(self.path)
        if os.path.isdir(full_path):
            self.send_error(403, "Directory listing disabled")
            return

        super().do_GET()

    def log_message(self, format, *args):
        pass


class VRMServerThread(threading.Thread):
    def __init__(self, preferred_port=8001):
        super().__init__()
        self.port = preferred_port
        self.daemon = True
        self.server = None
        
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

    def run(self):
        handler = functools.partial(
            SecureVRMRequestHandler,
            directory=self.project_root
        )

        ports_to_try = [self.port, 8001, 8002, 8003, 8004, 8005, 8081, 8082]

        for try_port in ports_to_try:
            try:
                TCPServer.allow_reuse_address = True
                self.server = TCPServer(("127.0.0.1", try_port), handler)
                self.port = try_port
                logger.info(f"VRM Secure HTTP server started on http://127.0.0.1:{try_port}")
                break
            except OSError:
                continue

        if self.server:
            try:
                self.server.serve_forever()
            except Exception as e:
                logger.error(f"VRM server runtime error: {e}")
        else:
            logger.error("Could not start VRM HTTP server on any available port")

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
                logger.info("VRM HTTP server stopped")
            except Exception as e:
                logger.error(f"Error stopping VRM server: {e}")