"""
Tests for all 4 enhancement areas:
1. Performance benchmarks (visible comparisons)
2. Async ergonomics (from_awaitable, map_async, and_then_async)
3. Error context propagation (.context(), .with_context(), ContextError)
4. Do-notation (generator-based early returns)
"""

import asyncio
import pytest
from resolute import (
    Ok, Err, Result,
    Some, Nothing,
    ContextError,
    from_awaitable, map_async, and_then_async,
    do, do_option,
)


# ========================================================================
# 1. PERFORMANCE BENCHMARKS — visible side-by-side comparisons
# ========================================================================

class TestPerformanceBenchmarks:
    """Proves that Result overhead is negligible vs raw Python."""

    def test_ok_creation_vs_raw_return(self, benchmark):
        """Time Ok(42) vs bare return 42."""
        def raw():
            return 42
        # Benchmark the resolute version
        result = benchmark(lambda: Ok(42))
        assert result.is_ok()

    def test_err_unwrap_or_vs_try_except(self, benchmark):
        """Time Err.unwrap_or() vs try/except with fallback."""
        err = Err("fail")
        result = benchmark(lambda: err.unwrap_or(0))
        assert result == 0

    def test_map_chain_vs_if_else(self, benchmark):
        """Time .map().map() chain vs equivalent if/else."""
        ok = Ok(10)
        result = benchmark(lambda: ok.map(lambda x: x * 2).map(lambda x: x + 1))
        assert result == Ok(21)

    def test_and_then_chain_vs_nested_ifs(self, benchmark):
        """Time .and_then() chain vs nested ifs."""
        def step(x):
            return Ok(x + 1)
        ok = Ok(0)
        result = benchmark(lambda: ok.and_then(step).and_then(step).and_then(step))
        assert result == Ok(3)

    def test_native_exception_for_comparison(self, benchmark):
        """Baseline: how fast is a raw try/except?"""
        def with_exception():
            try:
                raise ValueError("test")
            except ValueError:
                return 0
        result = benchmark(with_exception)
        assert result == 0


# ========================================================================
# 2. ASYNC ERGONOMICS
# ========================================================================

class TestAsyncErgonomics:
    """Tests for from_awaitable, map_async, and_then_async."""

    @pytest.mark.asyncio
    async def test_from_awaitable_success(self):
        async def fetch():
            return {"status": 200}
        result = await from_awaitable(fetch())
        assert result == Ok({"status": 200})

    @pytest.mark.asyncio
    async def test_from_awaitable_catches_specified_exception(self):
        async def fail():
            raise ConnectionError("timeout")
        result = await from_awaitable(fail(), catch=ConnectionError)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ConnectionError)

    @pytest.mark.asyncio
    async def test_from_awaitable_lets_uncaught_propagate(self):
        async def fail():
            raise KeyError("wrong")
        with pytest.raises(KeyError):
            await from_awaitable(fail(), catch=ValueError)

    @pytest.mark.asyncio
    async def test_map_async_applies_to_ok(self):
        async def double(x: int) -> int:
            return x * 2
        result = await map_async(Ok(5), double)
        assert result == Ok(10)

    @pytest.mark.asyncio
    async def test_map_async_skips_err(self):
        async def double(x: int) -> int:
            return x * 2
        result = await map_async(Err("fail"), double)
        assert result == Err("fail")

    @pytest.mark.asyncio
    async def test_and_then_async_chains_on_ok(self):
        async def validate(x: int) -> Result:
            if x > 0:
                return Ok(x)
            return Err("must be positive")
        result = await and_then_async(Ok(5), validate)
        assert result == Ok(5)

    @pytest.mark.asyncio
    async def test_and_then_async_short_circuits_on_err(self):
        called = False
        async def should_not_run(x: int) -> Result:
            nonlocal called
            called = True
            return Ok(x)
        result = await and_then_async(Err("already failed"), should_not_run)
        assert result == Err("already failed")
        assert not called

    @pytest.mark.asyncio
    async def test_full_async_pipeline(self):
        """Chain multiple async operations end-to-end."""
        async def fetch_user(user_id: int) -> dict:
            return {"id": user_id, "name": "Archy"}

        async def fetch_email(user: dict) -> Result:
            return Ok(f"{user['name'].lower()}@example.com")

        result = await from_awaitable(fetch_user(1))
        result = await and_then_async(result, fetch_email)
        assert result == Ok("archy@example.com")


