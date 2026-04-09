"""
resolute._do
~~~~~~~~~~~~~~
Do-notation for Result and Option — Pythonic early returns.

Instead of deeply nested .and_then() chains:

    result = (
        find_user(1)
        .and_then(lambda u: get_profile(u))
        .and_then(lambda p: validate_email(p.email))
        .map(lambda e: e.lower())
    )

Write this:

    @do()
    def process():
        user = yield find_user(1)
        profile = yield get_profile(user)
        email = yield validate_email(profile.email)
        return email.lower()

    result = process()  # Ok("archy@example.com") or first Err

You can also ``return Err(...)`` explicitly for conditional exits:

    @do()
    def check(value: int):
        if value < 0:
            return Err("negative")  # NOT double-wrapped
        x = yield validate(value)
        return x * 2

For Option types, use ``@do_option()``:

    @do_option()
    def lookup():
        user = yield find_user_opt(1)     # unwraps Some, exits on Nothing
        email = yield get_email_opt(user)
        return email.lower()

    lookup()  # Some("archy@...") or Nothing
"""

from __future__ import annotations

import functools
from types import GeneratorType
from typing import (
    Any,
    Callable,
    Generator,
    TypeVar,
    Union,
)

from ._result import Ok, Err, Result
from ._option import Some, Option, _Nothing, _NothingType

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


def do() -> Callable[
    [Callable[..., Generator[Result[Any, E], Any, T]]],
    Callable[..., Result[T, E]],
]:
    """
    Decorator that enables generator-based do-notation for Results.

    TYPE CHECKER NOTE:
    Always annotate the return type explicitly — pyright and mypy cannot
    infer it from the generator body.

    Yield a Result to "unwrap" it — if it's Ok, the value is sent back.
    If it's Err, execution stops and that Err is returned immediately.

    The final ``return`` value is wrapped in Ok() — unless it is already
    a Result, in which case it is returned as-is (no double-wrapping).

    Usage::

        @do()
        def pipeline():
            x = yield Ok(10)
            y = yield Ok(20)
            return x + y

        pipeline()  # Ok(30)

        @do()
        def failing():
            x = yield Ok(10)
            y = yield Err("boom")   # stops here
            return x + y            # never reached

        failing()  # Err("boom")

        @do()
        def conditional(value: int):
            if value < 0:
                return Err("negative")  # explicit Err return — not double-wrapped
            return value

        conditional(-1)  # Err("negative")
        conditional(5)   # Ok(5)
    """
    def decorator(
        gen_func: Callable[..., Generator[Result[Any, E], Any, T]],
    ) -> Callable[..., Result[T, E]]:

        @functools.wraps(gen_func)
        def wrapper(*args: Any, **kwargs: Any) -> Result[T, E]:
            gen = gen_func(*args, **kwargs)
            # If the function returned early (no yield), it's not a generator
            if not isinstance(gen, GeneratorType):
                return _finalize_result(gen)
            try:
                yielded = next(gen)
                while True:
                    # Guard: ensure the yielded value is a Result or Option
                    if not hasattr(yielded, "_is_monadic") or not yielded._is_monadic:
                        raise TypeError(
                            f"Value yielded in @do must be Result or Option, got {type(yielded).__name__}. "
                            "Did you mean to use '.unwrap()' or yield a valid container?"
                        )

                    if isinstance(yielded, Err):
                        return yielded
                    
                    if isinstance(yielded, _NothingType):
                        return yielded  # type: ignore[return-value]
                    
                    # Send the unwrapped Ok value back
                    try:
                        yielded = gen.send(yielded.unwrap())
                    except StopIteration as stop:
                        return _finalize_result(stop.value)
            except StopIteration as stop:
                return _finalize_result(stop.value)

        return wrapper

    return decorator


def _finalize_result(return_value: Any) -> Result[Any, Any]:
    """
    Wrap a generator's return value in Ok — unless it is already a Result.

    This prevents the double-wrap problem where ``return Err("x")`` inside
    a @do() generator would become ``Ok(Err("x"))`` instead of ``Err("x")``.
    """
    if isinstance(return_value, (Ok, Err)):
        return return_value
    return Ok(return_value)


# --------------------------------------------------------------------------- #
# do_option — same pattern, for Option[T]
# --------------------------------------------------------------------------- #

def do_option() -> Callable[
    [Callable[..., Generator[Option[Any], Any, T]]],
    Callable[..., Option[T]],
]:
    """
    Decorator that enables generator-based do-notation for Options.

    TYPE CHECKER NOTE:
    Always annotate the return type explicitly — pyright and mypy cannot
    infer it from the generator body.

    Yield an Option to "unwrap" it — if it's Some, the value is sent back.
    If it's Nothing, execution stops and Nothing is returned immediately.

    The final ``return`` value is wrapped in Some() — unless it is already
    an Option, in which case it is returned as-is.

    Usage::

        @do_option()
        def lookup():
            user = yield find_user_opt(1)
            email = yield get_email_opt(user)
            return email.lower()

        lookup()  # Some("archy@...") or Nothing

        @do_option()
        def conditional(value):
            if value is None:
                return Nothing  # explicit Nothing — not double-wrapped
            return value

        conditional(None)  # Nothing
        conditional(42)    # Some(42)
    """
    def decorator(
        gen_func: Callable[..., Generator[Option[Any], Any, T]],
    ) -> Callable[..., Option[T]]:

        @functools.wraps(gen_func)
        def wrapper(*args: Any, **kwargs: Any) -> Option[T]:
            gen = gen_func(*args, **kwargs)
            # If the function returned early (no yield), it's not a generator
            if not isinstance(gen, GeneratorType):
                return _finalize_option(gen)
            try:
                yielded = next(gen)
                while True:
                    # Guard: ensure the yielded value is a Result or Option
                    if not hasattr(yielded, "_is_monadic") or not yielded._is_monadic:
                        raise TypeError(
                            f"Value yielded in @do_option must be Option or Result, got {type(yielded).__name__}. "
                            "Did you mean to use '.unwrap()' or yield a valid container?"
                        )

                    if isinstance(yielded, _NothingType):
                        return _Nothing

                    if isinstance(yielded, Err):
                        return _Nothing  # Err in Option context → Nothing
                    
                    # Special case: if a Result is yielded in do_option, transpose it?
                    # No, let's keep it simple: just unwrap if it has .unwrap()
                    try:
                        yielded = gen.send(yielded.unwrap())
                    except StopIteration as stop:
                        return _finalize_option(stop.value)
            except StopIteration as stop:
                return _finalize_option(stop.value)

        return wrapper

    return decorator


def _finalize_option(return_value: Any) -> Option[Any]:
    """
    Wrap a generator's return value in Some — unless it is already an Option.

    Handles explicit Result returns: Err → Nothing, Ok → Some(value).
    """
    if isinstance(return_value, (_NothingType, Some)):
        return return_value
    if isinstance(return_value, Err):
        return _Nothing
    if isinstance(return_value, Ok):
        return Some(return_value.unwrap())
    return Some(return_value)
