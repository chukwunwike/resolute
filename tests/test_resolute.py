"""
tests/test_resolute.py
~~~~~~~~~~~~~~~~~~~~~~~
Full test suite for resolute.

Covers:
  - Result (Ok / Err): all methods
  - Option (Some / Nothing): all methods
  - @safe decorator
  - @safe_async decorator
  - Combinators: collect, collect_all, partition, transpose,
    flatten_result, sequence, transpose_result
  - Edge cases: hashing, equality, iteration, bool, pattern matching
  - SafeDecoratorError for forbidden exception types
"""

import asyncio
import sys
import warnings

import pytest

from resolute import (
    Err,
    Ok,
    Nothing,
    Option,
    Result,
    SafeDecoratorError,
    Some,
    UnwrapError,
    collect,
    collect_all,
    flatten_result,
    partition,
    safe,
    safe_async,
    sequence,
    transpose,
    transpose_result,
)


# ============================================================================
# Result — basic state inspection
# ============================================================================

class TestResultStateInspection:
    def test_ok_is_ok(self):
        assert Ok(1).is_ok() is True

    def test_ok_is_not_err(self):
        assert Ok(1).is_err() is False

    def test_err_is_err(self):
        assert Err("x").is_err() is True

    def test_err_is_not_ok(self):
        assert Err("x").is_ok() is False

    def test_ok_and_predicate_true(self):
        assert Ok(5).is_ok_and(lambda x: x > 3) is True

    def test_ok_and_predicate_false(self):
        assert Ok(2).is_ok_and(lambda x: x > 3) is False

    def test_err_ok_and_always_false(self):
        assert Err("x").is_ok_and(lambda x: True) is False

    def test_err_and_predicate_true(self):
        assert Err("bad").is_err_and(lambda e: "bad" in e) is True

    def test_err_and_predicate_false(self):
        assert Err("ok").is_err_and(lambda e: "bad" in e) is False

    def test_ok_err_and_always_false(self):
        assert Ok(1).is_err_and(lambda e: True) is False


# ============================================================================
# Result — extracting values
# ============================================================================

class TestResultUnwrap:
    def test_ok_unwrap(self):
        assert Ok(42).unwrap() == 42

    def test_err_unwrap_raises(self):
        with pytest.raises(UnwrapError) as exc_info:
            Err("oops").unwrap()
        assert "oops" in str(exc_info.value)
        assert exc_info.value.original == "oops"

    def test_ok_unwrap_or(self):
        assert Ok(1).unwrap_or(99) == 1

    def test_err_unwrap_or(self):
        assert Err("x").unwrap_or(99) == 99

    def test_ok_unwrap_or_else(self):
        assert Ok(5).unwrap_or_else(lambda e: 0) == 5

    def test_err_unwrap_or_else(self):
        assert Err("bad").unwrap_or_else(lambda e: len(e)) == 3

    def test_ok_unwrap_or_raise(self):
        assert Ok(7).unwrap_or_raise(ValueError("nope")) == 7

    def test_err_unwrap_or_raise(self):
        with pytest.raises(ValueError, match="nope"):
            Err("x").unwrap_or_raise(ValueError("nope"))

    def test_ok_unwrap_err_raises(self):
        with pytest.raises(UnwrapError):
            Ok(1).unwrap_err()

    def test_err_unwrap_err(self):
        assert Err("e").unwrap_err() == "e"

    def test_ok_expect(self):
        assert Ok(3).expect("should exist") == 3

    def test_err_expect_raises_with_message(self):
        with pytest.raises(UnwrapError, match="should exist"):
            Err("x").expect("should exist")

    def test_ok_expect_err_raises(self):
        with pytest.raises(UnwrapError, match="should be error"):
            Ok(1).expect_err("should be error")

    def test_err_expect_err(self):
        assert Err("bad").expect_err("should be error") == "bad"


# ============================================================================
# Result — transforming Ok values
# ============================================================================

