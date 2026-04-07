"""
resolute._exceptions
~~~~~~~~~~~~~~~~~~~~~
Custom exceptions raised by resolute internals.
"""

from typing import Any


class UnwrapError(Exception):
    """
    Raised when .unwrap() is called on an Err, or .unwrap_err() on an Ok,
    or .unwrap() is called on Nothing.

    The original value is stored on the exception so callers can inspect it.
    """

    def __init__(self, message: str, original: Any = None) -> None:
        super().__init__(message)
        self.original = original

    def __repr__(self) -> str:
        return f"UnwrapError({self.args[0]!r})"


class SafeDecoratorError(Exception):
    """
    Raised at decoration time when @safe is used incorrectly —
    e.g. attempting to catch BaseException or not specifying
    exception types as a class or tuple of classes.
    """
