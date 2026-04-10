"""
explicit_result._option
~~~~~~~~~~~~~~~~~
Core Option[T] type with Some and Nothing variants.

Option represents a value that may or may not exist.
It is an explicit, type-safe alternative to returning None.
"""

from __future__ import annotations

import warnings

from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    TypeVar,
    TYPE_CHECKING,
    cast,
    get_args,
    get_origin,
)

__all__ = ["Option", "Some", "Nothing"]


from ._exceptions import UnwrapError

if TYPE_CHECKING:
    from ._result import Result

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


class Option(Generic[T]):
    """
    Base class for Some[T] and Nothing.

    Never instantiate Option directly — use Some(value) or Nothing.

    Type parameters:
        T — the type of the contained value (only relevant for Some)
    """

    __slots__ = ()
    _is_monadic = True

    # ------------------------------------------------------------------ #
    # State inspection
    # ------------------------------------------------------------------ #

    def is_some(self) -> bool:
        """Return True if this is a Some variant."""
        return isinstance(self, Some)

    def is_nothing(self) -> bool:
        """Return True if this is the Nothing variant."""
        return self is _Nothing

    def is_some_and(self, predicate: Callable[[T], bool]) -> bool:
        """
        Return True if Some and value satisfies predicate.

            Some(4).is_some_and(lambda x: x > 3)   # True
            Some(2).is_some_and(lambda x: x > 3)   # False
            Nothing.is_some_and(lambda x: True)     # False
        """
        if isinstance(self, Some):
            return predicate(cast(T, self._value))
        return False

    @classmethod
    def of(cls, value: T | None) -> "Option[T]":
        """Wrap a nullable value. Returns Nothing for None, Some(value) otherwise.
        
        Use this instead of Some() when the value might be None:
            Option.of(user.email)   # Nothing if email is None, Some(email) otherwise
            Some(user.email)        # Some(None) — almost certainly a bug
        """
        return Nothing if value is None else Some(value)

    @classmethod
    def from_optional(cls, value: T | None) -> "Option[T]":
        """Alias for of(). Wrap a nullable value."""
        return cls.of(value)

    # ------------------------------------------------------------------ #
    # Extracting values
    # ------------------------------------------------------------------ #

    def unwrap(self) -> T:
        """
        Return the Some value, or raise UnwrapError if Nothing.

            Some(1).unwrap()   # 1
            Nothing.unwrap()   # raises UnwrapError
        """
        if isinstance(self, Some):
            return cast(T, self._value)
        raise UnwrapError("Called unwrap() on Nothing")

    def unwrap_or(self, default: T) -> T:
        """
        Return the Some value, or the provided default if Nothing.

            Some(1).unwrap_or(99)  # 1
            Nothing.unwrap_or(99)  # 99
        """
        if isinstance(self, Some):
            return cast(T, self._value)
        return default

    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        """
        Return the Some value, or compute a default if Nothing.

            Nothing.unwrap_or_else(lambda: expensive_default())
        """
        if isinstance(self, Some):
            return cast(T, self._value)
        return f()

    def unwrap_or_raise(self, exc: Exception) -> T:
        """
        Return the Some value, or raise the given exception if Nothing.
        """
        if isinstance(self, Some):
            return cast(T, self._value)
        raise exc

    def expect(self, message: str) -> T:
        """
        Return the Some value, or raise UnwrapError with custom message.

            Nothing.expect("user must be logged in")
            # raises UnwrapError("user must be logged in")
        """
        if isinstance(self, Some):
            return cast(T, self._value)
        raise UnwrapError(message)

    # ------------------------------------------------------------------ #
    # Transforming values
    # ------------------------------------------------------------------ #

    def map(self, f: Callable[[T], U]) -> "Option[U]":
        """
        Apply f to the Some value, leaving Nothing untouched.

            Some(2).map(lambda x: x * 3)  # Some(6)
            Nothing.map(lambda x: x * 3)  # Nothing
        """
        if isinstance(self, Some):
            return Some(f(self._value))
        return self  # type: ignore[return-value]

    def map_or(self, default: U, f: Callable[[T], U]) -> U:
        """
        Apply f to Some value, or return default for Nothing.

            Some(2).map_or(0, lambda x: x * 3)  # 6
            Nothing.map_or(0, lambda x: x * 3)  # 0
        """
        if isinstance(self, Some):
            return f(cast(T, self._value))
        return default

    def map_or_else(self, default_f: Callable[[], U], f: Callable[[T], U]) -> U:
        """
        Apply f to Some value, or call default_f for Nothing.

            Nothing.map_or_else(lambda: compute_default(), lambda x: x)
        """
        if isinstance(self, Some):
            return f(cast(T, self._value))
        return default_f()

    def filter(self, predicate: Callable[[T], bool]) -> "Option[T]":
        """
        Return self if Some and predicate is True, otherwise Nothing.

            Some(4).filter(lambda x: x > 3)   # Some(4)
            Some(2).filter(lambda x: x > 3)   # Nothing
            Nothing.filter(lambda x: True)     # Nothing
        """
        if isinstance(self, Some) and predicate(cast(T, self._value)):
            return self
        return Nothing

    # ------------------------------------------------------------------ #
    # Chaining
    # ------------------------------------------------------------------ #

    def and_then(self, f: Callable[[T], "Option[U]"]) -> "Option[U]":
        """
        Chain another Option-returning function on the Some value.
        Short-circuits on Nothing.

            def find_email(user_id: int) -> Option[str]: ...

            Some(42).and_then(find_email)  # Some("archy@example.com") or Nothing
            Nothing.and_then(find_email)   # Nothing
        """
        if isinstance(self, Some):
            return f(cast(T, self._value))
        return self  # type: ignore[return-value]

    def or_else(self, f: Callable[[], "Option[T]"]) -> "Option[T]":
        """
        Return self if Some, otherwise call f and return its result.

            Nothing.or_else(lambda: Some(default_value))
            Some(1).or_else(lambda: Some(99))  # Some(1)
        """
        if isinstance(self, Some):
            return self
        return f()

    def and_(self, other: "Option[U]") -> "Option[U]":
        """
        Return other if self is Some, otherwise Nothing.

            Some(1).and_(Some(2))   # Some(2)
            Nothing.and_(Some(2))   # Nothing
        """
        if isinstance(self, Some):
            return other
        return Nothing

    def or_(self, other: "Option[T]") -> "Option[T]":
        """
        Return self if Some, otherwise other.

            Some(1).or_(Some(99))  # Some(1)
            Nothing.or_(Some(99))  # Some(99)
        """
        if isinstance(self, Some):
            return self
        return other

    def zip(self, other: "Option[U]") -> "Option[tuple[T, U]]":
        """
        Combine two Some values into a Some tuple.
        Returns Nothing if either is Nothing.

            Some(1).zip(Some("a"))   # Some((1, "a"))
            Some(1).zip(Nothing)     # Nothing
            Nothing.zip(Some("a"))   # Nothing
        """
        if isinstance(self, Some) and isinstance(other, Some):
            return Some((cast(T, self._value), cast(U, other._value)))
        return Nothing

    def flatten(self) -> "Option[T]":
        """
        Flatten Option[Option[T]] into Option[T].

            Some(Some(1)).flatten()  # Some(1)
            Some(Nothing).flatten()  # Nothing
            Nothing.flatten()        # Nothing
        """
        if isinstance(self, Some) and isinstance(self._value, Option):
            return cast(Option[T], self._value)
        if isinstance(self, Some):
            return self
        return Nothing

    def transpose(self) -> "Result[Option[T], E]":
        """
        Transpose Option[Result[T, E]] into Result[Option[T], E].

        Returns:
            - Ok(Some(v)) if self is Some(Ok(v))
            - Err(e) if self is Some(Err(e))
            - Ok(Nothing) if self is Nothing

            Some(Ok(1)).transpose()    # Ok(Some(1))
            Some(Err("x")).transpose() # Err("x")
            Nothing.transpose()        # Ok(Nothing)
        """
        from ._result import Ok, Err, Result
        if isinstance(self, Some):
            inner = self.unwrap()
            if isinstance(inner, Result):
                if isinstance(inner, Ok):
                    return Ok(Some(inner.unwrap()))
                return inner  # Err passes through
            # Fallback for non-Result Some values (though transpose is intended for Result)
            return Ok(self)
        return Ok(Nothing)

    # ------------------------------------------------------------------ #
    # Converting to Result
    # ------------------------------------------------------------------ #

    def ok_or(self, error: E) -> "Result[T, E]":
        """
        Convert to Result — Some(v) becomes Ok(v), Nothing becomes Err(error).

            Some(1).ok_or("missing")  # Ok(1)
            Nothing.ok_or("missing")  # Err("missing")
        """
        from ._result import Ok, Err
        if isinstance(self, Some):
            return Ok(cast(T, self._value))
        return Err(error)

    def ok_or_else(self, error_f: Callable[[], E]) -> "Result[T, E]":
        """
        Convert to Result — Some(v) becomes Ok(v), Nothing becomes Err(error_f()).

            Nothing.ok_or_else(lambda: compute_error_message())
        """
        from ._result import Ok, Err
        if isinstance(self, Some):
            return Ok(cast(T, self._value))
        return Err(error_f())

    # ------------------------------------------------------------------ #
    # Iteration support
    # ------------------------------------------------------------------ #

    def __iter__(self) -> Iterator[T]:
        """
        Iterate over the Some value (yields one item), or nothing.

            [x for opt in options for x in opt]  # flatten list of Options
        """
        if isinstance(self, Some):
            yield cast(T, self._value)

    # ------------------------------------------------------------------ #
    # Dunder methods
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        raise NotImplementedError

    def __bool__(self) -> bool:
        """Prevent boolean evaluation to avoid hidden truthiness bugs."""
        raise RuntimeError(
            "Resolute types do not support implicit boolean truthiness. "
            "Use .is_some(), .is_nothing(), or pattern matching instead."
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: Any
    ) -> Any:
        """Pydantic v2 core schema implementation."""
        from pydantic_core import core_schema

        args = get_args(source)
        # Handle both Option and Option[T]
        inner_type = args[0] if args else Any

        def validate(value: Any) -> Option[Any]:
            if value is None:
                return Nothing
            if isinstance(value, Option):
                return value
            return Some(value)

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.unwrap() if v.is_some() else None
            ),
        )


