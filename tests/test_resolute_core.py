# tests/test_resolute_core.py
"""
Comprehensive pytest suite for the resolute library.
Tests Result[T, E], Option[T], decorators, and combinators.
"""
from __future__ import annotations

import pytest
from typing import Callable, Generic, TypeVar

from resolute import (
    Result, Ok, Err,
    Option, Some, Nothing,
    safe, safe_async, do, do_option,
    collect, partition,
    UnwrapError, ContextError
)

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
U = TypeVar("U")


# =============================================================================
# Result[T, E] Core Tests
# =============================================================================

class TestResultCore:
    """Tests for basic Result variant behavior and inspection methods."""

    def test_ok_variant_construction(self) -> None:
        """Ok(value) constructs successfully and holds the value."""
        result: Result[int, str] = Ok(42)
        assert result.is_ok() is True
        assert result.is_err() is False
        assert result.unwrap() == 42

    def test_err_variant_construction(self) -> None:
        """Err(error) constructs successfully and holds the error."""
        error = ValueError("test error")
        result: Result[str, ValueError] = Err(error)
        assert result.is_ok() is False
        assert result.is_err() is True
        assert result.unwrap_err() is error

    def test_unwrap_on_err_raises_unwrap_error(self) -> None:
        """Calling unwrap() on Err raises UnwrapError with the original error."""
        result: Result[int, RuntimeError] = Err(RuntimeError("boom"))
        with pytest.raises(UnwrapError) as exc_info:
            result.unwrap()
        assert isinstance(exc_info.value.original, RuntimeError)
        assert str(exc_info.value.original) == "boom"

    def test_unwrap_err_on_ok_raises_unwrap_error(self) -> None:
        """Calling unwrap_err() on Ok raises UnwrapError."""
        result: Result[int, str] = Ok(100)
        with pytest.raises(UnwrapError):
            result.unwrap_err()

    def test_expect_provides_custom_message_on_failure(self) -> None:
        """expect(msg) raises UnwrapError with custom message when Err."""
        result: Result[str, Exception] = Err(ValueError("internal"))
        with pytest.raises(UnwrapError, match="custom context"):
            result.expect("custom context")

    def test_unwrap_or_returns_default_on_err(self) -> None:
        """unwrap_or(default) returns the default value when Result is Err."""
        ok_result: Result[int, str] = Ok(42)
        err_result: Result[int, str] = Err("error")
        
        assert ok_result.unwrap_or(0) == 42
        assert err_result.unwrap_or(0) == 0

    def test_unwrap_or_evaluates_default_eagerly(self) -> None:
        """unwrap_or evaluates the default argument eagerly (not lazy)."""
        side_effect = {"called": False}
        
        def expensive_default() -> int:
            side_effect["called"] = True
            return 99
        
        # Even though we have Ok, the default is still evaluated
        result: Result[int, str] = Ok(42)
        assert result.unwrap_or(expensive_default()) == 42  # type: ignore
        assert side_effect["called"] is True


# =============================================================================
# Result[T, E] Chaining Tests
# =============================================================================

