"""
resolute._decorators
~~~~~~~~~~~~~~~~~~~~~
@safe and @safe_async decorators.

These wrap exception-throwing functions into Result-returning functions,
bridging existing Python code (which uses exceptions) with the Result-based
world.
"""

from __future__ import annotations

import asyncio
import functools
import warnings
from typing import Any, Callable, Tuple, Type, TypeVar, Union, cast

from ._exceptions import SafeDecoratorError
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
    """
    if isinstance(catch, type):
        catch_tuple: Tuple[Type[Exception], ...] = (catch,)
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

        for forbidden in _FORBIDDEN_EXACT:
            if issubclass(exc_type, forbidden):
                raise SafeDecoratorError(
                    f"@safe may not catch {exc_type.__name__} — it is a "
                    "program-termination signal."
                )

        if not issubclass(exc_type, Exception):
            raise SafeDecoratorError(
                f"@safe may only catch Exception subclasses, "
                f"not {exc_type.__name__}"
            )

    if any(exc_type is Exception for exc_type in catch_tuple):
        warnings.warn(
            "@safe(catch=Exception) catches ALL exceptions. "
            "Prefer specifying the exact exception types you expect.",
            RuntimeWarning,
            stacklevel=3,
        )

    return catch_tuple


class safe:
    """
    Decorator that wraps a function's exceptions into a Result type.
    """

    _catch: Tuple[Type[Exception], ...]

    def __init__(
        self,
        func: Callable[..., T] | None = None,
        *,
        catch: ExcTypes = Exception,
        allow_broad: bool = False,
    ) -> None:
        self._func = func
        if allow_broad:
            if isinstance(catch, type):
                self._catch = (catch,)
            else:
                self._catch = tuple(catch)
        else:
            self._catch = _validate_catch(catch)

    def __call__(self, func: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
        target_func = self._func or func
        
        @functools.wraps(target_func)
        def wrapper(*args: Any, **kwargs: Any) -> Result[T, Exception]:
            try:
                return Ok(cast(T, target_func(*args, **kwargs)))
            except self._catch as exc:
                return Err(exc)

        # Update annotations
        original_annotations = getattr(target_func, "__annotations__", {}).copy()
        original_return = original_annotations.get("return")
        if original_return is not None:
             # Dynamically patching Result with a type variable is hard for Mypy.
             # We use Any here to satisfy strict mode while keeping the runtime logic.
            original_annotations["return"] = Any 
        wrapper.__annotations__ = original_annotations
        return wrapper


class safe_async:
    """
    Async version of @safe.
    """

    _catch: Tuple[Type[Exception], ...]

    def __init__(
        self,
        func: Callable[..., Any] | None = None,
        *,
        catch: ExcTypes = Exception,
        allow_broad: bool = False,
    ) -> None:
        self._func = func
        if allow_broad:
            if isinstance(catch, type):
                self._catch = (catch,)
            else:
                self._catch = tuple(catch)
        else:
            self._catch = _validate_catch(catch)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        target_func = self._func or func

        @functools.wraps(target_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Result[Any, Exception]:
            try:
                return Ok(await target_func(*args, **kwargs))
            except self._catch as exc:
                return Err(exc)

        return wrapper
