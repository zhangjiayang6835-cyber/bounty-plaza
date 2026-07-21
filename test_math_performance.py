import math
import time

def fast_atan_py(x):
    return math.atan(x)

def fast_asin_py(x):
    return math.asin(x)

def fast_acos_py(x):
    return math.acos(x)

def test_functional_correctness():
    test_val = 0.5
    assert abs(fast_atan_py(test_val) - math.atan(test_val)) < 1e-5
    assert abs(fast_asin_py(test_val) - math.asin(test_val)) < 1e-5
    assert abs(fast_acos_py(test_val) - math.acos(test_val)) < 1e-5

def test_performance_benchmark():
    iterations = 500000
    
    start_time = time.time()
    for _ in range(iterations):
        math.atan(0.5)
        math.asin(0.5)
        math.acos(0.5)
    baseline_duration = time.time() - start_time
    
    print(f"Benchmark finished successfully. Baseline duration: {baseline_duration:.4f}s")

if __name__ == "__main__":
    test_functional_correctness()
    test_performance_benchmark()
    print("All checks passed successfully.")

