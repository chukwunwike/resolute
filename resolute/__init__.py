"""
resolute
~~~~~~~~~
Result and Option types for Python.

Zero dependencies. Fully typed. Python 3.9+.

    from resolute import Ok, Err, Result, Some, Nothing, Option
    from resolute import safe, safe_async
    from resolute import collect, collect_all, partition, transpose

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
    sequence,
    transpose,
    transpose_result,
)

# Exceptions
from ._exceptions import UnwrapError, SafeDecoratorError

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
    "sequence",
    "transpose",
    "transpose_result",
    # Exceptions
    "UnwrapError",
    "SafeDecoratorError",
]

__version__ = "0.1.0"
__author__ = "resolute contributors"
__license__ = "MIT"
