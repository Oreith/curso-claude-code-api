"""Normalización de `title` de tarea (Incremento 1 del plan de tareas).

Contrato §Normalización de texto (docs/contrato-api.md:20-31): se recorta el
espacio de los extremos y se rechaza el valor que no deja ningún carácter
visible, por categoría Unicode (`Cc`, `Cf`, `Zl`, `Zp`, `Zs`). No toca base de
datos. Los invisibles se escriben con secuencias de escape a propósito.
"""

import pytest

from app.schemas import _titulo_normalizado


def test_recorta_espacios_ascii():
    assert _titulo_normalizado("  Regar las plantas  ") == "Regar las plantas"


@pytest.mark.parametrize(
    ("valor", "categoria"),
    [
        ("", "vacío"),
        ("   ", "Zs ASCII"),
        ("  ", "Zs NO-BREAK SPACE"),
        ("​", "Cf ZERO WIDTH SPACE"),
        ("﻿", "Cf BOM"),
        ("\x00", "Cc NUL"),
        ("\t\n", "Cc tab y salto"),
        (" ", "Zl LINE SEPARATOR"),
        (" ", "Zp PARAGRAPH SEPARATOR"),
        ("​  ", "solo invisibles mezclados"),
    ],
)
def test_rechaza_sin_caracter_visible(valor, categoria):
    with pytest.raises(ValueError):
        _titulo_normalizado(valor)


def test_acepta_con_invisibles_interiores():
    # Tiene caracteres visibles: se acepta y se devuelve recortado, con los
    # invisibles interiores intactos (el contrato solo exige un visible).
    assert _titulo_normalizado("  Regar​las plantas  ") == "Regar​las plantas"


def test_acepta_invisible_al_inicio_que_strip_no_quita():
    # str.strip() no elimina U+200B (no es whitespace); queda y hay visibles.
    assert _titulo_normalizado("​Regar") == "​Regar"
