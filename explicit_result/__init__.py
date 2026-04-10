"""
explicit_result
~~~~~~~~~
Result and Option types for Python.

Zero dependencies. Fully typed. Python 3.9+.

    from explicit_result import Ok, Err, Result, Some, Nothing, Option
    from explicit_result import safe, safe_async
    from explicit_result import collect, collect_all, partition, transpose

Quick start:

    def divide(a: float, b: float) -> Result[float, str]:
        if b == 0:
            return Err("division by zero")
        return Ok(a / b)

    result = divide(10, 2)
    print(result)           # Ok(5.0)

    value = result.unwrap_or(0.0)
    print(value)            # 5.0

    result.map(lambda x: x * 2)       # Ok(10.0)
    result.and_then(lambda x: Ok(x))  # Ok(5.0)

Safe decorator:

    @safe(catch=ValueError)
    def parse(s: str) -> int:
        return int(s)

    parse("42")   # Ok(42)
    parse("abc")  # Err(ValueError(...))

Pattern matching (Python 3.10+):

    match result:
        case Ok(value):
            print(f"Success: {value}")
        case Err(error):
            print(f"Failed: {error}")
"""

# Core types
from ._result import Result, Ok, Err
from ._option import Option, Some, Nothing, _NothingType

# Decorators
from ._decorators import safe, safe_async

# Combinators
from ._combinators import (
    collect,
    collect_all,
    partition,
    flatten_result,
    flatten_option,
    sequence,
    transpose,
    transpose_result,
)

# Exceptions
from ._exceptions import UnwrapError, SafeDecoratorError

# Context propagation
from ._context import ContextError

# Async helpers
from ._async_helpers import (
    from_awaitable,
    map_async,
    and_then_async,
    from_optional_async,
    map_option_async,
    and_then_option_async,
)

# Do-notation
from ._do import do, do_option

__all__ = [
    # Result
    "Result",
    "Ok",
    "Err",
    # Option
    "Option",
    "Some",
    "Nothing",
    # Decorators
    "safe",
    "safe_async",
    # Combinators
    "collect",
    "collect_all",
    "partition",
    "flatten_result",
    "flatten_option",
    "sequence",
    "transpose",
    "transpose_result",
    # Exceptions
    "UnwrapError",
    "SafeDecoratorError",
    # Context propagation
    "ContextError",
    # Async helpers
    "from_awaitable",
    "map_async",
    "and_then_async",
    "from_optional_async",
    "map_option_async",
    "and_then_option_async",
    # Do-notation
    "do",
    "do_option",
]

__version__ = "0.3.1"
__author__ = "explicit_result contributors"
__license__ = "MIT"

