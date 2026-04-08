"""
Comprehensive pytest tests for the `resolute` library.

Tested features:
- Result combinators: collect, partition
- @safe decorator (sync & async)
- @do / @do_option do-notation
- Error context and chain
- Option.ok_or() conversion
- Unwrap safety (UnwrapError)
"""

import pytest
from typing import List, Tuple
from resolute import (
    Ok, Err, Result, Option, Some, Nothing,
    collect, partition,
    safe, safe_async, do, do_option,
    UnwrapError, ContextError
)


# ----------------------------------------------------------------------
# collect combinator
# ----------------------------------------------------------------------
def test_collect_all_ok() -> None:
    results: List[Result[int, str]] = [Ok(1), Ok(2), Ok(3)]
    assert collect(results) == Ok([1, 2, 3])


def test_collect_first_err() -> None:
    results: List[Result[int, str]] = [Ok(1), Err("fail"), Ok(3)]
    assert collect(results) == Err("fail")


def test_collect_empty_list() -> None:
    assert collect([]) == Ok([])


def test_collect_large_with_first_err() -> None:
    # 1000 Oks followed by one Err
    results = [Ok(i) for i in range(1000)] + [Err("boom")]
    assert collect(results) == Err("boom")


def test_collect_lazy_iterable() -> None:
    def gen():
        yield Ok(1)
        yield Err("stop")
        yield Ok(2)   # never reached

    assert collect(gen()) == Err("stop")


# ----------------------------------------------------------------------
# partition combinator
# ----------------------------------------------------------------------
def test_partition_all_ok() -> None:
    results: List[Result[int, str]] = [Ok(1), Ok(2), Ok(3)]
    oks, errs = partition(results)
    assert oks == [1, 2, 3]
    assert errs == []


def test_partition_all_err() -> None:
    results: List[Result[int, str]] = [Err("a"), Err("b")]
    oks, errs = partition(results)
    assert oks == []
    assert errs == ["a", "b"]


def test_partition_mixed() -> None:
    results: List[Result[int, str]] = [Ok(1), Err("x"), Ok(2), Err("y")]
    oks, errs = partition(results)
    assert oks == [1, 2]
    assert errs == ["x", "y"]


def test_partition_empty() -> None:
    oks, errs = partition([])
    assert oks == []
    assert errs == []


def test_partition_large_random() -> None:
    import random
    random.seed(42)
    size = 1000
    results = []
    expected_oks = []
    expected_errs = []
    for i in range(size):
        if random.choice([True, False]):
            results.append(Ok(i))
            expected_oks.append(i)
        else:
            results.append(Err(str(i)))
            expected_errs.append(str(i))

    oks, errs = partition(results)
    assert oks == expected_oks
    assert errs == expected_errs
    # order preserved
    assert len(oks) + len(errs) == size


# ----------------------------------------------------------------------
# @safe decorator (sync)
# ----------------------------------------------------------------------
def test_safe_sync_success() -> None:
    @safe()
    def divide(a: int, b: int) -> float:
        return a / b

    result = divide(10, 2)
    assert result == Ok(5.0)


def test_safe_sync_caught_exception() -> None:
    @safe(catch=(ZeroDivisionError,))
    def divide(a: int, b: int) -> float:
        return a / b

    result = divide(10, 0)
    assert result.is_err()
    assert isinstance(result.unwrap_err(), ZeroDivisionError)


def test_safe_sync_uncaught_exception_bubbles() -> None:
    @safe(catch=(ValueError,))
    def oops() -> None:
        raise TypeError("not caught")

    with pytest.raises(TypeError, match="not caught"):
        oops()


def test_safe_sync_custom_exception() -> None:
    class MyError(Exception):
        pass

    @safe(catch=(MyError,))
    def fail() -> None:
        raise MyError("custom")

    result = fail()
    assert result.is_err()
    assert isinstance(result.unwrap_err(), MyError)


# ----------------------------------------------------------------------
# @safe decorator (async)
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_safe_async_success() -> None:
    @safe_async()
    async def async_double(x: int) -> int:
        return x * 2

    result = await async_double(21)
    assert result == Ok(42)


@pytest.mark.asyncio
async def test_safe_async_caught_exception() -> None:
    @safe_async(catch=(RuntimeError,))
    async def async_fail() -> None:
        raise RuntimeError("async boom")

    result = await async_fail()
    assert result.is_err()
    assert str(result.unwrap_err()) == "async boom"