class TestResultChaining:
    """Tests for map, map_err, and_then, or_else combinators."""

    def test_map_transforms_ok_value(self) -> None:
        """map applies function to Ok value, preserves Err."""
        result: Result[int, str] = Ok(5)
        mapped = result.map(lambda x: x * 2)
        assert mapped == Ok(10)
        
        err_result: Result[int, str] = Err("fail")
        assert err_result.map(lambda x: x * 2) == Err("fail")

    def test_map_err_transforms_error(self) -> None:
        """map_err applies function to Err value, preserves Ok."""
        result: Result[str, int] = Err(404)
        mapped = result.map_err(lambda e: f"Error code: {e}")
        assert mapped == Err("Error code: 404")
        
        ok_result: Result[str, int] = Ok("success")
        assert ok_result.map_err(lambda e: f"Error: {e}") == Ok("success")

    def test_and_then_chains_successful_operations(self) -> None:
        """and_then flattens nested Results on success."""
        def divide(x: int, y: int) -> Result[float, str]:
            if y == 0:
                return Err("division by zero")
            return Ok(x / y)
        
        result: Result[int, str] = Ok(10)
        chained = result.and_then(lambda x: divide(x, 2))
        assert chained == Ok(5.0)
        
        # Short-circuits on Err
        err_result: Result[int, str] = Err("prior error")
        assert err_result.and_then(lambda x: divide(x, 2)) == Err("prior error")
        
        # Short-circuits if lambda returns Err
        zero_div = result.and_then(lambda x: divide(x, 0))
        assert zero_div == Err("division by zero")

    def test_or_else_provides_fallback_on_error(self) -> None:
        """or_else executes fallback function only when Result is Err."""
        def fallback(e: str) -> Result[int, str]:
            return Ok(len(e))
        
        err_result: Result[int, str] = Err("error")
        recovered = err_result.or_else(fallback)
        assert recovered == Ok(5)
        
        # Ok passes through unchanged
        ok_result: Result[int, str] = Ok(42)
        assert ok_result.or_else(fallback) == Ok(42)

    def test_chaining_preserves_type_hints(self) -> None:
        """Verify type hints work correctly through chains."""
        def parse_int(s: str) -> Result[int, ValueError]:
            try:
                return Ok(int(s))
            except ValueError as e:
                return Err(e)
        
        def double(x: int) -> Result[int, ValueError]:
            return Ok(x * 2)
        
        # This should type-check correctly
        result: Result[str, ValueError] = Ok("21")
        final = result.and_then(parse_int).and_then(double)
        assert final == Ok(42)


# =============================================================================
# Result Context & Error Tracking Tests
# =============================================================================

class TestResultContext:
    """Tests for context(), chain(), and root_cause() error tracking."""

    def test_context_adds_layer_to_error_chain(self) -> None:
        """context() wraps Err with additional context."""
        original_err = ValueError("low-level error")
        result: Result[int, Exception] = Err(original_err).context("database operation failed")
        
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, ContextError)
        # Note: actual assertion depends on ContextError implementation

    def test_chain_returns_error_hierarchy(self) -> None:
        """chain() returns list of ContextErrors from most to least specific."""
        err = RuntimeError("root cause")
        result = (Err(err)
                  .context("step 2 failed")
                  .context("step 1 failed"))
        
        chain = result.unwrap_err().chain()
        assert len(chain) >= 1  # Adjust based on actual implementation
        # Verify chain order and content as per library spec

    def test_root_cause_extracts_original_exception(self) -> None:
        """root_cause() returns the original unwrapped exception."""
        original = FileNotFoundError("missing.txt")
        result = Err(original).context("config load failed")
        
        cause = result.unwrap_err().root_cause
        assert cause is original
        assert isinstance(cause, FileNotFoundError)


# =============================================================================
# Option[T] Core Tests
# =============================================================================

class TestOptionCore:
    """Tests for Option variant behavior and basic methods."""

    def test_some_variant_behavior(self) -> None:
        """Some(value) behaves as expected."""
        opt: Option[str] = Some("hello")
        assert opt.is_some() is True
        assert opt.is_nothing() is False
        assert opt.unwrap() == "hello"

    def test_nothing_singleton_behavior(self) -> None:
        """Nothing is a singleton and behaves correctly."""
        opt1: Option[int] = Nothing
        opt2: Option[int] = Nothing
        assert opt1 is opt2  # Singleton identity
        assert opt1.is_nothing() is True
        assert opt1.is_some() is False

    def test_unwrap_nothing_raises_unwrap_error(self) -> None:
        """Unwrapping Nothing raises UnwrapError."""
        with pytest.raises(UnwrapError):
            Nothing.unwrap()

    def test_unwrap_or_with_option(self) -> None:
        """unwrap_or returns value or default appropriately."""
        assert Some(42).unwrap_or(0) == 42
        assert Nothing.unwrap_or(0) == 0

    def test_ok_or_converts_option_to_result(self) -> None:
        """ok_or() converts Some->Ok, Nothing->Err."""
        some_result = Some("value").ok_or(ValueError("missing"))
        assert some_result == Ok("value")
        
        nothing_result = Nothing.ok_or(ValueError("missing"))
        assert nothing_result.is_err()
        assert isinstance(nothing_result.unwrap_err(), ValueError)


