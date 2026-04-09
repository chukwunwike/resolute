"""
resolute._async_helpers
~~~~~~~~~~~~~~~~~~~~~~~~
Async ergonomics for Result and Option.

These utilities bridge the gap between sync Result/Option types
and async/await code, eliminating awkward nested awaits.
"""

from __future__ import annotations

import warnings
from typing import (
    Any,
    Awaitable,
    Callable,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from ._result import Ok, Err, Result

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


async def from_awaitable(
    aw: Awaitable[T],
    catch: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
) -> Result[T, Exception]:
    """
    Await an awaitable and wrap the result in Ok/Err.

        result = await from_awaitable(fetch_data(), catch=ConnectionError)
        # Ok(data) or Err(ConnectionError(...))

    Arguments:
        aw: Any awaitable (coroutine, Task, Future).
        catch: Exception type(s) to catch. Defaults to Exception.

    Returns:
        Ok(value) on success, Err(exception) on caught failure.
    """
    if catch is Exception:
        warnings.warn(
            "from_awaitable(catch=Exception) catches ALL exceptions. "
            "Prefer specifying the exact exception types you expect.",
            RuntimeWarning,
            stacklevel=2,
        )
    try:
        value = await aw
        return Ok(value)
    except catch as exc:
        return Err(exc)


async def map_async(
    result: Result[T, E],
    f: Callable[[T], Awaitable[U]],
) -> Result[U, E]:
    """
    Apply an async function to the Ok value of a Result.

        result = Ok(user_id)
        profile = await map_async(result, fetch_profile)
        # Ok(Profile(...)) or original Err

    If the result is Err, the function is never called.
    """
    if isinstance(result, Ok):
        value = await f(result.value)
        return Ok(value)
    return result  # type: ignore[return-value]


async def and_then_async(
    result: Result[T, E],
    f: Callable[[T], Awaitable[Result[U, E]]],
) -> Result[U, E]:
    """
    Chain an async Result-returning function on the Ok value.

        result = Ok(user_id)
        profile = await and_then_async(result, async_find_profile)
        # Ok(Profile(...)) or Err(...)

    If the result is Err, the function is never called.
    This is the async equivalent of .and_then().
    """
    if isinstance(result, Ok):
        return await f(result.value)
    return result  # type: ignore[return-value]
