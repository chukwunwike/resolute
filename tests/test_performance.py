"""
tests/test_performance.py
Micro-benchmarks to ensure Result and Option operations are extremely fast.
Runs via pytest-benchmark.
"""
from resolute import Ok, Err, safe

def native_exception_control_flow():
    try:
        raise ValueError("error")
    except ValueError:
        return 0

def resolute_control_flow():
    try:
        Err("error").unwrap()
    except Exception:
        return 0

def test_benchmark_native_exceptions(benchmark):
    """Benchmark raw Python try/except."""
    benchmark(native_exception_control_flow)

def test_benchmark_resolute_unwrapping(benchmark):
    """Benchmark resolute Err generation and unwrapping."""
    benchmark(resolute_control_flow)

# Testing `@safe` decorator overhead
def native_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return 0

@safe(catch=ZeroDivisionError)
def resolute_divide(a, b):
    return a / b

def wrapped_divide_benchmark(a, b):
    return resolute_divide(a, b).unwrap_or(0)

def test_benchmark_safe_decorator(benchmark):
    """Benchmark overhead of the @safe decorator."""
    benchmark(wrapped_divide_benchmark, 10, 0)