class TestResultMap:
    def test_map_ok(self):
        assert Ok(2).map(lambda x: x * 3) == Ok(6)

    def test_map_err_passthrough(self):
        assert Err("bad").map(lambda x: x * 3) == Err("bad")

    def test_map_or_ok(self):
        assert Ok(2).map_or(0, lambda x: x * 3) == 6

    def test_map_or_err(self):
        assert Err("bad").map_or(0, lambda x: x * 3) == 0

    def test_map_or_else_ok(self):
        assert Ok(2).map_or_else(lambda e: 0, lambda x: x * 3) == 6

    def test_map_or_else_err(self):
        assert Err("bad").map_or_else(lambda e: len(e), lambda x: 0) == 3

    def test_map_err_transforms_error(self):
        assert Err("bad").map_err(str.upper) == Err("BAD")

    def test_map_err_ok_passthrough(self):
        assert Ok(1).map_err(str.upper) == Ok(1)


# ============================================================================
# Result — chaining
# ============================================================================

class TestResultChaining:
    def _safe_div(self, x: int) -> Result[float, str]:
        return Ok(10 / x) if x != 0 else Err("division by zero")

    def test_and_then_ok(self):
        assert Ok(2).and_then(self._safe_div) == Ok(5.0)

    def test_and_then_ok_leads_to_err(self):
        assert Ok(0).and_then(self._safe_div) == Err("division by zero")

    def test_and_then_short_circuits_on_err(self):
        assert Err("prior").and_then(self._safe_div) == Err("prior")

    def test_or_else_ok_passthrough(self):
        assert Ok(1).or_else(lambda e: Ok(0)) == Ok(1)

    def test_or_else_recovers_err(self):
        assert Err("bad").or_else(lambda e: Ok(99)) == Ok(99)

    def test_or_else_remaps_err(self):
        assert Err("bad").or_else(lambda e: Err(e.upper())) == Err("BAD")

    def test_and_returns_other_if_ok(self):
        assert Ok(1).and_(Ok(2)) == Ok(2)

    def test_and_returns_self_if_err(self):
        assert Err("x").and_(Ok(2)) == Err("x")

    def test_or_returns_self_if_ok(self):
        assert Ok(1).or_(Ok(99)) == Ok(1)

    def test_or_returns_other_if_err(self):
        assert Err("x").or_(Ok(99)) == Ok(99)


# ============================================================================
# Result — conversion to Option
# ============================================================================

class TestResultToOption:
    def test_ok_to_some(self):
        assert Ok(1).ok() == Some(1)

    def test_err_to_nothing(self):
        assert Ok(1).err() is Nothing
        assert Err("x").ok() is Nothing

    def test_err_to_some(self):
        assert Err("x").err() == Some("x")


# ============================================================================
# Result — dunder methods
# ============================================================================

class TestResultDunder:
    def test_ok_repr(self):
        assert repr(Ok(42)) == "Ok(42)"

    def test_err_repr(self):
        assert repr(Err("bad")) == "Err('bad')"

    def test_ok_equality(self):
        assert Ok(1) == Ok(1)
        assert Ok(1) != Ok(2)

    def test_err_equality(self):
        assert Err("x") == Err("x")
        assert Err("x") != Err("y")

    def test_ok_err_not_equal(self):
        assert Ok(1) != Err(1)

    def test_ok_hashable(self):
        s = {Ok(1), Ok(1), Ok(2)}
        assert len(s) == 2

    def test_err_hashable(self):
        s = {Err("a"), Err("a"), Err("b")}
        assert len(s) == 2

    def test_ok_bool_truthy(self):
        assert bool(Ok(1)) is True
        assert bool(Ok(0)) is True  # 0 is Ok, not falsy
        assert bool(Ok(None)) is True

    def test_err_bool_falsy(self):
        assert bool(Err("x")) is False

    def test_ok_iteration(self):
        assert list(Ok(5)) == [5]

    def test_err_iteration_empty(self):
        assert list(Err("x")) == []

    def test_ok_in_list_comprehension(self):
        results = [Ok(1), Err("skip"), Ok(3)]
        values = [x for r in results for x in r]
        assert values == [1, 3]


