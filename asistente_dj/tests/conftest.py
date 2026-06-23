"""Config compartida de pytest: agrega asistente_dj/ al sys.path para poder
importar los módulos del proyecto (classifier, config, db, etc.) directo,
sin necesidad de instalar el proyecto como paquete."""
import os
import sys

_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)