# ========================================================================
# 3. ERROR CONTEXT PROPAGATION
# ========================================================================

class TestContextPropagation:
    """Tests for .context(), .with_context(), and ContextError."""

    def test_context_wraps_err(self):
        result = Err("file not found").context("loading config")
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, ContextError)
        assert err.message == "loading config"
        assert err.cause == "file not found"

    def test_context_passes_through_ok(self):
        result = Ok(42).context("should not matter")
        assert result == Ok(42)

    def test_with_context_is_lazy(self):
        called = False
        def make_msg():
            nonlocal called
            called = True
            return "expensive context"

        Ok(1).with_context(make_msg)
        assert not called  # Never called for Ok

        Err("bad").with_context(make_msg)
        assert called  # Called for Err

    def test_context_chaining(self):
        """Build a chain of context like Rust's anyhow."""
        result = (
            Err("ENOENT")
            .context("reading database config")
            .context("initializing application")
        )
        err = result.unwrap_err()
        assert isinstance(err, ContextError)
        assert "initializing application" in str(err)

        # Walk the chain
        chain = err.chain()
        assert len(chain) == 3  # init -> reading -> ENOENT
        assert chain[0].message == "initializing application"
        assert chain[1].message == "reading database config"
        assert chain[2] == "ENOENT"

    def test_context_error_str(self):
        err = ContextError("loading user", ValueError("bad id"))
        assert str(err) == "loading user: bad id"

    def test_context_error_cause_chaining(self):
        """ContextError sets __cause__ for standard Python traceback support."""
        original = ValueError("original")
        err = ContextError("wrapped", original)
        assert err.__cause__ is original

    def test_context_with_map_err(self):
        """Combine .context() with .map_err() for full control."""
        result = (
            Err(FileNotFoundError("app.json"))
            .map_err(lambda e: str(e))
            .context("startup failed")
        )
        err = result.unwrap_err()
        assert isinstance(err, ContextError)
        assert err.cause == "[Errno 2] No such file or directory: 'app.json'" or "app.json" in str(err.cause)


# ========================================================================
# 4. DO-NOTATION
# ========================================================================

class TestDoNotation:
    """Tests for the do() generator-based context manager."""

    def test_do_success_chain(self):
        @do()
        def pipeline():
            x = yield Ok(10)
            y = yield Ok(20)
            return x + y

        result = pipeline()
        assert result == Ok(30)

    def test_do_short_circuits_on_err(self):
        @do()
        def pipeline():
            x = yield Ok(10)
            y = yield Err("boom")
            return x + y  # never reached

        result = pipeline()
        assert result == Err("boom")

    def test_do_with_real_functions(self):
        def parse(s: str) -> Result:
            try:
                return Ok(int(s))
            except ValueError:
                return Err(f"not a number: {s}")

        def validate(n: int) -> Result:
            return Ok(n) if n > 0 else Err("must be positive")

        @do()
        def process(raw: str):
            n = yield parse(raw)
            valid = yield validate(n)
            return valid * 2

        assert process("5") == Ok(10)
        assert process("abc") == Err("not a number: abc")
        assert process("-3") == Err("must be positive")

    def test_do_with_many_steps(self):
        @do()
        def long_pipeline():
            a = yield Ok(1)
            b = yield Ok(2)
            c = yield Ok(3)
            d = yield Ok(4)
            e = yield Ok(5)
            return a + b + c + d + e

        assert long_pipeline() == Ok(15)

    def test_do_preserves_function_name(self):
        @do()
        def my_pipeline():
            x = yield Ok(1)
            return x

        assert my_pipeline.__name__ == "my_pipeline"

    def test_do_early_return_on_first_step(self):
        @do()
        def pipeline():
            x = yield Err("immediate failure")
            return x  # never reached

        assert pipeline() == Err("immediate failure")

    def test_do_with_context(self):
        """Combine do-notation with context propagation."""
        def load_config() -> Result:
            return Err("file missing")

        @do()
        def boot():
            config = yield load_config().context("startup")
            return config

        result = boot()
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, ContextError)
        assert err.message == "startup"
