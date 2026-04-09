"""
resolute._result
~~~~~~~~~~~~~~~~~
Core Result[T, E] type with Ok and Err variants.

Result represents a computation that can either succeed (Ok) or fail (Err).
It forces the caller to handle both cases explicitly, making error paths
visible in the type system and eliminating surprise exceptions.
"""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    TypeVar,
    TYPE_CHECKING,
    overload,
    cast,
    get_args,
    get_origin,
)

__all__ = ["Result", "Ok", "Err"]


from ._exceptions import UnwrapError

if TYPE_CHECKING:
    from ._option import Option
    from ._context import ContextError

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


class Result(Generic[T, E]):
    """
    Base class for Ok[T, E] and Err[T, E].

    Never instantiate Result directly — use Ok(value) or Err(error).

    Type parameters:
        T — the success value type
        E — the error value type
    """

    __slots__ = ()

    # ------------------------------------------------------------------ #
    # State inspection
    # ------------------------------------------------------------------ #

    def is_ok(self) -> bool:
        """Return True if this is an Ok variant."""
        return isinstance(self, Ok)

    def is_err(self) -> bool:
        """Return True if this is an Err variant."""
        return isinstance(self, Err)

    def is_ok_and(self, predicate: Callable[[T], bool]) -> bool:
        """
        Return True if this is Ok AND the value satisfies the predicate.

            Ok(4).is_ok_and(lambda x: x > 3)   # True
            Ok(2).is_ok_and(lambda x: x > 3)   # False
            Err("x").is_ok_and(lambda x: True)  # False
        """
        if isinstance(self, Ok):
            return predicate(cast(Ok[T, E], self)._value)
        return False

    def is_err_and(self, predicate: Callable[[E], bool]) -> bool:
        """
        Return True if this is Err AND the error satisfies the predicate.

            Err("bad").is_err_and(lambda e: "bad" in e)  # True
            Ok(1).is_err_and(lambda e: True)             # False
        """
        if isinstance(self, Err):
            return predicate(cast(Err[T, E], self)._error)
        return False

    @classmethod
    def from_optional(cls, value: T | None, error: E) -> "Result[T, E]":
        """
        Wrap a nullable value. Returns Ok(value) if not None, Err(error) otherwise.

        Useful for interfacing with traditional Python APIs:
            Result.from_optional(db.find(uid), "user not found")
        """
        return Ok(value) if value is not None else Err(error)

    # ------------------------------------------------------------------ #
    # Extracting values (safe)
    # ------------------------------------------------------------------ #

    def unwrap(self) -> T:
        """
        Return the Ok value, or raise UnwrapError if this is Err.

        Use this when you are logically certain the result is Ok.
        If you are not certain, use unwrap_or or unwrap_or_else instead.

            Ok(1).unwrap()       # 1
            Err("x").unwrap()    # raises UnwrapError
        """
        if isinstance(self, Ok):
            return cast(Ok[T, E], self)._value
        err = cast(Err[T, E], self)
        raise UnwrapError(
            f"Called unwrap() on an Err value: {err._error!r}",
            original=err._error,
        )

    def unwrap_or(self, default: T) -> T:
        """
        Return the Ok value, or the provided default if Err.

            Ok(1).unwrap_or(99)      # 1
            Err("x").unwrap_or(99)   # 99
        """
        if isinstance(self, Ok):
            return cast(Ok[T, E], self)._value
        return default

    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        """
        Return the Ok value, or compute a default from the error.

            Err("oops").unwrap_or_else(lambda e: len(e))  # 4
        """
        if isinstance(self, Ok):
            return cast(T, self._value)
        err: Err[T, E] = cast(Err[T, E], self)
        return f(err._error)

    def unwrap_or_raise(self, exc: Exception) -> T:
        """
        Return the Ok value, or raise the given exception if Err.

            Err("bad").unwrap_or_raise(ValueError("config failed"))
        """
        if isinstance(self, Ok):
            return cast(T, self._value)
        raise exc

    def unwrap_err(self) -> E:
        """
        Return the Err value, or raise UnwrapError if this is Ok.

            Err("x").unwrap_err()   # "x"
            Ok(1).unwrap_err()      # raises UnwrapError
        """
        if isinstance(self, Err):
            return cast(E, self._error)
        ok: Ok[T, E] = self  # type: ignore[assignment]
        raise UnwrapError(
            f"Called unwrap_err() on an Ok value: {ok._value!r}",
            original=ok._value,
        )

    def expect(self, message: str) -> T:
        """
        Return the Ok value, or raise UnwrapError with a custom message if Err.

            Ok(1).expect("should have a user")        # 1
            Err("nope").expect("should have a user")  # raises UnwrapError("should have a user: 'nope'")
        """
        if isinstance(self, Ok):
            return cast(T, self._value)
        err: Err[T, E] = self  # type: ignore[assignment]
        raise UnwrapError(
            f"{message}: {err._error!r}",
            original=err._error,
        )

    def expect_err(self, message: str) -> E:
        """
        Return the Err value, or raise UnwrapError with a custom message if Ok.
        """
        if isinstance(self, Err):
            return cast(E, self._error)
        ok: Ok[T, E] = self  # type: ignore[assignment]
        raise UnwrapError(
            f"{message}: {ok._value!r}",
            original=ok._value,
        )

    # ------------------------------------------------------------------ #
    # Transforming Ok values
    # ------------------------------------------------------------------ #

    def map(self, f: Callable[[T], U]) -> "Result[U, E]":
        """
        Apply f to the Ok value, leaving Err untouched.

            Ok(2).map(lambda x: x * 3)      # Ok(6)
            Err("bad").map(lambda x: x * 3) # Err("bad")
        """
        if isinstance(self, Ok):
            return Ok(f(self._value))
        return self  # type: ignore[return-value]

    def map_or(self, default: U, f: Callable[[T], U]) -> U:
        """
        Apply f to Ok value, or return default for Err.

            Ok(2).map_or(0, lambda x: x * 3)      # 6
            Err("bad").map_or(0, lambda x: x * 3) # 0
        """
        if isinstance(self, Ok):
            return f(cast(T, self._value))
        return default

    def map_or_else(self, default_f: Callable[[E], U], f: Callable[[T], U]) -> U:
        """
        Apply f to Ok value, or apply default_f to Err value.

            Ok(2).map_or_else(lambda e: 0, lambda x: x * 3)       # 6
            Err("bad").map_or_else(lambda e: len(e), lambda x: 0)  # 3
        """
        if isinstance(self, Ok):
            return f(cast(T, self._value))
        err: Err[T, E] = cast(Err[T, E], self)
        return default_f(err._error)

    # ------------------------------------------------------------------ #
    # Transforming Err values
    # ------------------------------------------------------------------ #

    def map_err(self, f: Callable[[E], F]) -> "Result[T, F]":
        """
        Apply f to the Err value, leaving Ok untouched.

            Err("bad").map_err(str.upper)  # Err("BAD")
            Ok(1).map_err(str.upper)       # Ok(1)
        """
        if isinstance(self, Err):
            return Err(f(self._error))
        return self  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Chaining / Flatmap
    # ------------------------------------------------------------------ #

    def and_then(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """
        Chain another Result-returning function on the Ok value.
        Short-circuits on Err — f is never called.

        This is the core composition operator (also known as flatmap or bind).

            def safe_sqrt(x: float) -> Result[float, str]:
                return Ok(x ** 0.5) if x >= 0 else Err("negative input")

            Ok(4.0).and_then(safe_sqrt)    # Ok(2.0)
            Ok(-1.0).and_then(safe_sqrt)   # Err("negative input")
            Err("prior").and_then(safe_sqrt)  # Err("prior")
        """
        if isinstance(self, Ok):
            return f(cast(T, self._value))
        return cast(Result[U, E], self)

    def or_else(self, f: Callable[[E], "Result[T, F]"]) -> "Result[T, F]":
        """
        Chain a recovery function on the Err value.
        Short-circuits on Ok — f is never called.

            Err("bad").or_else(lambda e: Ok(0))  # Ok(0)
            Ok(1).or_else(lambda e: Ok(0))        # Ok(1)
        """
        if isinstance(self, Err):
            return f(self._error)
        return self  # type: ignore[return-value]

    def and_(self, other: "Result[U, E]") -> "Result[U, E]":
        """
        Return other if self is Ok, otherwise return self (the Err).

            Ok(1).and_(Ok(2))        # Ok(2)
            Err("x").and_(Ok(2))     # Err("x")
            Ok(1).and_(Err("y"))     # Err("y")
        """
        if isinstance(self, Ok):
            return other
        return self  # type: ignore[return-value]

    def or_(self, other: "Result[T, F]") -> "Result[T, F]":
        """
        Return self if Ok, otherwise return other.

            Ok(1).or_(Ok(2))        # Ok(1)
            Err("x").or_(Ok(2))     # Ok(2)
            Err("x").or_(Err("y"))  # Err("y")
        """
        if isinstance(self, Err):
            return other
        return cast(Result[T, F], self)

    def flatten(self) -> "Result[T, E]":
        """
        Flatten a nested Result[Result[T, E], E] into Result[T, E].

        If self is Ok(Ok(value)), returns Ok(value).
        If self is Ok(Err(e)), returns Err(e).
        If self is Err(e), returns Err(e).

            Ok(Ok(42)).flatten()        # Ok(42)
            Ok(Err("bad")).flatten()    # Err("bad")
            Err("outer").flatten()     # Err("outer")
        """
        if isinstance(self, Ok) and isinstance(self._value, Result):
            return self._value
        return self  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Converting to Option
    # ------------------------------------------------------------------ #

    def ok(self) -> "Option[T]":
        """
        Convert to Option — Ok(v) becomes Some(v), Err becomes Nothing.
        The error context is discarded.

            Ok(1).ok()      # Some(1)
            Err("x").ok()   # Nothing
        """
        from ._option import Some, _Nothing
        if isinstance(self, Ok):
            return Some(cast(T, self._value))
        return _Nothing

    def err(self) -> "Option[E]":
        """
        Convert to Option — Err(e) becomes Some(e), Ok becomes Nothing.

            Err("x").err()  # Some("x")
            Ok(1).err()     # Nothing
        """
        from ._option import Some, _Nothing
        if isinstance(self, Err):
            return Some(cast(E, self._error))
        return _Nothing

    # ------------------------------------------------------------------ #
    # Context propagation
    # ------------------------------------------------------------------ #

    def context(self, message: str) -> "Result[T, ContextError]":
        """
        Add context to an Err. If Ok, passes through unchanged.

            Err("not found").context("loading user config")
            # Err(ContextError("loading user config", "not found"))

        This is inspired by Rust's `.context()` from the `anyhow` crate.
        It wraps the original error in a ContextError that preserves
        the full error chain, similar to Python's `raise ... from ...`.
        """
        from ._context import ContextError
        if isinstance(self, Err):
            return Err(ContextError(message, self.unwrap_err()))
        return cast("Result[T, ContextError]", self)

    def with_context(self, f: Callable[[], str]) -> "Result[T, ContextError]":
        """
        Add context lazily — f() is only called if this is Err.

            result.with_context(lambda: f"Failed to process {filename}")

        Use this when building the context message is expensive.
        """
        from ._context import ContextError
        if isinstance(self, Err):
            return Err(ContextError(f(), self.unwrap_err()))
        return cast("Result[T, ContextError]", self)

    def root_cause(self) -> "Option[Any]":
        """
        If this is Err and the error is a ContextError, return its root cause.
        If it's a normal Err, return the error value.
        If it's Ok, return Nothing.

            Err("bad").root_cause()              # Some("bad")
            Err(ContextError("m", "c")).root_cause() # Some("c")
            Ok(1).root_cause()                   # Nothing
        """
        from ._option import Some, _Nothing
        if isinstance(self, Err):
            err = self.unwrap_err()
            if hasattr(err, "root_cause"):
                return Some(err.root_cause)
            return Some(err)
        return _Nothing

    # ------------------------------------------------------------------ #
    # Iteration support
    # ------------------------------------------------------------------ #

    def __iter__(self) -> Iterator[T]:
        """
        Iterate over the Ok value (yields one item), or nothing for Err.

        This lets you use Result in a for loop or with list comprehensions:

            [x for r in results for x in r]  # flattens Ok values, skips Errs
        """
        if isinstance(self, Ok):
            yield cast(T, self._value)

    # ------------------------------------------------------------------ #
    # Dunder methods
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        raise NotImplementedError  # implemented by Ok and Err

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError

    def __bool__(self) -> bool:
        """Ok is truthy, Err is falsy. Allows: if result: ..."""
        return isinstance(self, Ok)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: Any
    ) -> Any:
        """Pydantic v2 core schema implementation."""
        from pydantic_core import core_schema

        args = get_args(source)
        if len(args) == 2:
            ok_type, err_type = args
        else:
            ok_type, err_type = Any, Any

        def validate(value: Any) -> Result[Any, Any]:
            if isinstance(value, Result):
                return value
            if isinstance(value, dict):
                if "ok" in value:
                    return Ok(value["ok"])
                if "err" in value:
                    return Err(value["err"])
            # Fallback: try to validate as Ok
            return Ok(value)

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: {"ok": v.unwrap()} if v.is_ok() else {"err": v.unwrap_err()}
            ),
        )