# ============================================================================
# Result — pattern matching (Python 3.10+)
# ============================================================================

@pytest.mark.skipif(sys.version_info < (3, 10), reason="match requires Python 3.10+")
class TestResultPatternMatching:
    def test_ok_match(self):
        result = Ok(42)
        matched = None
        match result:
            case Ok(v):
                matched = ("ok", v)
            case Err(e):
                matched = ("err", e)
        assert matched == ("ok", 42)

    def test_err_match(self):
        result = Err("bad")
        matched = None
        match result:
            case Ok(v):
                matched = ("ok", v)
            case Err(e):
                matched = ("err", e)
        assert matched == ("err", "bad")


# ============================================================================
# Option — basic state inspection
# ============================================================================

class TestOptionStateInspection:
    def test_some_is_some(self):
        assert Some(1).is_some() is True

    def test_some_is_not_nothing(self):
        assert Some(1).is_nothing() is False

    def test_nothing_is_nothing(self):
        assert Nothing.is_nothing() is True

    def test_nothing_is_not_some(self):
        assert Nothing.is_some() is False

    def test_some_and_predicate_true(self):
        assert Some(4).is_some_and(lambda x: x > 3) is True

    def test_some_and_predicate_false(self):
        assert Some(2).is_some_and(lambda x: x > 3) is False

    def test_nothing_some_and_false(self):
        assert Nothing.is_some_and(lambda x: True) is False


# ============================================================================
# Option — extracting values
# ============================================================================

class TestOptionUnwrap:
    def test_some_unwrap(self):
        assert Some(42).unwrap() == 42

    def test_nothing_unwrap_raises(self):
        with pytest.raises(UnwrapError):
            Nothing.unwrap()

    def test_some_unwrap_or(self):
        assert Some(1).unwrap_or(99) == 1

    def test_nothing_unwrap_or(self):
        assert Nothing.unwrap_or(99) == 99

    def test_some_unwrap_or_else(self):
        assert Some(1).unwrap_or_else(lambda: 99) == 1

    def test_nothing_unwrap_or_else(self):
        assert Nothing.unwrap_or_else(lambda: 99) == 99

    def test_some_unwrap_or_raise(self):
        assert Some(1).unwrap_or_raise(ValueError()) == 1

    def test_nothing_unwrap_or_raise(self):
        with pytest.raises(TypeError):
            Nothing.unwrap_or_raise(TypeError("missing"))

    def test_some_expect(self):
        assert Some(1).expect("must exist") == 1

    def test_nothing_expect_raises(self):
        with pytest.raises(UnwrapError, match="must exist"):
            Nothing.expect("must exist")


# ============================================================================
# Option — transforming values
# ============================================================================

class TestOptionTransform:
    def test_map_some(self):
        assert Some(2).map(lambda x: x * 3) == Some(6)

    def test_map_nothing_passthrough(self):
        assert Nothing.map(lambda x: x * 3) is Nothing

    def test_map_or_some(self):
        assert Some(2).map_or(0, lambda x: x * 3) == 6

    def test_map_or_nothing(self):
        assert Nothing.map_or(0, lambda x: x * 3) == 0

    def test_map_or_else_some(self):
        assert Some(2).map_or_else(lambda: 0, lambda x: x * 3) == 6

    def test_map_or_else_nothing(self):
        assert Nothing.map_or_else(lambda: 99, lambda x: 0) == 99

    def test_filter_passes(self):
        assert Some(4).filter(lambda x: x > 3) == Some(4)

    def test_filter_fails(self):
        assert Some(2).filter(lambda x: x > 3) is Nothing

    def test_filter_nothing(self):
        assert Nothing.filter(lambda x: True) is Nothing


# ============================================================================
# Option — chaining
# ============================================================================

