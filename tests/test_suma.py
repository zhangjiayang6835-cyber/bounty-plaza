"""Pruebas unitarias para la función suma().
Resuelve Issue #527: La función suma() resta en vez de sumar ($50 USD).
"""

import pytest
from suma import suma


def test_suma_enteros_positivos():
    assert suma(2, 3) == 5
    assert suma(10, 20) == 30
    assert suma(0, 0) == 0


def test_suma_numeros_negativos():
    assert suma(-5, -7) == -12
    assert suma(-10, 15) == 5
    assert suma(20, -5) == 15


def test_suma_flotantes():
    assert pytest.approx(suma(2.5, 3.1), 0.0001) == 5.6
    assert pytest.approx(suma(-1.5, 0.5), 0.0001) == -1.0


def test_suma_validacion_tipos():
    with pytest.raises(TypeError):
        suma("2", 3)  # type: ignore

    with pytest.raises(TypeError):
        suma(5, [1, 2])  # type: ignore

    with pytest.raises(TypeError):
        suma(True, 4)  # type: ignore