# --------------------------------------------------------------------------- #
# Concrete variants
# --------------------------------------------------------------------------- #

class Ok(Result[T, E]):
    """
    The success variant of Result.

        r = Ok(42)
        r.is_ok()       # True
        r.unwrap()      # 42
    """

    __slots__ = ("_value",)
    __match_args__ = ("_value",)  # enables: case Ok(value):

    def __init__(self, value: T) -> None:
        self._value = value

    @property
    def value(self) -> T:
        """The contained success value."""
        return self._value

    def __repr__(self) -> str:
        return f"Ok({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ok) and self._value == other._value

    def __hash__(self) -> int:
        return hash(("Ok", self._value))

    def __bool__(self) -> bool:
        return True


class Err(Result[T, E]):
    """
    The failure variant of Result.

        r = Err("file not found")
        r.is_err()        # True
        r.unwrap_err()    # "file not found"
    """

    __slots__ = ("_error",)
    __match_args__ = ("_error",)  # enables: case Err(error):

    def __init__(self, error: E) -> None:
        self._error = error

    @property
    def error(self) -> E:
        """The contained error value."""
        return self._error

    def __repr__(self) -> str:
        return f"Err({self._error!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Err) and self._error == other._error

    def __hash__(self) -> int:
        return hash(("Err", self._error))

    def __bool__(self) -> bool:
        return False