# --------------------------------------------------------------------------- #
# Concrete variants
# --------------------------------------------------------------------------- #

class Some(Option[T]):
    """
    The Some variant — contains a value.

        o = Some(42)
        o.is_some()   # True
        o.unwrap()    # 42
    """

    __slots__ = ("_value",)
    __match_args__ = ("value",)  # enables: case Some(value=x):

    def __init__(self, value: T) -> None:
        if value is None:
            warnings.warn(
                "Some(None) is usually a bug. If you are wrapping a potentially "
                "missing value, use Option.of(value) instead.",
                RuntimeWarning,
                stacklevel=2,
            )
        self._value = value
        from ._context_vars import _check_do_context
        _check_do_context(self, "@do_option")

    @property
    def value(self) -> T:
        """The contained value."""
        return self._value

    def __repr__(self) -> str:
        return f"Some({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Some) and self._value == other._value

    def __hash__(self) -> int:
        return hash(("Some", self._value))


class _NothingType(Option[T]):
    """
    The Nothing variant — singleton, represents absence of a value.

    Use the module-level `Nothing` constant; don't instantiate directly.
    """

    __slots__ = ()
    _instance: _NothingType[Any] | None = None

    def __new__(cls) -> _NothingType[T]:
        # Singleton — there is only one Nothing
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __copy__(self) -> _NothingType[T]:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> _NothingType[T]:
        return self

    def __repr__(self) -> str:
        return "Nothing"

    def __eq__(self, other: object) -> bool:
        return other is _Nothing

    def __hash__(self) -> int:
        return hash("Nothing")


# The singleton Nothing instance — import and use this directly
Nothing: _NothingType[Any] = _NothingType()

# Internal alias used in _result.py to avoid circular import issues
_Nothing = Nothing
