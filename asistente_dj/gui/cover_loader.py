"""Cargador asíncrono de carátulas (URLs remotas, ej. CDN de Apple) con
caché en memoria, compartido por todas las vistas que necesiten mostrarlas
(grilla, panel de detalle, etc.) — así cada URL se descarga una sola vez
por sesión, sin importar en cuántos lugares se use."""
from __future__ import annotations

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest


class CoverLoader(QObject):
    cargada = Signal(str)   # url ya disponible en la caché, lista para pintar

    def __init__(self):
        super().__init__()
        self._cache: dict[str, QPixmap] = {}
        self._pendientes: set[str] = set()
        self._manager = QNetworkAccessManager(self)

    def pixmap(self, url: str) -> QPixmap | None:
        """Devuelve el pixmap cacheado, o None si todavía no se descargó
        (y dispara la descarga en background si no se había pedido antes).
        Quien llama debe escuchar la señal `cargada` para repintar cuando
        esté lista."""
        if not url:
            return None
        if url in self._cache:
            return self._cache[url]
        if url not in self._pendientes:
            self._pendientes.add(url)
            self._descargar(url)
        return None

    def _descargar(self, url: str):
        resp = self._manager.get(QNetworkRequest(QUrl(url)))
        resp.finished.connect(lambda: self._on_terminado(resp, url))

    def _on_terminado(self, resp, url: str):
        self._pendientes.discard(url)
        try:
            datos = resp.readAll()
            pix = QPixmap()
            if pix.loadFromData(datos):
                self._cache[url] = pix
                self.cargada.emit(url)
        finally:
            resp.deleteLater()


_instancia: CoverLoader | None = None


def obtener() -> CoverLoader:
    global _instancia
    if _instancia is None:
        _instancia = CoverLoader()
    return _instancia
