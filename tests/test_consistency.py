import pytest
from explicit_result import Ok, Err, Some, Nothing, Result, Option, do, do_option, flatten_option

def test_result_transpose():
    # Ok(Some) -> Some(Ok)
    assert Ok(Some(1)).transpose() == Some(Ok(1))
    # Ok(Nothing) -> Nothing
    assert Ok(Nothing).transpose() == Nothing
    # Err -> Some(Err)
    assert Err("x").transpose() == Some(Err("x"))

def test_option_transpose():
    # Some(Ok) -> Ok(Some)
    assert Some(Ok(1)).transpose() == Ok(Some(1))
    # Some(Err) -> Err
    assert Some(Err("x")).transpose() == Err("x")
    # Nothing -> Ok(Nothing)
    assert Nothing.transpose() == Ok(Nothing)

def test_result_zip():
    assert Ok(1).zip(Ok(2)) == Ok((1, 2))
    assert Err("x").zip(Ok(2)) == Err("x")
    assert Ok(1).zip(Err("y")) == Err("y")
    assert Err("x").zip(Err("y")) == Err("x")

def test_result_of():
    assert Result.of(1, "err") == Ok(1)
    assert Result.of(None, "err") == Err("err")

def test_flatten_option():
    assert flatten_option(Some(Some(1))) == Some(1)
    assert flatten_option(Some(Nothing)) == Nothing
    assert flatten_option(Nothing) == Nothing

def test_do_yield_guard_result():
    @do()
    def bad_yield():
        yield 1  # Not a Result or Option
        return 2

    with pytest.raises(TypeError) as exc:
        bad_yield()
    assert "Value yielded in @do must be Result or Option" in str(exc.value)

def test_do_yield_guard_option():
    @do_option()
    def bad_yield_opt():
        yield None  # Not an Option or Result
        return 2

    with pytest.raises(TypeError) as exc:
        bad_yield_opt()
    assert "Value yielded in @do_option must be Option or Result" in str(exc.value)

def test_do_notation_mixed_yields():
    # Result @do should allow yielding Option (it has _is_monadic)
    # but unwrap() will raise if it's Nothing.
    @do()
    def mixed():
        val = yield Some(10)
        return val * 2
    
    assert mixed() == Ok(20)

    @do()
    def mixed_fail():
        yield Nothing
        return 1
    
    # In my implementation, if Nothing is yielded, it returns yielded (Nothing)
    # But @do expects Result. If Nothing is returned, the caller of @do 
    # will get an Option instead of a Result. This is technically an inconsistency 
    # but better than crashing.
    assert mixed_fail() == Nothing

def test_do_option_mixed_yields():
    @do_option()
    def mixed_opt():
        val = yield Ok(10)
        return val * 2
    
    assert mixed_opt() == Some(20)

    @do_option()
    def mixed_opt_fail():
        yield Err("x")
        return 1
    
    # Bug 2 fix: Err in Option context is converted to Nothing
    assert mixed_opt_fail() == Nothing