# ----------------------------------------------------------------------
# do-notation (Result)
# ----------------------------------------------------------------------
def test_do_notation_ok() -> None:
    @do()
    def add_ok(a: Result[int, str], b: Result[int, str]) -> Result[int, str]:
        x = yield a
        y = yield b
        return Ok(x + y)

    assert add_ok(Ok(3), Ok(5)) == Ok(8)


def test_do_notation_short_circuit() -> None:
    @do()
    def add_with_err(a: Result[int, str], b: Result[int, str]) -> Result[int, str]:
        x = yield a
        y = yield b
        return Ok(x + y)

    assert add_with_err(Ok(3), Err("fail")) == Err("fail")
    assert add_with_err(Err("first"), Ok(5)) == Err("first")


def test_do_notation_mixed_ok_err() -> None:
    @do()
    def first_err() -> Result[int, str]:
        x = yield Err("stop")
        return Ok(x + 1)   # never reached

    assert first_err() == Err("stop")


# ----------------------------------------------------------------------
# do-notation (Option)
# ----------------------------------------------------------------------
def test_do_option_some() -> None:
    @do_option()
    def add_some(a: Option[int], b: Option[int]) -> Option[int]:
        x = yield a
        y = yield b
        return Some(x + y)

    assert add_some(Some(3), Some(5)) == Some(8)


def test_do_option_nothing_short_circuit() -> None:
    @do_option()
    def add_with_nothing(a: Option[int], b: Option[int]) -> Option[int]:
        x = yield a
        y = yield b
        return Some(x + y)

    assert add_with_nothing(Some(3), Nothing) == Nothing
    assert add_with_nothing(Nothing, Some(5)) == Nothing


# ----------------------------------------------------------------------
# Option -> Result conversion (.ok_or)
# ----------------------------------------------------------------------
def test_option_ok_or_some() -> None:
    assert Some(42).ok_or("missing") == Ok(42)


def test_option_ok_or_nothing() -> None:
    assert Nothing.ok_or("error msg") == Err("error msg")


# ----------------------------------------------------------------------
# Error context and chain
# ----------------------------------------------------------------------
def test_error_context() -> None:
    res = Err(ValueError("original")).context("wrapping context")
    assert res.is_err()
    err = res.unwrap_err()
    # root_cause returns the original exception
    assert isinstance(err.root_cause, ValueError)
    assert str(err.root_cause) == "original"

    chain = err.chain()
    assert len(chain) == 2
    assert isinstance(chain[0], ContextError)  # the added context
    assert isinstance(chain[1], ValueError)     # original cause


def test_error_context_multiple() -> None:
    res = Err(KeyError("missing")).context("first").context("second")
    err = res.unwrap_err()
    chain = err.chain()
    assert len(chain) == 3
    assert str(chain[0]) == "second: first: 'missing'"
    assert str(chain[1]) == "first: 'missing'"
    assert isinstance(chain[-1], KeyError)


def test_ok_context_does_nothing() -> None:
    ok = Ok(100)
    assert ok.context("should be ignored") == Ok(100)
    # Ok does not have a chain() method
    assert not hasattr(ok, "chain")


# ----------------------------------------------------------------------
# Unwrap safety (UnwrapError)
# ----------------------------------------------------------------------
def test_unwrap_ok() -> None:
    assert Ok(99).unwrap() == 99


def test_unwrap_err_raises() -> None:
    err = Err("broken")
    with pytest.raises(UnwrapError, match=r"Called unwrap\(\) on an Err value"):
        err.unwrap()


def test_unwrap_nothing_raises() -> None:
    with pytest.raises(UnwrapError, match=r"Called unwrap\(\) on Nothing"):
        Nothing.unwrap()


def test_unwrap_or_ok() -> None:
    assert Ok(10).unwrap_or(999) == 10
    assert Err("err").unwrap_or(999) == 999


def test_unwrap_err_ok() -> None:
    assert Err("fail").unwrap_err() == "fail"
    with pytest.raises(UnwrapError, match=r"Called unwrap_err\(\) on an Ok value"):
        Ok(123).unwrap_err()


def test_expect_ok() -> None:
    assert Ok(42).expect("should be ok") == 42


def test_expect_err() -> None:
    with pytest.raises(UnwrapError, match=r"custom message"):
        Err("broken").expect("custom message")
