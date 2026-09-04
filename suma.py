"""Módulo de suma aritmética.
Resuelve Issue #527: La función suma() resta en vez de sumar ($50 USD).
Fuente original: demetriodiazdeleon-pixel/morriganprueba#1
"""

from typing import Union

Number = Union[int, float]


def suma(a: Number, b: Number) -> Number:
    """Devuelve la suma aritmética de a y b.

    Args:
        a: Primer número (int o float).
        b: Segundo número (int o float).

    Returns:
        Number: El resultado de a + b.

    Raises:
        TypeError: Si alguno de los argumentos no es un número.
    """
    if not isinstance(a, (int, float)) or isinstance(a, bool):
        raise TypeError(f"El argumento 'a' debe ser un número, recibido: {type(a).__name__}")
    if not isinstance(b, (int, float)) or isinstance(b, bool):
        raise TypeError(f"El argumento 'b' debe ser un número, recibido: {type(b).__name__}")
    return a + b
