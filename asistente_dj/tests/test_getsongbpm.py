"""Tests de las funciones puras de getsongbpm.py (sin red)."""
from getsongbpm import key_a_camelot, limpiar_artista, limpiar_titulo


def test_key_a_camelot_mayor():
    assert key_a_camelot("C") == "8B"
    assert key_a_camelot("G") == "9B"


def test_key_a_camelot_menor():
    assert key_a_camelot("Am") == "8A"
    assert key_a_camelot("Gm") == "6A"


def test_key_a_camelot_con_sostenido():
    assert key_a_camelot("F#m") == "11A"


def test_key_a_camelot_con_simbolo_unicode():
    # ♭/♯ deben normalizarse igual que b/#
    assert key_a_camelot("D♭") == key_a_camelot("Db")


def test_key_a_camelot_vacio():
    assert key_a_camelot("") == ""
    assert key_a_camelot(None) == ""


def test_limpiar_titulo_quita_numero_de_pista():
    assert limpiar_titulo("03 - Nova") == "Nova"


def test_limpiar_titulo_quita_feat():
    assert limpiar_titulo("Nova feat. Alguien") == "Nova"


def test_limpiar_titulo_quita_sufijo_de_mix():
    assert limpiar_titulo("Nova - Extended Mix") == "Nova"


def test_limpiar_artista_se_queda_con_el_primero():
    assert limpiar_artista("Tale Of Us feat. Mathame") == "Tale Of Us"
    assert limpiar_artista("Tale Of Us, Mathame") == "Tale Of Us"
    assert limpiar_artista("Tale Of Us vs. Mathame") == "Tale Of Us"
