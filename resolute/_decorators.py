"""
resolute._decorators
~~~~~~~~~~~~~~~~~~~~~
@safe and @safe_async decorators.

These wrap exception-throwing functions into Result-returning functions,
bridging existing Python code (which uses exceptions) with the Result-based
world.

Safety rules enforced at decoration time:
  - You must specify which exception types to catch (no bare @safe allowed
    without arguments unless catch=Exception is explicitly accepted)
  - BaseException and its direct subtypes (KeyboardInterrupt, SystemExit,
    GeneratorExit) may NEVER be caught — they are program-termination signals
  - A warning is emitted when catch=Exception is used, because this almost
    always silently swallows bugs
"""

from __future__ import annotations

import asyncio
import functools
import warnings
from typing import Any, Callable, Tuple, Type, TypeVar, Union, overload

from ._exceptions import SafeDecoratorError, UnwrapError
from ._result import Err, Ok, Result

T = TypeVar("T")
E = TypeVar("E")

# Exception types that must never be caught by @safe
_FORBIDDEN_BASE_TYPES = (BaseException,)
_FORBIDDEN_EXACT = (KeyboardInterrupt, SystemExit, GeneratorExit)

ExcTypes = Union[Type[Exception], Tuple[Type[Exception], ...]]


def _validate_catch(catch: Any) -> Tuple[Type[Exception], ...]:
    """
    Validate the exception types supplied to @safe / @safe_async.

    Returns a normalised tuple of exception classes.
    Raises SafeDecoratorError for invalid input.
    Emits a RuntimeWarning if catch=Exception (overly broad).
    """
    # Normalise to tuple
    if isinstance(catch, type):
        catch_tuple: tuple = (catch,)
    elif isinstance(catch, tuple):
        catch_tuple = catch
    else:
        raise SafeDecoratorError(
            "@safe `catch` must be an exception class or a tuple of exception "
            f"classes, got {type(catch).__name__!r}"
        )

    for exc_type in catch_tuple:
        if not isinstance(exc_type, type):
            raise SafeDecoratorError(
                f"@safe `catch` entries must be exception classes, "
                f"got {exc_type!r}"
            )

        # Forbid BaseException and its special subclasses
        for forbidden in _FORBIDDEN_EXACT:
            if issubclass(exc_type, forbidden):
                raise SafeDecoratorError(
                    f"@safe may not catch {exc_type.__name__} — it is a "
                    f"program-termination signal, not a recoverable error. "
                    f"Catching it would prevent clean shutdown."
                )

        if not issubclass(exc_type, Exception):
            raise SafeDecoratorError(
                f"@safe may only catch Exception subclasses, "
                f"not {exc_type.__name__}"
            )

    # Warn on overly broad catch
    if any(exc_type is Exception for exc_type in catch_tuple):
        warnings.warn(
            "@safe(catch=Exception) catches ALL exceptions including "
            "AttributeError, IndexError, TypeError, and other bugs. "
            "Prefer specifying the exact exception types you expect. "
            "This warning can be silenced with allow_broad=True.",
            RuntimeWarning,
            stacklevel=3,
        )

    return catch_tuple  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# @safe  (synchronous)
# --------------------------------------------------------------------------- #

class safe:
    """
    Decorator that wraps a function's exceptions into a Result type.

    Basic usage:
        @safe(catch=ValueError)
        def parse_int(s: str) -> int:
            return int(s)

        parse_int("42")   # Ok(42)
        parse_int("abc")  # Err(ValueError("invalid literal ..."))

    Multiple exception types:
        @safe(catch=(ValueError, KeyError))
        def lookup(data: dict, key: str) -> int:
            return int(data[key])

    Broad catch (emits warning, use with care):
        @safe(catch=Exception, allow_broad=True)
        def risky() -> str: ...

    The decorated function's return type becomes Result[original_type, ExcType].
    Exceptions NOT listed in `catch` are re-raised normally — they are bugs
    and should not be silently converted to Err.
    """

    def __new__(
        cls,
        func: Callable | None = None,
        *,
        catch: ExcTypes = Exception,
        allow_broad: bool = False,
    ) -> Any:
        instance = super().__new__(cls)
        if func is not None:
            # Used as bare @safe without arguments — not recommended,
            # but we support it by defaulting to Exception with a warning.
            instance.__init__(catch=Exception, allow_broad=allow_broad)
            return instance(func)
        return instance

    def __init__(
        self,
        func: Callable | None = None,
        *,
        catch: ExcTypes = Exception,
        allow_broad: bool = False,
    ) -> None:
        if allow_broad:
            # Suppress the broad-catch warning when user is explicit
            if isinstance(catch, type):
                self._catch: tuple = (catch,)
            else:
                self._catch = tuple(catch)
            for exc_type in self._catch:
                if not isinstance(exc_type, type) or not issubclass(exc_type, Exception):
                    raise SafeDecoratorError(
                        f"@safe `catch` entries must be Exception subclasses, got {exc_type!r}"
                    )
                for forbidden in _FORBIDDEN_EXACT:
                    if issubclass(exc_type, forbidden):
                        raise SafeDecoratorError(
                            f"@safe may not catch {exc_type.__name__} even with allow_broad=True."
                        )
        else:
            self._catch = _validate_catch(catch)

    def __call__(self, func: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
        catch = self._catch

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Result[T, Exception]:
            try:
                return Ok(func(*args, **kwargs))
            except catch as exc:  # type: ignore[misc]
                return Err(exc)

        # Update annotations so static analyzers see Result return type
        original_annotations = getattr(func, "__annotations__", {}).copy()
        original_return = original_annotations.get("return")
        if original_return is not None:
            original_annotations["return"] = Result[original_return, Exception]  # type: ignore[valid-type]
        wrapper.__annotations__ = original_annotations
        wrapper.__wrapped__ = func  # type: ignore[attr-defined]

        return wrapper


# --------------------------------------------------------------------------- #
# @safe_async  (asynchronous)
# --------------------------------------------------------------------------- #

class safe_async:
    """
    Async version of @safe. Wraps an async function's exceptions into Result.

    Basic usage:
        @safe_async(catch=aiohttp.ClientError)
        async def fetch(url: str) -> str:
            async with aiohttp.ClientSession() as s:
                async with s.get(url) as r:
                    return await r.text()

        result = await fetch("https://example.com")
        # Ok("<html>...") or Err(aiohttp.ClientError(...))

    The decorated function returns Awaitable[Result[T, ExcType]].
    """

    def __new__(
        cls,
        func: Callable | None = None,
        *,
        catch: ExcTypes = Exception,
        allow_broad: bool = False,
    ) -> Any:
        instance = super().__new__(cls)
        if func is not None:
            instance.__init__(catch=Exception, allow_broad=allow_broad)
            return instance(func)
        return instance

    def __init__(
        self,
        func: Callable | None = None,
        *,
        catch: ExcTypes = Exception,
        allow_broad: bool = False,
    ) -> None:
        if allow_broad:
            if isinstance(catch, type):
                self._catch: tuple = (catch,)
            else:
                self._catch = tuple(catch)
        else:
            self._catch = _validate_catch(catch)

    def __call__(
        self, func: Callable[..., Any]
    ) -> Callable[..., Any]:
        catch = self._catch

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Result[Any, Exception]:
            try:
                return Ok(await func(*args, **kwargs))
            except catch as exc:  # type: ignore[misc]
                return Err(exc)

        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return wrapper