class TestOptionChaining:
    def _double_if_positive(self, x: int) -> Option:
        return Some(x * 2) if x > 0 else Nothing

    def test_and_then_some(self):
        assert Some(3).and_then(self._double_if_positive) == Some(6)

    def test_and_then_some_to_nothing(self):
        assert Some(-1).and_then(self._double_if_positive) is Nothing

    def test_and_then_nothing(self):
        assert Nothing.and_then(self._double_if_positive) is Nothing

    def test_or_else_some_passthrough(self):
        assert Some(1).or_else(lambda: Some(99)) == Some(1)

    def test_or_else_nothing_recovers(self):
        assert Nothing.or_else(lambda: Some(99)) == Some(99)

    def test_and_some_some(self):
        assert Some(1).and_(Some(2)) == Some(2)

    def test_and_nothing_returns_nothing(self):
        assert Nothing.and_(Some(2)) is Nothing

    def test_or_some_returns_self(self):
        assert Some(1).or_(Some(99)) == Some(1)

    def test_or_nothing_returns_other(self):
        assert Nothing.or_(Some(99)) == Some(99)

    def test_zip_some_some(self):
        assert Some(1).zip(Some("a")) == Some((1, "a"))

    def test_zip_some_nothing(self):
        assert Some(1).zip(Nothing) is Nothing

    def test_zip_nothing_some(self):
        assert Nothing.zip(Some("a")) is Nothing

    def test_flatten_some_some(self):
        assert Some(Some(1)).flatten() == Some(1)

    def test_flatten_some_nothing(self):
        assert Some(Nothing).flatten() is Nothing

    def test_flatten_nothing(self):
        assert Nothing.flatten() is Nothing


# ============================================================================
# Option — conversion to Result
# ============================================================================

class TestOptionToResult:
    def test_some_ok_or(self):
        assert Some(1).ok_or("missing") == Ok(1)

    def test_nothing_ok_or(self):
        assert Nothing.ok_or("missing") == Err("missing")

    def test_some_ok_or_else(self):
        assert Some(1).ok_or_else(lambda: "missing") == Ok(1)

    def test_nothing_ok_or_else(self):
        assert Nothing.ok_or_else(lambda: "missing") == Err("missing")


# ============================================================================
# Option — dunder methods
# ============================================================================

class TestOptionDunder:
    def test_some_repr(self):
        assert repr(Some(42)) == "Some(42)"

    def test_nothing_repr(self):
        assert repr(Nothing) == "Nothing"

    def test_some_equality(self):
        assert Some(1) == Some(1)
        assert Some(1) != Some(2)

    def test_nothing_equality(self):
        assert Nothing == Nothing

    def test_some_not_equal_nothing(self):
        assert Some(1) != Nothing

    def test_some_hashable(self):
        s = {Some(1), Some(1), Some(2)}
        assert len(s) == 2

    def test_nothing_singleton(self):
        from resolute._option import _NothingType
        assert _NothingType() is Nothing

    def test_some_bool_truthy(self):
        assert bool(Some(1)) is True
        assert bool(Some(0)) is True
        assert bool(Some(None)) is True

    def test_nothing_bool_falsy(self):
        assert bool(Nothing) is False

    def test_some_iteration(self):
        assert list(Some(5)) == [5]

    def test_nothing_iteration_empty(self):
        assert list(Nothing) == []

    def test_option_in_comprehension(self):
        opts = [Some(1), Nothing, Some(3)]
        values = [x for o in opts for x in o]
        assert values == [1, 3]


# ============================================================================
# @safe decorator
# ============================================================================

