"""Servidor HTTP local mínimo para servir el HTML del reproductor de YouTube.

QWebEngineView.setHtml() carga el documento con un origen opaco (sin header
Referer real en las sub-peticiones), y YouTube rechaza embeber el video sin
eso (error "Este video no está disponible" / código 152, confirmado al
probarlo). Servimos el HTML desde localhost en vez de eso, así el iframe a YouTube
sale con un Referer real de http://127.0.0.1, que YouTube sí acepta —igual
que cuando cualquier sitio externo embebe un video.
"""
from __future__ import annotations

import http.server
import socketserver
import threading
import time

_state = {"html": "<html><body></body></html>"}
_server: socketserver.TCPServer | None = None
_port: int | None = None


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_state["html"].encode("utf-8"))

    def log_message(self, *_args):
        pass


def _ensure_server():
    global _server, _port
    if _server is not None:
        return
    _server = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    _port = _server.server_address[1]
    threading.Thread(target=_server.serve_forever, daemon=True).start()


def set_html(html: str) -> str:
    """Guarda `html` para que lo sirva el servidor local y devuelve la URL a
    cargar. Incluye un parámetro único para forzar que QWebEngineView no
    reutilice una navegación cacheada de una carga anterior."""
    _ensure_server()
    _state["html"] = html
    return f"http://127.0.0.1:{_port}/?t={time.time_ns()}"
