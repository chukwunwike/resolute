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
from ._option import Option, Some, Nothing

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


async def from_optional_async(aw: Awaitable[T | None]) -> Option[T]:
    """
    Await a nullable value and wrap it in Option. Nothing if None.
    """
    value = await aw
    return Some(value) if value is not None else Nothing


async def map_option_async(
    opt: Option[T],
    f: Callable[[T], Awaitable[U]],
) -> Option[U]:
    """
    Apply an async function to the Some value of an Option.
    """
    if isinstance(opt, Some):
        value = await f(opt.value)
        return Some(value)
    return opt  # type: ignore[return-value]


async def and_then_option_async(
    opt: Option[T],
    f: Callable[[T], Awaitable[Option[U]]],
) -> Option[U]:
    """
    Chain an async Option-returning function on the Some value.
    """
    if isinstance(opt, Some):
        return await f(opt.value)
    return opt  # type: ignore[return-value]
