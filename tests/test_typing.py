"""
tests/test_typing.py
Static type-checking assertions for explicit_result using `mypy` or `pyright`.
These tests check that generics resolve correctly.
"""
from typing_extensions import assert_type
from explicit_result import Ok, Err, Result, Some, Nothing, Option, safe

def test_result_types() -> None:
    # Basic creation
    r_ok: Result[int, str] = Ok(42)
    assert_type(r_ok.unwrap(), int)
    
    r_err: Result[int, str] = Err("bad")
    assert_type(r_err.unwrap_err(), str)

    # Chaining transformations
    r_map = r_ok.map(lambda x: float(x))
    assert_type(r_map, Result[float, str])

    r_map_err = r_err.map_err(lambda e: Exception(e))
    assert_type(r_map_err, Result[int, Exception])

    def f(x: int) -> Result[bool, str]:
        return Ok(x > 0)

    # and_then changes the inner type T
    r_chained = r_ok.and_then(f)
    assert_type(r_chained, Result[bool, str])

def test_option_types() -> None:
    o_some: Option[int] = Some(42)
    assert_type(o_some.unwrap(), int)

    o_map = o_some.map(lambda x: str(x))
    assert_type(o_map, Option[str])

    def f(x: int) -> Option[bool]:
        return Some(x > 0)

    o_chained = o_some.and_then(f)
    assert_type(o_chained, Option[bool])

def test_decorators() -> None:
    @safe(catch=ValueError)
    def parse(s: str) -> int:
        return int(s)

    # Result should capture the return type and the Exception
    res = parse("42")
    assert_type(res, Result[int, ValueError])
