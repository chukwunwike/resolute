import pytest
from explicit_result import safe, Ok, Err

def throw_error():
    raise ValueError("oops")

@safe(catch=ValueError)
def safe_throw():
    raise ValueError("oops")

def manual_try():
    try:
        throw_error()
    except ValueError as e:
        return e

def test_benchmark_try_except(benchmark):
    benchmark(manual_try)

def test_benchmark_safe_decorator(benchmark):
    benchmark(safe_throw)

def deep_nest_try():
    try:
        try:
            try:
                throw_error()
            except ValueError:
                raise
        except ValueError:
            raise
    except ValueError as e:
        return e

@safe(catch=ValueError)
def deep_nest_safe():
    return safe_throw()

def test_benchmark_deep_nest_try(benchmark):
    benchmark(deep_nest_try)

def test_benchmark_deep_nest_safe(benchmark):
    benchmark(deep_nest_safe)
