"""
Tests for bugs found in the deep codebase audit.
Covers Bugs 2, 3, 4, 5, and 6 from the implementation plan.
"""
import pytest
import asyncio
from resolute import (
    Ok, Err, Result, Some, Nothing, Option,
    do, do_option, safe, safe_async, from_awaitable,
)
from resolute._exceptions import SafeDecoratorError


# ───────────────────────────────────────────────────────────────────────
# Bug 2: @do_option must convert yielded Err → Nothing
# ───────────────────────────────────────────────────────────────────────

class TestDoOptionErrConversion:

    def test_yield_err_returns_nothing(self):
        """Yielding an Err inside @do_option should return Nothing, not leak Err."""
        @do_option()
        def pipeline():
            x = yield Some(10)
            y = yield Err("boom")   # should short-circuit as Nothing
            return x + y

        result = pipeline()
        assert result == Nothing
        assert isinstance(result, Option)

    def test_yield_ok_works_normally(self):
        """Yielding an Ok inside @do_option should unwrap the value."""
        @do_option()
        def pipeline():
            x = yield Some(10)
            y = yield Ok(20)     # Ok can be yielded in Option context
            return x + y

        result = pipeline()
        assert result == Some(30)


# ───────────────────────────────────────────────────────────────────────
# Bug 3: _finalize_option must handle explicit Result returns
# ───────────────────────────────────────────────────────────────────────

class TestFinalizeOptionResultReturns:

    def test_return_err_becomes_nothing(self):
        """return Err('x') inside @do_option should become Nothing."""
        @do_option()
        def pipeline(value: int):
            if value < 0:
                return Err("negative")  # should NOT become Some(Err(...))
            return value

        result = pipeline(-1)
        assert result == Nothing

    def test_return_ok_unwraps(self):
        """return Ok(42) inside @do_option should become Some(42)."""
        @do_option()
        def pipeline():
            return Ok(42)

        result = pipeline()
        assert result == Some(42)


# ───────────────────────────────────────────────────────────────────────
# Bug 4: Option.transpose() must use isinstance, not duck-typing
# ───────────────────────────────────────────────────────────────────────

class TestTransposeTypeCheck:

    def test_transpose_ok(self):
        assert Some(Ok(1)).transpose() == Ok(Some(1))

    def test_transpose_err(self):
        assert Some(Err("x")).transpose() == Err("x")

    def test_transpose_nothing(self):
        assert Nothing.transpose() == Ok(Nothing)

    def test_transpose_non_result_with_is_ok_attr(self):
        """Objects with an 'is_ok' attribute should NOT be treated as Result."""
        class FakeResult:
            is_ok = True
            def unwrap(self):
                return 42

        # With isinstance check, this should fallback to Ok(Some(FakeResult))
        result = Some(FakeResult()).transpose()
        assert isinstance(result, Ok)
        inner = result.unwrap()
        assert isinstance(inner, Some)
        assert isinstance(inner.unwrap(), FakeResult)


# ───────────────────────────────────────────────────────────────────────
# Bug 5: allow_broad=True must still block fatal signals
# ───────────────────────────────────────────────────────────────────────

class TestAllowBroadSafety:

    def test_allow_broad_blocks_keyboard_interrupt(self):
        """allow_broad=True should still reject KeyboardInterrupt."""
        with pytest.raises(SafeDecoratorError, match="program-termination signal"):
            @safe(catch=KeyboardInterrupt, allow_broad=True)
            def bad():
                pass

    def test_allow_broad_blocks_system_exit(self):
        """allow_broad=True should still reject SystemExit."""
        with pytest.raises(SafeDecoratorError, match="program-termination signal"):
            @safe(catch=SystemExit, allow_broad=True)
            def bad():
                pass

    def test_allow_broad_allows_exception(self):
        """allow_broad=True should allow Exception without warning."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            # This should NOT raise a RuntimeWarning
            @safe(catch=Exception, allow_broad=True)
            def good(x):
                return int(x)

            assert good("42") == Ok(42)
            assert good("abc").is_err()


# ───────────────────────────────────────────────────────────────────────
# Bug 6: from_awaitable should not warn on every call
# ───────────────────────────────────────────────────────────────────────

class TestFromAwaitableNoSpam:

    @pytest.mark.asyncio
    async def test_no_warning_on_default_catch(self):
        """from_awaitable() with default catch should not emit RuntimeWarning."""
        import warnings

        async def ok_coro():
            return 42

        with warnings.catch_warnings():
            warnings.simplefilter("error")  # any warning becomes an error
            result = await from_awaitable(ok_coro())
            assert result == Ok(42)
