import pytest
from explicit_result import Ok, Err, ContextError, Some, Nothing, Result

def test_context_error_root_cause():
    base = ValueError("original")
    ctx1 = ContextError("layer 1", base)
    ctx2 = ContextError("layer 2", ctx1)
    
    assert ctx2.root_cause is base
    assert ctx1.root_cause is base

def test_result_root_cause_with_context():
    base = ValueError("original")
    res = Err(base).context("wrapper")
    
    root = res.root_cause
    assert root == Some(base)

def test_result_root_cause_simple_err():
    res = Err("static error")
    assert res.root_cause == Some("static error")

def test_result_root_cause_ok():
    res = Ok(42)
    assert res.root_cause is Nothing

def test_result_from_optional():
    assert Result.from_optional(10, "err") == Ok(10)
    assert Result.from_optional(None, "err") == Err("err")

def test_option_identity_optimization():
    # Verify that is_nothing() uses identity check
    assert Nothing.is_nothing() is True
    assert Some(1).is_nothing() is False

def test_context_error_chain():
    base = ValueError("a")
    err = ContextError("c", ContextError("b", base))
    chain = err.chain()
    assert len(chain) == 3
    assert chain[-1] is base
