"""Tests de escaneo de punta a punta: genera MP3 de prueba (tests/make_test_files.py),
escanea contra una base SQLite temporal, y verifica la clasificación.

Nunca toca la Biblioteca Confiable real (se monkeypatchea `biblioteca_confiable.buscar`
para que devuelva None, como si no estuviera configurada) — un test no debe
depender de la red ni de credenciales de quien lo corre.
"""
import db
import scanner
import biblioteca_confiable
import make_test_files


def test_scan_clasifica_tracks_de_prueba(tmp_path, monkeypatch):
    monkeypatch.setattr(biblioteca_confiable, "buscar", lambda *a, **k: None)

    carpeta = tmp_path / "musica"
    make_test_files.main(str(carpeta))

    conn = db.connect(str(tmp_path / "test.db"))
    resumen = scanner.scan(str(carpeta), conn)

    assert resumen["total"] == len(make_test_files.TRACKS)
    # Solo el track sin género (tag vacío) va a revisar — "Future Bass" sí
    # matchea (alias de "Bass House"), aunque el comentario del fixture en
    # make_test_files.py diga "no reconocido".
    assert resumen["por_revisar"] == 1
    assert resumen["clasificados"] == resumen["total"] - 1
    # el track de 128kbps queda marcado como baja calidad
    assert resumen["baja_calidad"] == 1

    fila = conn.execute(
        "SELECT genero, subgenero FROM tracks WHERE artista='Fisher'"
    ).fetchone()
    assert fila["genero"] == "House"
    assert fila["subgenero"] == "Tech House"

    # regresión: "Melodic Techno" (tag crudo) ya no debe clasificarse como
    # subgénero de Techno, sino como el género unificado
    fila_melodic = conn.execute(
        "SELECT genero, subgenero FROM tracks WHERE artista='Tale Of Us'"
    ).fetchone()
    assert fila_melodic["genero"] == "Melodic House & Techno"
    assert fila_melodic["subgenero"] is None

    conn.close()


def test_rescan_no_pisa_clasificacion_manual(tmp_path, monkeypatch):
    monkeypatch.setattr(biblioteca_confiable, "buscar", lambda *a, **k: None)

    carpeta = tmp_path / "musica"
    make_test_files.main(str(carpeta))
    conn = db.connect(str(tmp_path / "test.db"))
    scanner.scan(str(carpeta), conn)

    # el DJ corrige a mano el género de un track
    conn.execute(
        "UPDATE tracks SET genero='Trance', subgenero='Psy-Trance', "
        "confianza='manual' WHERE artista='Fisher'"
    )
    conn.commit()

    # un segundo escaneo no debe pisar esa corrección manual
    scanner.scan(str(carpeta), conn)
    fila = conn.execute(
        "SELECT genero, subgenero, confianza FROM tracks WHERE artista='Fisher'"
    ).fetchone()
    assert fila["genero"] == "Trance"
    assert fila["subgenero"] == "Psy-Trance"
    assert fila["confianza"] == "manual"

    conn.close()
