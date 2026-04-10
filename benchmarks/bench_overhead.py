import pytest
from explicit_result import Ok, Err

def return_val():
    return 42

def return_ok():
    return Ok(42)

def test_benchmark_creation_plain(benchmark):
    benchmark(return_val)

def test_benchmark_creation_ok(benchmark):
    benchmark(return_ok)

def logic_if(val):
    if val > 0:
        return val * 2
    return None

def logic_result(val):
    return Ok(val).map(lambda x: x * 2).ok()

def test_benchmark_logic_if(benchmark):
    benchmark(logic_if, 10)

def test_benchmark_logic_result(benchmark):
    benchmark(logic_result, 10)