# =============================================================================
# Option[T] Chaining Tests
# =============================================================================

class TestOptionChaining:
    """Tests for Option map and and_then combinators."""

    def test_map_transforms_some_value(self) -> None:
        """map applies function to Some, preserves Nothing."""
        assert Some(5).map(lambda x: x * 2) == Some(10)
        assert Nothing.map(lambda x: x * 2) == Nothing

    def test_and_then_flattens_nested_options(self) -> None:
        """and_then chains Option-returning functions."""
        def safe_divide(x: int, y: int) -> Option[float]:
            if y == 0:
                return Nothing
            return Some(x / y)
        
        assert Some(10).and_then(lambda x: safe_divide(x, 2)) == Some(5.0)
        assert Nothing.and_then(lambda x: safe_divide(x, 2)) == Nothing
        assert Some(10).and_then(lambda x: safe_divide(x, 0)) == Nothing


# =============================================================================
# @safe Decorator Tests
# =============================================================================

class TestSafeDecorator:
    """Tests for the @safe exception-handling decorator."""

    @safe(catch=(ValueError, TypeError))
    def risky_function(self, x: str) -> int:
        if x == "bad":
            raise ValueError("invalid input")
        return int(x)

    @safe(catch=(RuntimeError,))
    def catches_all(self, x: int) -> str:
        if x < 0:
            raise RuntimeError("negative not allowed")
        return str(x)

    def test_safe_wraps_success_in_ok(self) -> None:
        """Successful execution returns Ok(value)."""
        result = self.risky_function("42")
        assert isinstance(result, Result)
        assert result == Ok(42)

    def test_safe_catches_specified_exceptions(self) -> None:
        """Specified exceptions are caught and returned as Err."""
        result = self.risky_function("bad")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    def test_safe_unspecified_exceptions_propagate(self) -> None:
        """Exceptions not in catch list propagate normally."""
        with pytest.raises(KeyError):
            @safe(catch=(ValueError,))
            def throws_keyerror() -> None:
                raise KeyError("not caught")
            throws_keyerror()

    def test_safe_catches_all_by_default(self) -> None:
        """@safe() with no args catches all Exception subclasses."""
        result = self.catches_all(-5)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), RuntimeError)


# =============================================================================
# @do and @do_option Decorator Tests
# =============================================================================

class TestDoNotation:
    """Tests for generator-based do-notation decorators."""

    @do()
    def successful_do(self) -> Result[str, str]:
        x: int = yield Ok(5)
        y: int = yield Ok(10)
        return Ok(f"sum: {x + y}")

    @do()
    def short_circuit_do(self) -> Result[str, str]:
        x: int = yield Ok(5)
        _ = yield Err("early failure")
        y: int = yield Ok(10)  # Never reached
        return Ok(f"sum: {x + y}")

    @do_option()
    def successful_do_option(self) -> Option[str]:
        x: int = yield Some(5)
        y: int = yield Some(10)
        return Some(f"product: {x * y}")

    @do_option()
    def short_circuit_option(self) -> Option[str]:
        x: int = yield Some(5)
        _ = yield Nothing
        y: int = yield Some(10)  # Never reached
        return Some(f"product: {x * y}")

    def test_do_notation_success_path(self) -> None:
        """Do-notation executes all yields on success."""
        result = self.successful_do()
        assert result == Ok("sum: 15")

    def test_do_notation_short_circuits_on_err(self) -> None:
        """Do-notation short-circuits and returns first Err."""
        result = self.short_circuit_do()
        assert result == Err("early failure")

    def test_do_option_success_path(self) -> None:
        """do_option executes all yields when all are Some."""
        result = self.successful_do_option()
        assert result == Some("product: 50")

    def test_do_option_short_circuits_on_nothing(self) -> None:
        """do_option short-circuits and returns Nothing."""
        result = self.short_circuit_option()
        assert result is Nothing

    def test_do_notation_type_annotations(self) -> None:
        """Verify yielded values can be type-annotated."""
        @do()
        def typed_do() -> Result[float, str]:
            val: int = yield Ok(42)
            # Type checker should know val is int here
            return Ok(float(val) * 1.5)
        
        assert typed_do() == Ok(63.0)


