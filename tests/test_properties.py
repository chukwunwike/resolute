"""
tests/test_properties.py
Property-based tests for explicit_result Result and Option using Hypothesis.
Tests Monad laws (Left Identity, Right Identity, Associativity).
"""
from hypothesis import given, strategies as st
from explicit_result import Ok, Err, Result, Some, Nothing, Option

# Strategies for generating values and errors
val_st = st.integers() | st.text() | st.floats(allow_nan=False, allow_infinity=False)
err_st = st.integers() | st.text()

# Pure functions for testing chained transformations
def f_ok(x) -> Result:
    return Ok(f"f({x})")

def g_ok(x) -> Result:
    return Ok(f"g({x})")

def f_some(x) -> Option:
    return Some(f"f({x})")

def g_some(x) -> Option:
    return Some(f"g({x})")

# === Result Monad Laws ===

@given(val_st)
def test_result_left_identity(v):
    # Left Identity: return v >>= f is equivalent to f(v)
    assert Ok(v).and_then(f_ok) == f_ok(v)

@given(val_st)
def test_result_right_identity(v):
    # Right Identity: m >>= return is equivalent to m
    m = Ok(v)
    assert m.and_then(Ok) == m

@given(val_st)
def test_result_associativity(v):
    # Associativity: (m >>= f) >>= g is equivalent to m >>= (\x -> f(x) >>= g)
    m = Ok(v)
    left_side = m.and_then(f_ok).and_then(g_ok)
    right_side = m.and_then(lambda x: f_ok(x).and_then(g_ok))
    assert left_side == right_side

@given(err_st)
def test_err_short_circuit(e):
    m = Err(e)
    assert m.and_then(f_ok) == m  # Error propagates

# === Option Monad Laws ===

@given(val_st)
def test_option_left_identity(v):
    assert Some(v).and_then(f_some) == f_some(v)

@given(val_st)
def test_option_right_identity(v):
    m = Some(v)
    assert m.and_then(Some) == m

@given(val_st)
def test_option_associativity(v):
    m = Some(v)
    left_side = m.and_then(f_some).and_then(g_some)
    right_side = m.and_then(lambda x: f_some(x).and_then(g_some))
    assert left_side == right_side

def test_nothing_short_circuit():
    m = Nothing
    assert m.and_then(f_some) is Nothing

