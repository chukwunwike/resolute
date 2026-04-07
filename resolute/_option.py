"""
resolute._option
~~~~~~~~~~~~~~~~~
Core Option[T] type with Some and Nothing variants.

Option represents a value that may or may not exist.
It is an explicit, type-safe alternative to returning None.
"""

from __future__ import annotations

from typing import (
    Callable,
    Generic,
    Iterator,
    TypeVar,
    TYPE_CHECKING,
)

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

    # ------------------------------------------------------------------ #
    # State inspection
    # ------------------------------------------------------------------ #

    def is_some(self) -> bool:
        """Return True if this is a Some variant."""
        return isinstance(self, Some)

    def is_nothing(self) -> bool:
        """Return True if this is the Nothing variant."""
        return isinstance(self, _NothingType)

    def is_some_and(self, predicate: Callable[[T], bool]) -> bool:
        """
        Return True if Some and value satisfies predicate.

            Some(4).is_some_and(lambda x: x > 3)   # True
            Some(2).is_some_and(lambda x: x > 3)   # False
            Nothing.is_some_and(lambda x: True)     # False
        """
        if isinstance(self, Some):
            return predicate(self._value)
        return False

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
            return self._value
        raise UnwrapError("Called unwrap() on Nothing")

    def unwrap_or(self, default: T) -> T:
        """
        Return the Some value, or the provided default if Nothing.

            Some(1).unwrap_or(99)  # 1
            Nothing.unwrap_or(99)  # 99
        """
        if isinstance(self, Some):
            return self._value
        return default

    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        """
        Return the Some value, or compute a default if Nothing.

            Nothing.unwrap_or_else(lambda: expensive_default())
        """
        if isinstance(self, Some):
            return self._value
        return f()

    def unwrap_or_raise(self, exc: Exception) -> T:
        """
        Return the Some value, or raise the given exception if Nothing.
        """
        if isinstance(self, Some):
            return self._value
        raise exc

    def expect(self, message: str) -> T:
        """
        Return the Some value, or raise UnwrapError with custom message.

            Nothing.expect("user must be logged in")
            # raises UnwrapError("user must be logged in")
        """
        if isinstance(self, Some):
            return self._value
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
            return f(self._value)
        return default

    def map_or_else(self, default_f: Callable[[], U], f: Callable[[T], U]) -> U:
        """
        Apply f to Some value, or call default_f for Nothing.

            Nothing.map_or_else(lambda: compute_default(), lambda x: x)
        """
        if isinstance(self, Some):
            return f(self._value)
        return default_f()

    def filter(self, predicate: Callable[[T], bool]) -> "Option[T]":
        """
        Return self if Some and predicate is True, otherwise Nothing.

            Some(4).filter(lambda x: x > 3)   # Some(4)
            Some(2).filter(lambda x: x > 3)   # Nothing
            Nothing.filter(lambda x: True)     # Nothing
        """
        if isinstance(self, Some) and predicate(self._value):
            return self
        return _Nothing

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
            return f(self._value)
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
        return _Nothing  # type: ignore[return-value]

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
            return Some((self._value, other._value))
        return _Nothing  # type: ignore[return-value]

    def flatten(self) -> "Option[T]":
        """
        Flatten Option[Option[T]] into Option[T].

            Some(Some(1)).flatten()  # Some(1)
            Some(Nothing).flatten()  # Nothing
            Nothing.flatten()        # Nothing
        """
        if isinstance(self, Some) and isinstance(self._value, Option):
            return self._value  # type: ignore[return-value]
        if isinstance(self, Some):
            return self  # type: ignore[return-value]
        return _Nothing  # type: ignore[return-value]

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
            return Ok(self._value)
        return Err(error)

    def ok_or_else(self, error_f: Callable[[], E]) -> "Result[T, E]":
        """
        Convert to Result — Some(v) becomes Ok(v), Nothing becomes Err(error_f()).

            Nothing.ok_or_else(lambda: compute_error_message())
        """
        from ._result import Ok, Err
        if isinstance(self, Some):
            return Ok(self._value)
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
            yield self._value

    # ------------------------------------------------------------------ #
    # Dunder methods
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError

    def __bool__(self) -> bool:
        """Some is truthy, Nothing is falsy."""
        return isinstance(self, Some)


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
    __match_args__ = ("_value",)  # enables: case Some(value):

    def __init__(self, value: T) -> None:
        self._value = value

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

    def __bool__(self) -> bool:
        return True


class _NothingType(Option[T]):
    """
    The Nothing variant — singleton, represents absence of a value.

    Use the module-level `Nothing` constant; don't instantiate directly.
    """

    __slots__ = ()
    _instance: "_NothingType | None" = None

    def __new__(cls) -> "_NothingType":
        # Singleton — there is only one Nothing
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "Nothing"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _NothingType)

    def __hash__(self) -> int:
        return hash("Nothing")

    def __bool__(self) -> bool:
        return False


# The singleton Nothing instance — import and use this directly
Nothing: _NothingType = _NothingType()

# Internal alias used in _result.py to avoid circular import issues
_Nothing = Nothing