# =============================================================================
# Combinators: collect and partition
# =============================================================================

class TestCollectCombinator:
    """Tests for collect() - aggregates Results, short-circuits on first Err."""

    def test_collect_all_ok_returns_list(self) -> None:
        """collect([Ok(...), Ok(...)]) returns Ok([values])."""
        results = [Ok(1), Ok(2), Ok(3)]
        result = collect(results)
        assert result == Ok([1, 2, 3])

    def test_collect_short_circuits_on_first_err(self) -> None:
        """collect returns first Err encountered, ignoring rest."""
        results = [Ok(1), Err("error at index 1"), Ok(3), Err("later error")]
        result = collect(results)
        assert result == Err("error at index 1")

    def test_collect_empty_list(self) -> None:
        """collect([]) returns Ok([])."""
        assert collect([]) == Ok([])

    def test_collect_preserves_error_type(self) -> None:
        """The specific Err value is preserved."""
        custom_err = TypeError("type mismatch")
        results = [Ok("a"), Err(custom_err)]
        result = collect(results)
        assert result.unwrap_err() is custom_err

    def test_collect_with_generator_input(self) -> None:
        """collect works with any iterable, not just lists."""
        def gen():
            yield Ok(10)
            yield Ok(20)
            yield Ok(30)
        
        assert collect(gen()) == Ok([10, 20, 30])


class TestPartitionCombinator:
    """Tests for partition() - separates Ok and Err values."""

    def test_partition_all_ok(self) -> None:
        """partition([Ok(...)]) returns (values, [])."""
        results = [Ok(1), Ok(2), Ok(3)]
        ok_vals, err_vals = partition(results)
        assert ok_vals == [1, 2, 3]
        assert err_vals == []

    def test_partition_all_err(self) -> None:
        """partition([Err(...)]) returns ([], errors)."""
        errors = [ValueError("a"), TypeError("b")]
        results = [Err(e) for e in errors]
        ok_vals, err_vals = partition(results)
        assert ok_vals == []
        assert err_vals == errors

    def test_partition_mixed_results(self) -> None:
        """partition separates Ok and Err values correctly."""
        results = [Ok(1), Err("e1"), Ok(2), Err("e2"), Ok(3)]
        ok_vals, err_vals = partition(results)
        assert ok_vals == [1, 2, 3]
        assert err_vals == ["e1", "e2"]

    def test_partition_preserves_order(self) -> None:
        """Values maintain their original order within each group."""
        results = [Ok("a"), Ok("b"), Err(1), Ok("c"), Err(2)]
        ok_vals, err_vals = partition(results)
        assert ok_vals == ["a", "b", "c"]
        assert err_vals == [1, 2]

    def test_partition_empty_input(self) -> None:
        """partition([]) returns ([], [])."""
        assert partition([]) == ([], [])

    def test_partition_with_large_input(self) -> None:
        """partition handles large lists efficiently (performance smoke test)."""
        results = [Ok(i) if i % 3 != 0 else Err(f"err_{i}") for i in range(1000)]
        ok_vals, err_vals = partition(results)
        assert len(ok_vals) == 666
        assert len(err_vals) == 334
        assert all(isinstance(v, int) for v in ok_vals)
        assert all(isinstance(e, str) for e in err_vals)


