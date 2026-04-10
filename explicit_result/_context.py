"""
explicit_result._context
~~~~~~~~~~~~~~~~~~
Error context propagation — wrap errors with additional context
without losing the original cause.

Inspired by Rust's `?` operator with `From` trait and
Python's `raise ... from ...` chaining.
"""

from __future__ import annotations


class ContextError(Exception):
    """
    An error that wraps another error with additional context.

        ContextError("Failed to load config", FileNotFoundError("app.json"))

    Supports Python's standard exception chaining via __cause__,
    so tracebacks show the full chain naturally.
    """

    def __init__(self, message: str, original: object = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = original
        if isinstance(original, BaseException):
            self.__cause__ = original   # enables "The above exception was..." traceback

    def __str__(self) -> str:
        return f"{self.message}: {self.cause}"

    def __repr__(self) -> str:
        return f"ContextError({self.message!r}, cause={self.cause!r})"

    @property
    def root_cause(self) -> object:
        """
        The original cause of this error, unwrapped from all ContextErrors.
        """
        current = self.cause
        while isinstance(current, ContextError):
            current = current.cause
        return current

    def chain(self) -> list[object]:
        """
        Walk the full error chain and return a list of all causes.

            err = ContextError("c", ContextError("b", ValueError("a")))
            err.chain()  # [ContextError("c",...), ContextError("b",...), ValueError("a")]
        """
        errors: list[object] = [self]
        current: object = self.cause
        while current is not None:
            errors.append(current)
            if isinstance(current, ContextError):
                current = current.cause
            else:
                break
        return errors
