"""
explicit_result._decorators
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


def _validate_catch(catch: Any, *, warn_broad: bool = True) -> Tuple[Type[Exception], ...]:
    """
    Validate the exception types supplied to @safe / @safe_async.

    Args:
        catch: Exception class or tuple of exception classes.
        warn_broad: If True, warn when catching bare Exception.
                    Set to False when allow_broad=True.
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

    if warn_broad and any(exc_type is Exception for exc_type in catch_tuple):
        warnings.warn(
            "@safe(catch=Exception) catches ALL exceptions. "
            "Prefer specifying the exact exception types you expect.",
            RuntimeWarning,
            stacklevel=3,
        )

    return catch_tuple


def safe(
    func: Callable[..., T] | None = None,
    *,
    catch: ExcTypes = Exception,
    allow_broad: bool = False,
) -> Any:
    """
    Decorator that wraps a function's exceptions into a Result type.
    """
    if func is not None:
        if not callable(func) or (isinstance(func, type) and issubclass(func, BaseException)):
            raise TypeError("The @safe decorator must be applied to a callable. Did you mean @safe(catch=SomeException)?")

    if allow_broad:
        _catch = _validate_catch(catch, warn_broad=False)
    else:
        _catch = _validate_catch(catch)

    def decorator(f: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Result[T, Exception]:
            try:
                return Ok(f(*args, **kwargs))
            except _catch as exc:
                return Err(exc)

        # Update annotations
        original_annotations = getattr(f, "__annotations__", {}).copy()
        if original_annotations.get("return") is not None:
             # Dynamically patching Result with a type variable is hard for Mypy.
             # We use Any here to satisfy strict mode while keeping the runtime logic.
            original_annotations["return"] = Any 
        wrapper.__annotations__ = original_annotations
        return wrapper

    if func is not None:
        return decorator(cast(Callable[..., T], func))
    return decorator


def safe_async(
    func: Callable[..., Any] | None = None,
    *,
    catch: ExcTypes = Exception,
    allow_broad: bool = False,
) -> Any:
    """
    Async version of @safe.
    """
    if func is not None:
        if not callable(func) or (isinstance(func, type) and issubclass(func, BaseException)):
            raise TypeError("The @safe_async decorator must be applied to a callable. Did you mean @safe_async(catch=SomeException)?")

    if allow_broad:
        _catch = _validate_catch(catch, warn_broad=False)
    else:
        _catch = _validate_catch(catch)

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(f)
        async def wrapper(*args: Any, **kwargs: Any) -> Result[Any, Exception]:
            try:
                return Ok(await f(*args, **kwargs))
            except _catch as exc:
                return Err(exc)

        # Update annotations
        original_annotations = getattr(f, "__annotations__", {}).copy()
        if original_annotations.get("return") is not None:
            original_annotations["return"] = Any 
        wrapper.__annotations__ = original_annotations
        return wrapper

    if func is not None:
        return decorator(cast(Callable[..., Any], func))
    return decorator
