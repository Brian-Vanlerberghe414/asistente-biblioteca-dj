"""Tests del clasificador de género (tag crudo -> árbol de géneros)."""
from classifier import classify
from config import GENRE_TREE


def test_alias_exacto():
    r = classify("Tech House")
    assert r.genero == "House"
    assert r.subgenero == "Tech House"
    assert r.confianza == "exacta"


def test_alias_parcial():
    # "Tech House (Extended Mix)" no es un alias exacto, pero contiene uno
    r = classify("Tech House (Extended Mix)")
    assert r.genero == "House"
    assert r.subgenero == "Tech House"
    assert r.confianza == "parcial"


def test_genero_no_reconocido_va_a_revisar():
    r = classify("zzxxqqwwvvbbnnmm1234")
    assert r.genero is None
    assert r.confianza == "ninguna"


def test_sin_tag():
    r = classify("")
    assert r.genero is None
    assert r.confianza == "ninguna"


def test_melodic_house_y_melodic_techno_se_unifican():
    """Regresión: "Melodic House" y "Melodic Techno" se fusionaron en
    "Melodic House & Techno" (sesión 2026-06-22) — no deben volver a
    clasificarse como subgénero de House/Techno."""
    for tag in ("Melodic Techno", "Melodic House", "melodic", "Melodic Progressive"):
        r = classify(tag)
        assert r.genero == "Melodic House & Techno", f"falló para {tag!r}"
        assert r.subgenero is None, f"falló para {tag!r}"


def test_carpeta_relativa_incluye_subgenero():
    r = classify("Deep House")
    assert r.carpeta_relativa == "House/Deep House"


def test_carpeta_relativa_sin_subgenero():
    r = classify("Melodic House & Techno")
    assert r.carpeta_relativa == "Melodic House & Techno"


def test_resultado_de_classify_siempre_es_consistente_con_el_arbol():
    """Cualquier (genero, subgenero) que devuelva classify() para un tag
    reconocido tiene que existir de verdad en GENRE_TREE — si no, hay un
    alias roto en config.GENRE_ALIASES."""
    from config import GENRE_ALIASES

    for alias, (genero, sub) in GENRE_ALIASES.items():
        r = classify(alias)
        assert r.genero == genero, f"alias {alias!r} no resolvió al género esperado"
        if genero is not None:
            assert genero in GENRE_TREE, f"{genero!r} (de alias {alias!r}) no está en GENRE_TREE"
        if sub is not None:
            assert sub in GENRE_TREE[genero], (
                f"subgénero {sub!r} (de alias {alias!r}) no está en "
                f"GENRE_TREE[{genero!r}] — ¿quedó un alias viejo tras una "
                f"reorganización del árbol?"
            )
