"""
resolute._combinators
~~~~~~~~~~~~~~~~~~~~~~
Higher-order utilities for working with collections of Results and Options.

    collect        — Ok([...]) if all Ok, else first Err
    collect_all    — Ok([...]) if all Ok, else Err([all errors])
    partition      — split list into (ok_values, err_values)
    transpose      — flip Option[Result] <-> Result[Option]
    flatten_result — Result[Result[T, E], E] -> Result[T, E]
    sequence       — like collect but for Option lists
"""

from __future__ import annotations

from typing import Iterable, TypeVar, List, Tuple

from ._result import Ok, Err, Result
from ._option import Some, Option, _Nothing, _NothingType

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


# --------------------------------------------------------------------------- #
# Result combinators
# --------------------------------------------------------------------------- #

def collect(results: Iterable[Result[T, E]]) -> Result[List[T], E]:
    """
    Turn an iterable of Results into a single Result of a list.

    Returns Ok([values...]) if every result is Ok.
    Returns the FIRST Err encountered, short-circuiting the rest.

        collect([Ok(1), Ok(2), Ok(3)])          # Ok([1, 2, 3])
        collect([Ok(1), Err("bad"), Ok(3)])      # Err("bad")
        collect([])                              # Ok([])

    Typical use: running multiple validations and either getting all
    values or the first failure.
    """
    values: List[T] = []
    for r in results:
        if isinstance(r, Err):
            return r
        values.append(r.unwrap())
    return Ok(values)


def collect_all(results: Iterable[Result[T, E]]) -> Result[List[T], List[E]]:
    """
    Turn an iterable of Results into a single Result of a list,
    collecting ALL errors rather than stopping at the first.

        collect_all([Ok(1), Err("a"), Ok(3), Err("b")])
        # Err(["a", "b"])

        collect_all([Ok(1), Ok(2)])
        # Ok([1, 2])

    Typical use: form validation where you want to report every
    invalid field to the user in one pass.
    """
    values: List[T] = []
    errors: List[E] = []

    for r in results:
        if isinstance(r, Ok):
            values.append(r.value)
        elif isinstance(r, Err):
            errors.append(r.error)

    if errors:
        return Err(errors)
    return Ok(values)


def partition(
    results: Iterable[Result[T, E]],
) -> Tuple[List[T], List[E]]:
    """
    Split an iterable of Results into two lists:
    one of Ok values and one of Err values.

        oks, errs = partition([Ok(1), Err("a"), Ok(2), Err("b")])
        # oks  = [1, 2]
        # errs = ["a", "b"]

    No values are lost — every Result ends up in exactly one list.
    """
    ok_values: List[T] = []
    err_values: List[E] = []

    for r in results:
        if isinstance(r, Ok):
            ok_values.append(r.value)
        elif isinstance(r, Err):
            err_values.append(r.error)

    return ok_values, err_values


def flatten_result(result: Result[Result[T, E], E]) -> Result[T, E]:
    """
    Flatten a nested Result[Result[T, E], E] into Result[T, E].

        flatten_result(Ok(Ok(1)))    # Ok(1)
        flatten_result(Ok(Err("x"))) # Err("x")
        flatten_result(Err("outer")) # Err("outer")

    Equivalent to result.and_then(lambda x: x).
    """
    return result.and_then(lambda x: x)


# --------------------------------------------------------------------------- #
# Option combinators
# --------------------------------------------------------------------------- #

def sequence(options: Iterable[Option[T]]) -> Option[List[T]]:
    """
    Turn an iterable of Options into a single Option of a list.

    Returns Some([values...]) if every option is Some.
    Returns Nothing if ANY option is Nothing.

        sequence([Some(1), Some(2), Some(3)])  # Some([1, 2, 3])
        sequence([Some(1), Nothing, Some(3)])  # Nothing
        sequence([])                           # Some([])
    """
    values: List[T] = []
    for opt in options:
        if isinstance(opt, _NothingType):
            return _Nothing
        values.append(opt.unwrap())
    return Some(values)


def transpose(opt: Option[Result[T, E]]) -> Result[Option[T], E]:
    """
    Transpose Option[Result[T, E]] into Result[Option[T], E].

        transpose(Some(Ok(1)))    # Ok(Some(1))
        transpose(Some(Err("x"))) # Err("x")
        transpose(Nothing)        # Ok(Nothing)

    Useful when you have a value that might not exist, and if it
    does exist it might have failed.
    """
    if isinstance(opt, _NothingType):
        return Ok(_Nothing)
    # opt is Some(Result)
    inner: Result[T, E] = opt.unwrap()
    if isinstance(inner, Ok):
        return Ok(Some(inner.value))
    return inner  # type: ignore[return-value]


def transpose_result(result: Result[Option[T], E]) -> Option[Result[T, E]]:
    """
    Transpose Result[Option[T], E] into Option[Result[T, E]].

        transpose_result(Ok(Some(1)))  # Some(Ok(1))
        transpose_result(Ok(Nothing))  # Nothing
        transpose_result(Err("x"))     # Some(Err("x"))

    Inverse of transpose().
    """
    if isinstance(result, Err):
        return Some(result)
    # result is Ok(Option)
    inner: Option[T] = result.unwrap()
    if isinstance(inner, _NothingType):
        return _Nothing
    return Some(Ok(inner.unwrap()))
