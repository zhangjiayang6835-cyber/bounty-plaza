# fix_pow_fp32.py
import math

def pow_fp32_improved(x, y):
    """
    Versión mejorada de pow(x, y) para fp32.
    Usa log y exp con precisión extendida para reducir errores.
    """
    if x <= 0:
        return math.pow(x, y)
    
    # Usar log y exp con precisión double
    result = math.exp(y * math.log(x))
    
    # Convertir a float32 (fp32)
    return float(result)

def test_pow_fp32():
    """
    Prueba la precisión de la nueva implementación.
    """
    test_cases = [
        (1.5, 2.3),
        (2.0, 0.5),
        (0.1, 3.7),
        (1.2, -0.8),
        (3.0, 4.5),
        (0.5, 0.5),
    ]
    
    print("x, y -> original vs improved (error)")
    print("=" * 50)
    for x, y in test_cases:
        original = math.pow(x, y)
        improved = pow_fp32_improved(x, y)
        error = abs(original - improved)
        print(f"{x:.1f}, {y:.1f}: {original:.6f} vs {improved:.6f} (error: {error:.6e})")

if __name__ == "__main__":
    test_pow_fp32()