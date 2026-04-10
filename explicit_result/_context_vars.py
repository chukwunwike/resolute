import inspect
import warnings
from contextvars import ContextVar

# Tracks if we are currently inside a @do or @do_option runner.
# This is used to detect "orphaned" monadic yields where the developer forgot the decorator.
_do_context_active: ContextVar[bool] = ContextVar("_do_context_active", default=False)


def _check_do_context(instance: object, decorator_hint: str = "@do") -> None:
    """
    Shared leak detector: warns if a monadic type is constructed inside
    a generator that lacks a @do / @do_option decorator.

    Called from Ok.__init__, Err.__init__, Some.__init__.
    NOT called from _NothingType (singleton — created at import time).

    Args:
        instance: The monadic instance being constructed (for its class name).
        decorator_hint: Which decorator the warning should suggest ("@do" or "@do_option").
    """
    if _do_context_active.get():
        return  # We're inside a proper @do context — nothing to warn about.

    frame = inspect.currentframe()
    # Walk two frames up: _check_do_context → __init__ → caller
    if frame and frame.f_back and frame.f_back.f_back:
        caller = frame.f_back.f_back
        # CO_GENERATOR = 0x20
        if caller.f_code.co_flags & 0x20:
            warnings.warn(
                f"Resolute type {type(instance).__name__} created inside generator "
                f"'{caller.f_code.co_name}' without {decorator_hint} decorator. "
                f"This will return a generator object instead of a Result/Option. "
                f"Did you forget to add {decorator_hint}()?",
                RuntimeWarning,
                stacklevel=3,
            )
