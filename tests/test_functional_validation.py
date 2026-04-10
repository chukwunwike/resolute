"""
Functional validation tests for Resolute.
This suite demonstrates the primary user-facing features and confirms
that the library behaves as expected in common scenarios.
"""

from typing import Union
import pytest
from explicit_result import Ok, Err, Result, Some, Nothing, Option, safe, UnwrapError


# 1. CORE RESULT BEHAVIOR
# ---------------------------------------------------------------------------

def test_result_basic_usage():
    """Verify that Ok and Err variants encapsulate data correctly."""
    success = Ok(42)
    failure = Err("something went wrong")

    assert success.is_ok()
    assert not success.is_err()
    assert success.unwrap() == 42

    assert failure.is_err()
    assert not failure.is_ok()
    with pytest.raises(UnwrapError, match="something went wrong"):
        failure.unwrap()


def test_result_chaining():
    """Verify and_then (flatmap) short-circuits on error."""
    def double(n: int) -> Result[int, str]:
        return Ok(n * 2)

    def fail_if_large(n: int) -> Result[int, str]:
        if n > 10:
            return Err("too big")
        return Ok(n)

    # Success chain: 5 -> 10 (ok) -> 10
    res1 = Ok(5).and_then(double).and_then(fail_if_large)
    assert res1 == Ok(10)

    # Failure chain: 8 -> 16 (too big) -> Err
    res2 = Ok(8).and_then(double).and_then(fail_if_large)
    assert res2 == Err("too big")

    # Short-circuit chain: Err -> (skipped) -> (skipped)
    res3 = Err("start fail").and_then(double).and_then(fail_if_large)
    assert res3 == Err("start fail")


# 2. CORE OPTION BEHAVIOR
# ---------------------------------------------------------------------------

def test_option_basic_usage():
    """Verify that Some and Nothing encapsulate presence/absence correctly."""
    present = Some("hello")
    absent = Nothing

    assert present.is_some()
    assert not present.is_nothing()
    assert present.unwrap() == "hello"

    assert absent.is_nothing()
    assert not absent.is_some()
    with pytest.raises(UnwrapError, match=r"Called unwrap\(\) on Nothing"):
        absent.unwrap()


def test_option_mapping_and_filtering():
    """Verify map and filter operations on Option."""
    opt = Some(10)
    
    # Map preserves Some
    assert opt.map(lambda x: x + 5) == Some(15)
    
    # Filter keeps value if predicate is true
    assert opt.filter(lambda x: x > 5) == Some(10)
    
    # Filter returns Nothing if predicate is false
    assert opt.filter(lambda x: x > 15) == Nothing
    
    # Operations on Nothing return Nothing
    assert Nothing.map(lambda x: x + 1) == Nothing
    assert Nothing.filter(lambda x: True) == Nothing


# 3. DECORATORS (@safe)
# ---------------------------------------------------------------------------

def test_safe_decorator_sync():
    """Verify that @safe catches specific exceptions and returns Err."""
    
    @safe(catch=ValueError)
    def parse_int(s: str) -> int:
        return int(s)

    # Successful call
    res_ok = parse_int("123")
    assert res_ok == Ok(123)

    # Failed call (caught)
    res_err = parse_int("abc")
    assert res_err.is_err()
    assert isinstance(res_err.unwrap_err(), ValueError)

    # Uncaught exception (should bubble up)
    @safe(catch=ValueError)
    def oops():
        raise KeyError("not a value error")
        
    with pytest.raises(KeyError):
        oops()


# 4. INTEROP (Result <-> Option)
# ---------------------------------------------------------------------------

def test_interop():
    """Verify Result can be converted to Option and vice versa."""
    # Ok -> Some
    assert Ok(1).ok() == Some(1)
    # Err -> Nothing
    assert Err("bad").ok() == Nothing
    
    # Some -> Ok
    assert Some(1).ok_or("err") == Ok(1)
    # Nothing -> Err
    assert Nothing.ok_or("err") == Err("err")


# 5. PATTERN MATCHING (Python 3.10+)
# ---------------------------------------------------------------------------

def test_pattern_matching():
    """Verify components support structural pattern matching."""
    result = Ok(100)
    
    # We simulate matching here (since we support 3.9+, but the structural
    # match logic is built into the classes via __match_args__)
    match_val = None
    
    # Structural match simulation:
    if isinstance(result, Ok):
        match_val = result.value
    
    assert match_val == 100
    
    option = Some("found it")
    if isinstance(option, Some):
        match_val = option.value
        
    assert match_val == "found it"