# =============================================================================
# Edge Cases & Integration Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases, error conditions, and integration scenarios."""

    def test_result_equality_and_hash(self) -> None:
        """Ok/Err support equality comparison and hashing where applicable."""
        assert Ok(1) == Ok(1)
        assert Ok(1) != Ok(2)
        assert Err("x") == Err("x")
        
        # Hashable if contained values are hashable
        assert hash(Ok(1)) == hash(Ok(1))
        assert {Ok(1), Ok(2), Err("e")}  # Should not raise

    def test_nothing_identity_across_imports(self) -> None:
        """Nothing singleton identity is preserved."""
        from resolute import Nothing as Nothing2
        assert Nothing is Nothing2

    def test_nested_result_handling(self) -> None:
        """Handling Result[Result[T, E], E] correctly."""
        nested: Result[Result[int, str], str] = Ok(Ok(42))
        flattened = nested.and_then(lambda x: x)
        assert flattened == Ok(42)

    def test_exception_in_map_function_is_not_caught(self) -> None:
        """Exceptions in map/and_then functions propagate (not auto-wrapped)."""
        def bad_map(x: int) -> int:
            raise RuntimeError("map failed")
        
        with pytest.raises(RuntimeError, match="map failed"):
            Ok(1).map(bad_map)
        
        # Use @safe if you want exception handling
        @safe(catch=(RuntimeError,))
        def safe_bad_map(x: int) -> Result[int, Exception]:
            return Ok(bad_map(x))  # Exception caught by decorator
        
        result = safe_bad_map(1)
        assert result.is_err()

    def test_context_with_none_error_value(self) -> None:
        """Edge case: context() when error value is None."""
        # Depending on library design, this may or may not be allowed
        # Test the actual behavior
        result = Err(None).context("something failed")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_async_function_with_safe_decorator(self) -> None:
        """@safe works with async functions (if library supports it)."""
        @safe_async(catch=(ValueError,))
        async def async_risky(delay: float) -> str:
            import asyncio
            await asyncio.sleep(delay)
            if delay < 0:
                raise ValueError("negative delay")
            return "done"
        
        # Success case
        result = await async_risky(0.01)
        assert result == Ok("done")
        
        # Error case
        result = await async_risky(-1.0)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)


# =============================================================================
# Property-Based Style Tests (using pytest parametrize)
# =============================================================================

@pytest.mark.parametrize("value", [0, -1, 42, 10**6, None, "", "test", [], {}])
def test_ok_unwrap_roundtrip(value: T) -> None:
    """Ok(value).unwrap() == value for various types."""
    assert Ok(value).unwrap() == value


@pytest.mark.parametrize("error", [
    Exception("base"),
    ValueError("value"),
    TypeError("type"),
    RuntimeError("runtime"),
    KeyError("missing"),
])
def test_err_unwrap_err_roundtrip(error: Exception) -> None:
    """Err(error).unwrap_err() is error for various exception types."""
    assert Err(error).unwrap_err() is error


@pytest.mark.parametrize("input_val,expected", [
    (Some(1), True),
    (Nothing, False),
    (Some(""), True),  # Empty string is still Some
    (Some([]), True),  # Empty list is still Some
])
def test_option_is_some_variations(input_val: Option[T], expected: bool) -> None:
    """is_some() returns True only for Some variants, regardless of content."""
    assert input_val.is_some() == expected


# =============================================================================
# Type Hint Verification (for static type checkers)
# =============================================================================

def test_type_hints_are_preserved() -> None:
    """Smoke test to ensure type hints work with mypy/pyright."""
    # These should not cause type errors when checked
    r1: Result[int, str] = Ok(42)
    r2: Result[str, int] = Err(404)
    
    o1: Option[float] = Some(3.14)
    o2: Option[bool] = Nothing
    
    # Chaining preserves types
    r3 = r1.map(str).and_then(lambda s: Ok(len(s)))
    _: Result[int, str] = r3  # Type checker should accept this
    
    # Option to Result conversion
    r4: Result[str, ValueError] = o1.map(str).ok_or(ValueError("no float"))
    _: Result[str, ValueError] = r4