class TestSafeDecorator:
    def test_safe_wraps_success(self):
        @safe(catch=ValueError)
        def parse(s: str) -> int:
            return int(s)

        assert parse("42") == Ok(42)

    def test_safe_wraps_failure(self):
        @safe(catch=ValueError)
        def parse(s: str) -> int:
            return int(s)

        result = parse("abc")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    def test_safe_reraises_uncaught_exception(self):
        @safe(catch=ValueError)
        def parse(x) -> int:
            return int(x["key"])  # will raise TypeError, not ValueError

        with pytest.raises(TypeError):
            parse("not a dict")

    def test_safe_multiple_exception_types(self):
        @safe(catch=(ValueError, KeyError))
        def lookup(data: dict, key: str) -> int:
            return int(data[key])

        assert lookup({"a": "5"}, "a") == Ok(5)
        assert lookup({}, "a").is_err()                       # KeyError
        assert lookup({"a": "x"}, "a").is_err()               # ValueError

    def test_safe_preserves_function_name(self):
        @safe(catch=ValueError)
        def my_func() -> int:
            return 1

        assert my_func.__name__ == "my_func"

    def test_safe_preserves_docstring(self):
        @safe(catch=ValueError)
        def my_func() -> int:
            """My docstring."""
            return 1

        assert my_func.__doc__ == "My docstring."

    def test_safe_forbidden_keyboard_interrupt(self):
        with pytest.raises(SafeDecoratorError, match="KeyboardInterrupt"):
            @safe(catch=KeyboardInterrupt)
            def f():
                pass

    def test_safe_forbidden_system_exit(self):
        with pytest.raises(SafeDecoratorError, match="SystemExit"):
            @safe(catch=SystemExit)
            def f():
                pass

    def test_safe_forbidden_generator_exit(self):
        with pytest.raises(SafeDecoratorError, match="GeneratorExit"):
            @safe(catch=GeneratorExit)
            def f():
                pass

    def test_safe_broad_exception_warns(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            @safe(catch=Exception)
            def f() -> int:
                return 1

        assert any(issubclass(w.category, RuntimeWarning) for w in caught)

    def test_safe_allow_broad_suppresses_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            @safe(catch=Exception, allow_broad=True)
            def f() -> int:
                return 1

        assert not any(issubclass(w.category, RuntimeWarning) for w in caught)


# ============================================================================
# @safe_async decorator
# ============================================================================

class TestSafeAsyncDecorator:
    def test_safe_async_success(self):
        @safe_async(catch=ValueError)
        async def parse(s: str) -> int:
            return int(s)

        result = asyncio.get_event_loop().run_until_complete(parse("42"))
        assert result == Ok(42)

    def test_safe_async_failure(self):
        @safe_async(catch=ValueError)
        async def parse(s: str) -> int:
            return int(s)

        result = asyncio.get_event_loop().run_until_complete(parse("abc"))
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    def test_safe_async_reraises_uncaught(self):
        @safe_async(catch=ValueError)
        async def f():
            raise TypeError("bug")

        with pytest.raises(TypeError):
            asyncio.get_event_loop().run_until_complete(f())

    def test_safe_async_preserves_name(self):
        @safe_async(catch=RuntimeError)
        async def my_async_func():
            pass

        assert my_async_func.__name__ == "my_async_func"


# ============================================================================
# Combinators
# ============================================================================

class TestCollect:
    def test_all_ok(self):
        assert collect([Ok(1), Ok(2), Ok(3)]) == Ok([1, 2, 3])

    def test_empty(self):
        assert collect([]) == Ok([])

    def test_first_err_short_circuits(self):
        assert collect([Ok(1), Err("bad"), Ok(3)]) == Err("bad")

    def test_stops_at_first_err(self):
        called = []

        def make(x):
            called.append(x)
            return Ok(x)

        collect([make(1), Err("stop"), make(3)])
        assert 3 not in called  # never evaluated — short-circuited


class TestCollectAll:
    def test_all_ok(self):
        assert collect_all([Ok(1), Ok(2), Ok(3)]) == Ok([1, 2, 3])

    def test_all_err(self):
        result = collect_all([Err("a"), Err("b")])
        assert result == Err(["a", "b"])

    def test_mixed(self):
        result = collect_all([Ok(1), Err("a"), Ok(3), Err("b")])
        assert result == Err(["a", "b"])

    def test_empty(self):
        assert collect_all([]) == Ok([])


class TestPartition:
    def test_mixed(self):
        oks, errs = partition([Ok(1), Err("a"), Ok(2), Err("b")])
        assert oks == [1, 2]
        assert errs == ["a", "b"]

    def test_all_ok(self):
        oks, errs = partition([Ok(1), Ok(2)])
        assert oks == [1, 2]
        assert errs == []

    def test_all_err(self):
        oks, errs = partition([Err("x"), Err("y")])
        assert oks == []
        assert errs == ["x", "y"]

    def test_empty(self):
        oks, errs = partition([])
        assert oks == []
        assert errs == []


class TestFlattenResult:
    def test_ok_ok(self):
        assert flatten_result(Ok(Ok(1))) == Ok(1)

    def test_ok_err(self):
        assert flatten_result(Ok(Err("x"))) == Err("x")

    def test_outer_err(self):
        assert flatten_result(Err("outer")) == Err("outer")


class TestSequence:
    def test_all_some(self):
        assert sequence([Some(1), Some(2), Some(3)]) == Some([1, 2, 3])

    def test_contains_nothing(self):
        assert sequence([Some(1), Nothing, Some(3)]) is Nothing

    def test_empty(self):
        assert sequence([]) == Some([])


class TestTranspose:
    def test_some_ok(self):
        assert transpose(Some(Ok(1))) == Ok(Some(1))

    def test_some_err(self):
        assert transpose(Some(Err("x"))) == Err("x")

    def test_nothing(self):
        result = transpose(Nothing)
        assert result.is_ok()
        assert result.unwrap() is Nothing


class TestTransposeResult:
    def test_ok_some(self):
        assert transpose_result(Ok(Some(1))) == Some(Ok(1))

    def test_ok_nothing(self):
        assert transpose_result(Ok(Nothing)) is Nothing

    def test_err(self):
        assert transpose_result(Err("x")) == Some(Err("x"))


# ============================================================================
# Real-world integration patterns
# ============================================================================

class TestIntegrationPatterns:
    def test_validation_pipeline(self):
        """Multiple validations — collect all errors."""

        def validate_name(s: str) -> Result[str, str]:
            s = s.strip()
            if not s:
                return Err("name is required")
            return Ok(s)

        def validate_age(s: str) -> Result[int, str]:
            try:
                age = int(s)
            except ValueError:
                return Err("age must be a number")
            if not (0 < age < 150):
                return Err("age out of range")
            return Ok(age)

        results = [validate_name("  "), validate_age("abc"), validate_age("200")]
        final = collect_all(results)
        assert final.is_err()
        errors = final.unwrap_err()
        assert len(errors) == 3

    def test_railway_chaining(self):
        """Result chain where each step can fail."""

        def parse_int(s: str) -> Result[int, str]:
            try:
                return Ok(int(s))
            except ValueError:
                return Err(f"not an int: {s!r}")

        def ensure_positive(n: int) -> Result[int, str]:
            return Ok(n) if n > 0 else Err(f"not positive: {n}")

        def double(n: int) -> Result[int, str]:
            return Ok(n * 2)

        result = (
            parse_int("5")
            .and_then(ensure_positive)
            .and_then(double)
        )
        assert result == Ok(10)

        result = (
            parse_int("-3")
            .and_then(ensure_positive)
            .and_then(double)
        )
        assert result == Err("not positive: -3")

    def test_option_chaining_user_lookup(self):
        """Nested Option lookups."""
        users = {1: {"name": "Archy", "email_id": 10}}
        emails = {10: "archy@example.com"}

        def get_user(uid: int) -> Option:
            return Some(users[uid]) if uid in users else Nothing

        def get_email(user: dict) -> Option:
            eid = user.get("email_id")
            return Some(emails[eid]) if eid in emails else Nothing

        result = get_user(1).and_then(get_email)
        assert result == Some("archy@example.com")

        result = get_user(99).and_then(get_email)
        assert result is Nothing

    def test_result_in_set(self):
        """Results work correctly as dict keys / set members."""
        cache = {Ok("key"): "stored value"}
        assert cache[Ok("key")] == "stored value"

    def test_bool_in_if_statement(self):
        """Ok is truthy, Err is falsy — clean if-result: usage."""
        result = Ok("data")
        if result:
            value = result.unwrap()
        else:
            value = "default"
        assert value == "data"

        result = Err("failed")
        if result:
            value = result.unwrap()
        else:
            value = "default"
        assert value == "default"
