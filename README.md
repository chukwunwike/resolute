# explicit-result
<!--   

[![Tests](https://github.com/chukwunwike/explicit-result/actions/workflows/tests.yml/badge.svg)](https://github.com/chukwunwike/explicit-result/actions/workflows/tests.yml)
-->


> **Result and Option types for Python — zero dependencies, fully typed.**

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Typed](https://img.shields.io/badge/typed-yes-brightgreen.svg)](https://peps.python.org/pep-0561/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://chukwunwike.github.io/explicit_result/)

### [Read the Full Documentation here](https://chukwunwike.github.io/explicit_result/)

---

Python functions lie. A function typed as `-> int` might return an integer, raise a `ValueError`, raise a `ConnectionError`, or return `None` depending on conditions the caller cannot see. The type system gives you no warning. You discover the truth at runtime, usually in production.

`explicit-result` fixes this by making errors **visible in the function signature itself**.

```python
from explicit_result import Ok, Err, Result

def divide(a: float, b: float) -> Result[float, str]:
    if b == 0:
        return Err("division by zero")
    return Ok(a / b)

result = divide(10, 2)   # Ok(5.0)
result = divide(10, 0)   # Err("division by zero")
```

The signature `Result[float, str]` is a contract: *"I will give you either a float or a string error. I will not surprise you."*

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
  - [Why not exceptions?](#why-not-exceptions)
  - [Why not returning None?](#why-not-returning-none)
  - [The explicit-result philosophy](#the-explicit_result-philosophy)
- [Safety & Reliability (v0.3.1)](#safety--reliability-v031)
- [Result\[T, E\]](#resultt-e)
  - [Creating Results](#creating-results)
  - [Checking the variant](#checking-the-variant)
  - [Extracting values safely](#extracting-values-safely)
  - [Transforming the Ok value](#transforming-the-ok-value)
  - [Transforming the Err value](#transforming-the-err-value)
  - [Chaining Results](#chaining-results)
  - [Converting to Option](#converting-to-option)
  - [Pattern matching](#pattern-matching)
  - [Boolean and iteration](#boolean-and-iteration)
- [Option\[T\]](#optiont)
  - [Creating Options](#creating-options)
  - [Checking the variant](#checking-the-variant-1)
  - [Extracting values safely](#extracting-values-safely-1)
  - [Transforming values](#transforming-values)
  - [Chaining Options](#chaining-options)
  - [Converting to Result](#converting-to-result)
  - [The Nothing singleton](#the-nothing-singleton)
- [Do-Notation](#do-notation)
  - [Result with @do](#result-with-do)
  - [Option with @do\_option](#option-with-do_option)
- [Error Context](#error-context)
- [Decorators](#decorators)
  - [@safe](#safe)
  - [@safe\_async](#safe_async)
  - [What @safe will never catch](#what-safe-will-never-catch)
- [Async Helpers](#async-helpers)
- [Combinators](#combinators)
  - [collect](#collect)
  - [collect\_all](#collect_all)
  - [partition](#partition)
  - [sequence](#sequence)
  - [transpose](#transpose)
  - [transpose\_result](#transpose_result)
  - [flatten\_result](#flatten_result)
- [Real-World Patterns](#real-world-patterns)
  - [Configuration parsing](#configuration-parsing)
  - [Form validation](#form-validation)
  - [Database queries](#database-queries)
  - [HTTP API calls](#http-api-calls)
  - [Chained lookups](#chained-lookups)
- [Error Handling Philosophy](#error-handling-philosophy)
  - [What belongs in Result](#what-belongs-in-result)
  - [What should stay as exceptions](#what-should-stay-as-exceptions)
- [Type System Integration](#type-system-integration)
- [API Reference](#api-reference)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

```bash
pip install explicit-result
```

`explicit-result` has **zero dependencies**. It requires Python 3.9 or later.

For Python 3.10+ you get full structural pattern matching support automatically.

---

## Quick Start

```python
from explicit_result import Ok, Err, Result, Some, Nothing, Option, safe

# --- Result: a value or an error ---

def parse_port(raw: str) -> Result[int, str]:
    try:
        port = int(raw)
    except ValueError:
        return Err(f"Port must be an integer, got: {raw!r}")
    if not 1 <= port <= 65535:
        return Err(f"Port {port} is out of valid range (1–65535)")
    return Ok(port)

parse_port("8080")     # Ok(8080)
parse_port("abc")      # Err("Port must be an integer, got: 'abc'")
parse_port("99999")    # Err("Port 99999 is out of valid range (1–65535)")

# --- Option: a value that might not exist ---

def find_user(user_id: int) -> Option[str]:
    users = {1: "Archy", 2: "Chuks"}
    return Some(users[user_id]) if user_id in users else Nothing

find_user(1)    # Some("Archy")
find_user(99)   # Nothing

# --- @safe: wrap existing functions ---

@safe(catch=ValueError)
def parse_float(s: str) -> float:
    return float(s)

parse_float("3.14")   # Ok(3.14)
parse_float("abc")    # Err(ValueError("could not convert string to float: 'abc'"))

# Bridge nullable values
Result.from_optional(os.environ.get("PORT"), "PORT not set")
# Ok("8080") or Err("PORT not set")
```

---

## Core Concepts

### Why not exceptions?

Exceptions are Python's built-in error mechanism and they work — but they have a fundamental flaw: **they are invisible in type signatures**.

```python
# What does this function signature tell you?
def get_user(user_id: int) -> User:
    ...
```

The answer is: almost nothing about failure. This function might:
- Return a `User` object
- Raise `UserNotFoundError`
- Raise `DatabaseConnectionError`
- Raise `PermissionError`

You would only know by reading the implementation, the docstring (if it's accurate), or by getting surprised in production. The type system provides no help.

Exceptions are also **invisible to control flow tools**. A linter cannot tell you that you forgot to handle `DatabaseConnectionError`. A type checker cannot warn you that you're calling `.name` on something that might not exist. The knowledge lives in the programmer's head.

### Why not returning None?

Returning `None` for failure is tempting but loses the error reason entirely:

```python
def find_config(path: str) -> dict | None:
    ...

config = find_config("/etc/app.conf")
# config is None — but WHY? File missing? Permission denied? Invalid syntax?
# We will never know.
```

`None` is also a valid value in many contexts, which creates ambiguity. And `dict | None` still tells callers nothing about *why* the operation failed.

### The explicit-result philosophy

`explicit_result` is built on three ideas:

**1. Errors should be part of the contract.**
A function that can fail should declare it in its return type. `Result[User, DatabaseError]` says exactly what can happen. Callers must handle both cases to get the value.

**2. The API should feel native to Python.**
`explicit_result` is not a Haskell or Rust port. Every method name, every pattern, and every design choice was made to feel natural in Python code.

**3. Adopt incrementally.**
You can use `Result` in one module and plain exceptions in another. You can wrap existing exception-throwing code with `@safe`. You do not need to rewrite your entire codebase to benefit.

---

## Result[T, E]

`Result[T, E]` represents a computation that either succeeds with a value of type `T`, or fails with an error of type `E`. There are two variants: `Ok(value)` and `Err(error)`.

### Creating Results

```python
from explicit_result import Ok, Err, Result

# Success
r: Result[int, str] = Ok(42)

# Failure
r: Result[int, str] = Err("something went wrong")

# In a function
def safe_divide(a: float, b: float) -> Result[float, str]:
    if b == 0:
        return Err("cannot divide by zero")
    return Ok(a / b)
```

The type parameters are optional but strongly recommended. With `Result[int, str]`, both mypy and pyright know that the Ok value is an `int` and the Err value is a `str`. Without them, type inference still works but provides less precision.

---

### Checking the variant

```python
r = Ok(42)

r.is_ok()   # True
r.is_err()  # False

r = Err("bad")

r.is_ok()   # False
r.is_err()  # True
```

For conditional checks that also inspect the value:

```python
# is_ok_and — True only if Ok AND value satisfies predicate
Ok(10).is_ok_and(lambda x: x > 5)    # True
Ok(2).is_ok_and(lambda x: x > 5)     # False
Err("x").is_ok_and(lambda x: True)   # False — never calls predicate

# is_err_and — True only if Err AND error satisfies predicate
Err("bad input").is_err_and(lambda e: "input" in e)  # True
Ok(1).is_err_and(lambda e: True)                      # False
```

---

### Extracting values safely

**`.unwrap()`** — Returns the Ok value. Raises `UnwrapError` if the result is Err. Use this only when you are logically certain the result is Ok, for example immediately after an `is_ok()` check, or in tests.

```python
Ok(42).unwrap()     # 42
Err("x").unwrap()   # raises UnwrapError: "Called unwrap() on an Err value: 'x'"
```

**`.unwrap_or(default)`** — Returns the Ok value, or the provided default if Err. The default is always evaluated, even if the result is Ok. If computing the default is expensive, use `unwrap_or_else`.

```python
Ok(42).unwrap_or(0)      # 42
Err("x").unwrap_or(0)    # 0
```

**`.unwrap_or_else(f)`** — Returns the Ok value, or calls `f` with the error and returns the result. The function `f` is only called when the result is Err.

```python
Err("file not found").unwrap_or_else(lambda e: f"default (reason: {e})")
# "default (reason: file not found)"

Ok(42).unwrap_or_else(lambda e: 0)   # 42  (f is never called)
```

**`.unwrap_or_raise(exc)`** — Returns the Ok value, or raises the given exception. Useful when you want to convert an Err back into a specific exception at a boundary.

```python
result.unwrap_or_raise(HTTPException(status_code=404))
```

**`.unwrap_err()`** — Returns the Err value. Raises `UnwrapError` if the result is Ok. Primarily useful in tests.

```python
Err("bad").unwrap_err()   # "bad"
Ok(1).unwrap_err()        # raises UnwrapError
```

**`.expect(message)`** — Like `.unwrap()` but includes a custom message in the `UnwrapError`. Use this to document *why* a value must be Ok at this point.

```python
config = load_config().expect(
    "Config must be loadable at startup — check your environment variables"
)
```

**`.expect_err(message)`** — Like `.unwrap_err()` but with a custom message.

---

### Transforming the Ok value

**`.map(f)`** — Applies `f` to the Ok value. Returns a new Ok with the result. If the result is Err, it is returned unchanged — `f` is never called.

```python
Ok(5).map(lambda x: x * 2)          # Ok(10)
Ok("hello").map(str.upper)           # Ok("HELLO")
Err("bad").map(lambda x: x * 2)     # Err("bad")  — f not called
```

**`.map_or(default, f)`** — Applies `f` to Ok value, or returns `default` for Err.

```python
Ok(5).map_or(0, lambda x: x * 2)     # 10
Err("bad").map_or(0, lambda x: x * 2)  # 0
```

**`.map_or_else(default_f, f)`** — Applies `f` to Ok, or calls `default_f` with the error for Err. Both functions are only called when their case applies.

```python
result.map_or_else(
    lambda e: f"Error: {e}",   # called if Err
    lambda v: f"Value: {v}"    # called if Ok
)
```

---

### Transforming the Err value

**`.map_err(f)`** — Applies `f` to the Err value. Returns a new Err with the result. If the result is Ok, it is returned unchanged — `f` is never called.

```python
Err("not found").map_err(str.upper)         # Err("NOT FOUND")
Err(404).map_err(lambda code: f"HTTP {code}")  # Err("HTTP 404")
Ok(42).map_err(str.upper)                   # Ok(42)  — f not called
```

This is useful for converting between error types — for example, converting a low-level `OSError` into a domain-specific error type.

---

### Chaining Results

The most powerful feature of `Result`. Chaining lets you write sequential logic that can fail at any step, without nested try/except blocks.

**`.and_then(f)`** — The core composition operator. If the result is Ok, calls `f` with the value and returns whatever `f` returns (which must itself be a `Result`). If the result is Err, returns it unchanged — `f` is never called.

This is also known as `flatmap` or `bind` in other languages.

```python
def parse_int(s: str) -> Result[int, str]:
    try:
        return Ok(int(s))
    except ValueError:
        return Err(f"not a number: {s!r}")

def ensure_positive(n: int) -> Result[int, str]:
    return Ok(n) if n > 0 else Err(f"must be positive, got {n}")

def double(n: int) -> Result[int, str]:
    return Ok(n * 2)

# Chaining all three:
result = (
    parse_int("5")
    .and_then(ensure_positive)
    .and_then(double)
)
# Ok(10)

result = (
    parse_int("-3")
    .and_then(ensure_positive)   # short-circuits here with Err("must be positive, got -3")
    .and_then(double)            # never called
)
# Err("must be positive, got -3")

result = (
    parse_int("abc")             # short-circuits here with Err("not a number: 'abc'")
    .and_then(ensure_positive)   # never called
    .and_then(double)            # never called
)
# Err("not a number: 'abc'")
```

**`.or_else(f)`** — The recovery operator. If the result is Err, calls `f` with the error and returns whatever `f` returns (a `Result`). If the result is Ok, returns it unchanged.

```python
# Try primary source, fall back to secondary
def get_from_cache(key: str) -> Result[str, str]: ...
def get_from_database(key: str) -> Result[str, str]: ...

value = (
    get_from_cache("user:1")
    .or_else(lambda e: get_from_database("user:1"))
    .unwrap_or("default")
)
```

**`.and_(other)`** — Returns `other` if self is Ok, otherwise returns self (the Err). Useful when you want to sequence operations but only care about the second result.

```python
Ok(1).and_(Ok(2))        # Ok(2)
Err("x").and_(Ok(2))     # Err("x")  — other is discarded
Ok(1).and_(Err("y"))     # Err("y")
```

**`.or_(other)`** — Returns self if Ok, otherwise returns `other`. A simple fallback.

```python
Ok(1).or_(Ok(99))        # Ok(1)
Err("x").or_(Ok(99))     # Ok(99)
Err("x").or_(Err("y"))   # Err("y")
```

---

### Converting to Option

**`.ok()`** — Converts to `Option`. Ok(v) becomes Some(v), Err becomes Nothing. The error value is discarded.

```python
Ok(42).ok()     # Some(42)
Err("x").ok()   # Nothing
```

**`.err()`** — Converts to `Option`. Err(e) becomes Some(e), Ok becomes Nothing.

```python
Err("x").err()  # Some("x")
Ok(42).err()    # Nothing
```

---

### Pattern matching

On Python 3.10+, `Result` supports structural pattern matching via `match`:

```python
result = divide(10, 2)

match result:
    case Ok(value):
        print(f"Success: {value}")
    case Err(error):
        print(f"Failed: {error}")
```

This is exhaustive — if you handle both `Ok` and `Err`, the type checker knows that every case is covered.

---

### Explicit Checks (Breaking in v0.3.1)

In v0.3.1, `Result` and `Option` **no longer support implicit boolean evaluation**. Using `if result:` will raise a `RuntimeError`. This prevents subtle bugs where a container carrying a falsy value (like `Ok(False)`) is misinterpreted.

You must use explicit methods:

```python
result = parse_int("42")

# REQUIRED: Use .is_ok() or .is_err()
if result.is_ok():
    value = result.unwrap()
else:
    value = 0
```

`Result` still supports iteration. `Ok(v)` yields `v` once. `Err` yields nothing. 
This is useful for flattening a list of results:

```python
results = [Ok(1), Err("skip"), Ok(3), Ok(4), Err("skip")]
values = [x for r in results for x in r]
# [1, 3, 4]
```

---

## Option[T]

`Option[T]` represents a value that may or may not exist. It is an explicit, type-safe alternative to returning `None`. There are two variants: `Some(value)` and `Nothing`.

`Option` is the right choice when absence is expected and normal — a database record that might not exist, a dictionary key that might be missing, a user preference that might not be set. In these cases, the absence is not an error; it is a valid outcome.

For cases where absence is caused by a failure you want to explain, use `Result` instead.

### Creating Options

```python
from explicit_result import Some, Nothing, Option

# Wrapping a value
o: Option[int] = Some(42)

# SAFE — None becomes Nothing
o = Option.of(user.email)   # Nothing if email is None

# FOOTGUN — None becomes Some(None)
o = Some(user.email)        # Some(None) — is_some() returns True!

# Representing absence
o: Option[int] = Nothing

# In a function
def get_config_value(key: str) -> Option[str]:
    env = {"HOST": "localhost", "PORT": "8080"}
    return Some(env[key]) if key in env else Nothing
```

---

### Checking the variant

```python
Some(1).is_some()     # True
Some(1).is_nothing()  # False
Nothing.is_some()     # False
Nothing.is_nothing()  # True

# With a predicate
Some(4).is_some_and(lambda x: x > 3)   # True
Some(2).is_some_and(lambda x: x > 3)   # False
Nothing.is_some_and(lambda x: True)    # False — predicate never called
```

---

### Extracting values safely

The same family of methods as `Result`, adapted for `Option`:

```python
Some(42).unwrap()           # 42
Nothing.unwrap()            # raises UnwrapError

Some(1).unwrap_or(99)       # 1
Nothing.unwrap_or(99)       # 99

Some(1).unwrap_or_else(lambda: expensive_default())   # 1 (function not called)
Nothing.unwrap_or_else(lambda: expensive_default())   # result of function

Nothing.unwrap_or_raise(KeyError("config key missing"))

Some(1).expect("user session must exist")   # 1
Nothing.expect("user session must exist")   # raises UnwrapError with your message
```

---

### Transforming values

**`.map(f)`** — Applies `f` to the Some value. Nothing passes through unchanged.

```python
Some("hello").map(str.upper)  # Some("HELLO")
Nothing.map(str.upper)        # Nothing
```

**`.map_or(default, f)`** and **`.map_or_else(default_f, f)`** — Identical in behaviour to the `Result` equivalents.

**`.filter(predicate)`** — Returns the Some value if the predicate is True, otherwise Nothing.

```python
Some(10).filter(lambda x: x > 5)   # Some(10)
Some(3).filter(lambda x: x > 5)    # Nothing
Nothing.filter(lambda x: True)     # Nothing
```

---

### Chaining Options

**`.and_then(f)`** — If Some, calls `f` with the value and returns the result (which must be an `Option`). If Nothing, returns Nothing.

```python
def lookup_email(user_id: int) -> Option[str]:
    emails = {1: "archy@example.com"}
    return Some(emails[user_id]) if user_id in emails else Nothing

Some(1).and_then(lookup_email)    # Some("archy@example.com")
Some(99).and_then(lookup_email)   # Nothing
Nothing.and_then(lookup_email)    # Nothing  — f never called
```

**`.or_else(f)`** — If Nothing, calls `f` and returns the result. If Some, returns self.

```python
Nothing.or_else(lambda: Some("default"))   # Some("default")
Some(1).or_else(lambda: Some(99))          # Some(1)
```

**`.zip(other)`** — Combines two Some values into a Some tuple. If either is Nothing, returns Nothing.

```python
Some(1).zip(Some("a"))   # Some((1, "a"))
Some(1).zip(Nothing)     # Nothing
Nothing.zip(Some("a"))   # Nothing
```

**`.flatten()`** — Flattens `Option[Option[T]]` into `Option[T]`.

```python
Some(Some(42)).flatten()   # Some(42)
Some(Nothing).flatten()    # Nothing
Nothing.flatten()          # Nothing
```

**`.and_(other)`** and **`.or_(other)`** — Identical in pattern to the `Result` equivalents.

---

### Converting to Result

**`.ok_or(error)`** — Converts to `Result`. Some(v) becomes Ok(v), Nothing becomes Err(error).

```python
Some(42).ok_or("not found")   # Ok(42)
Nothing.ok_or("not found")    # Err("not found")
```

**`.ok_or_else(error_f)`** — Like `.ok_or` but the error is computed lazily.

```python
Nothing.ok_or_else(lambda: compute_error_context())
```

---

### The Nothing singleton

`Nothing` is a singleton. There is only one `Nothing` in memory, regardless of how many times you use it. This means `is` comparisons work correctly:

```python
result = find_user(99)

if result is Nothing:
    print("user not found")
```

It also means `Nothing == Nothing` is always True, and `Nothing is Nothing` is always True.

---

## Do-Notation

Unlike some other libraries, `explicit-result`'s do-notation **fully supports branching logic** (if/else), loops, and early returns, as it leverages standard Python generators.

> [!IMPORTANT]
> **Safety Guard (v0.3.1)**: If you use `yield` inside a function but forget the `@do` or `@do_option` decorator, explicit-result will issue a `RuntimeWarning` at runtime to prevent you from accidentally returning a silent generator object.


### Result with @do

Yield a `Result` to unwrap its value. If it's an `Err`, the generator immediately short-circuits and returns that `Err`.

```python
# TYPE CHECKER NOTE:
# Always annotate the return type explicitly — pyright and mypy cannot
# infer it from the generator body.
#
# WORKS:
@do()
def get_profile() -> Result[dict, str]:   # ← required
    user = yield fetch_user()
    return user

# BREAKS type inference (checker sees Generator[...], not Result):
@do()
def get_profile():    # ← no annotation = no narrowing inside body
    user = yield fetch_user()
    return user
```

```python
from explicit_result import do, Ok, Err, Result

def fetch_user() -> Result[dict, str]: ...
def fetch_profile(uid: int) -> Result[dict, str]: ...

@do()
def get_user_profile() -> Result[dict, str]:
    user = yield fetch_user()            # Returns dict if Ok, short-circuits if Err
    profile = yield fetch_profile(user["id"])
    return {**user, **profile}           # Returns Ok({ ... }) automatically
```

### Option with @do_option

The same syntax works for `Option` using `@do_option()`. Yielding `Nothing` immediately returns `Nothing`.

```python
# TYPE CHECKER NOTE:
# Always annotate the return type explicitly — pyright and mypy cannot
# infer it from the generator body.
#
# WORKS:
@do_option()
def get_profile() -> Option[dict]:   # ← required
    user = yield fetch_user()
    return user

# BREAKS type inference (checker sees Generator[...], not Option):
@do_option()
def get_profile():    # ← no annotation = no narrowing inside body
    user = yield fetch_user()
    return user
```

```python
from explicit_result import do_option, Some, Nothing, Option

@do_option()
def get_leader_email(user_id: int) -> Option[str]:
    user = yield get_user(user_id)
    dept = yield get_dept(user["dept_id"])
    leader = yield get_leader(dept["lead_id"])
    return leader["email"]               # Returns Some(...) automatically
```

---

## Error Context

When an error propagates up the call stack, you often want to add context to explain *where* the error happened, without losing the original root cause. `explicit_result` provides `.context()` and `.with_context()`.

```python
from explicit_result import Ok, Err, Result

def read_file(path: str) -> Result[str, str]:
    return Err("Permission denied")

def load_config() -> Result[str, Exception]:
    return read_file("/etc/config.json").context("Failed to load configuration")

result = load_config()
# Err(ContextError("Failed to load configuration"))
```

Under the hood, `ContextError` wraps the original error using Python's `__cause__` mechanism. If you `raise result.unwrap_err()`, Python will print a standard traceback showing:

```text
ContextError: Failed to load configuration

The above exception was the direct cause of the following exception:
...
```

You can also use `.with_context(lambda e: ...)` if the context message is expensive to compute, as it will only execute if the `Result` is `Err`.

Type note: `.context()` changes the error type from `E` to `ContextError`.

If you need to access the original error downstream, you can use the **`.root_cause()`** helper on the `Result` (returns an `Option`) or the **`.root_cause`** property on the `ContextError`.

# On Result:
orig = result.root_cause().unwrap_or("no error")

# On ContextError:
try:
    result.unwrap()
except ContextError as e:
    print(f"Failed at: {e.message}")
    print(f"Original cause: {e.root_cause}")
```

---

## Diagnostic Visibility

explicit-result v0.3.1 introduces "Hybrid Representation" for errors. You get immediate diagnostic depth without any boilerplate.

### 1. The Verbose Default (`print`)
When you `print(result)` or convert it to a string, explicit-result extracts the **full stack trace** from where the error originated.

```python
# Output if result is Err:
Err(ValueError: invalid input)
Traceback (most recent call last):
  File "logic.py", line 42, in safe_func
    return 1 / 0
ZeroDivisionError: division by zero
```

### 2. The Concise Debug View (`repr`)
When viewing results in a debugger, list, or log, you get a compact summary with the **exact file and line**.

```python
# Output of repr(result):
Err(ZeroDivisionError: division by zero at logic.py:42)
```

### Configuration
You can control traceback verbosity via the `EXPLICIT_RESULT_VERBOSE_ERROR` environment variable:
- `1` (Default): Enable full tracebacks in `str()`.
- `0`: Disable tracebacks (Concise mode only).


---

## Decorators

### @safe

The `@safe` decorator wraps a function that might raise exceptions and converts it into a `Result`-returning function. It is the bridge between the existing Python ecosystem (which uses exceptions) and `explicit_result`-style code.

```python
from explicit_result import safe

@safe(catch=ValueError)
def parse_int(s: str) -> int:
    return int(s)

parse_int("42")    # Ok(42)
parse_int("abc")   # Err(ValueError("invalid literal for int() with base 10: 'abc'"))
```

The decorated function now returns `Result[int, ValueError]` instead of `int`. The exception is captured and placed in the `Err` variant. Exceptions not listed in `catch` are **re-raised normally** — they are bugs and should not be silently swallowed.

**Catching multiple exception types:**

```python
@safe(catch=(ValueError, KeyError))
def lookup_and_parse(data: dict, key: str) -> int:
    return int(data[key])
```

**Preserving metadata:** `@safe` uses `functools.wraps`, so the original function's `__name__`, `__doc__`, and `__module__` are preserved.

---

### @safe_async

The async equivalent of `@safe`. Wraps an `async def` function.

```python
from explicit_result import safe_async

@safe_async(catch=ConnectionError)
async def fetch_data(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()

# Returns Awaitable[Result[bytes, ConnectionError]]
result = await fetch_data("https://api.example.com/data")

match result:
    case Ok(data):
        process(data)
    case Err(error):
        log.warning(f"Fetch failed: {error}")
```

---

### What @safe will never catch

`@safe` enforces strict rules about which exceptions it will accept. These rules exist to prevent silent masking of program-termination signals and critical bugs.

**Forbidden — raises `SafeDecoratorError` at decoration time:**

| Exception | Reason |
|---|---|
| `KeyboardInterrupt` | The user pressed Ctrl+C. Catching this would prevent clean shutdown. |
| `SystemExit` | Something called `sys.exit()`. Catching this defeats the purpose. |
| `GeneratorExit` | Generator cleanup signal. Must propagate for async to work correctly. |

```python
@safe(catch=KeyboardInterrupt)   # raises SafeDecoratorError immediately
def bad_function():
    ...
```

**Warning — `catch=Exception` emits a `RuntimeWarning`:**

Catching `Exception` catches nearly everything, including `AttributeError`, `IndexError`, `TypeError` and other bugs. When you catch these and convert them to `Err`, you hide the bug from yourself.

```python
@safe(catch=Exception)   # works, but emits RuntimeWarning
def risky():
    ...
```

If you have a genuine reason to catch all exceptions, acknowledge it explicitly:

```python
@safe(catch=Exception, allow_broad=True)   # no warning
def intentionally_broad():
    ...
```

---

## Async Helpers

Mixing sync `Result` methods with `async` functions can feel clunky if you have to `await` inside `.and_then()` closures. `explicit_result` bridges this gap with its async helpers.

**`from_awaitable(awaitable)`** — Awaits an awaitable and wraps expected exceptions in `Result`.

**`map_async(result, async_func)`** — If Ok, awaits `async_func(value)` and wraps the result in `Ok`. If Err, returns the Err immediately.

**`and_then_async(result, async_func)`** — Like `map_async`, but `async_func` must return a `Result`.

```python
import asyncio
from explicit_result import Ok, Err, Result, and_then_async

async def fetch_user(uid: int) -> Result[dict, str]: ...
async def fetch_posts(user: dict) -> Result[list, str]: ...

async def get_user_posts(uid: int) -> Result[list, str]:
    user_res = await fetch_user(uid)
    return await and_then_async(user_res, fetch_posts)
```

---

## Combinators

Combinators are higher-order functions for working with collections of `Result` and `Option` values.

### collect

Turns an iterable of `Result` values into a single `Result` containing a list. Returns `Ok([...])` if all results are Ok. Returns the **first** Err encountered and stops immediately.

```python
from explicit_result import collect

collect([Ok(1), Ok(2), Ok(3)])          # Ok([1, 2, 3])
collect([Ok(1), Err("bad"), Ok(3)])     # Err("bad")  — stops here
collect([])                             # Ok([])
```

Use `collect` when you want to run multiple operations and either get all values or bail on the first failure.

---

### collect_all

**Rule of thumb: `collect` stops at the first error; `collect_all` accumulates all errors.**

Like `collect`, but gathers **all** errors instead of stopping at the first one. Returns `Ok([...])` if all results are Ok, or `Err([error1, error2, ...])` containing every error found.

```python
from explicit_result import collect_all

collect_all([Ok(1), Err("a"), Ok(3), Err("b")])
# Err(["a", "b"])

collect_all([Ok(1), Ok(2), Ok(3)])
# Ok([1, 2, 3])
```

Use `collect_all` for form validation, where you want to report every invalid field to the user in a single response rather than making them fix one error at a time.

---

### partition

Splits an iterable of `Result` values into two separate lists: one of Ok values and one of Err values.

```python
from explicit_result import partition

oks, errs = partition([Ok(1), Err("a"), Ok(2), Err("b"), Ok(3)])
# oks  = [1, 2, 3]
# errs = ["a", "b"]
```

No values are lost. Every Result ends up in exactly one list.

---

### sequence

Turns an iterable of `Option` values into a single `Option` containing a list. Returns `Some([...])` if all options are Some. Returns `Nothing` if any option is Nothing.

```python
from explicit_result import sequence

sequence([Some(1), Some(2), Some(3)])   # Some([1, 2, 3])
sequence([Some(1), Nothing, Some(3)])   # Nothing
sequence([])                            # Some([])
```

---

### transpose

Converts `Option[Result[T, E]]` into `Result[Option[T], E]`.

```python
from explicit_result import transpose

transpose(Some(Ok(42)))      # Ok(Some(42))
transpose(Some(Err("bad")))  # Err("bad")
transpose(Nothing)           # Ok(Nothing)
```

---

### transpose_result

The inverse of `transpose`. Converts `Result[Option[T], E]` into `Option[Result[T, E]]`.

```python
from explicit_result import transpose_result

transpose_result(Ok(Some(42)))  # Some(Ok(42))
transpose_result(Ok(Nothing))   # Nothing
transpose_result(Err("bad"))    # Some(Err("bad"))
```

---

### flatten_result

Flattens a nested `Result[Result[T, E], E]` into `Result[T, E]`.

```python
from explicit_result import flatten_result

flatten_result(Ok(Ok(42)))      # Ok(42)
flatten_result(Ok(Err("bad")))  # Err("bad")
flatten_result(Err("outer"))    # Err("outer")
```

---

## Real-World Patterns

### Configuration parsing

```python
from explicit_result import Ok, Err, Result, collect_all
import os

def require_env(key: str) -> Result[str, str]:
    value = os.environ.get(key)
    return Ok(value) if value is not None else Err(f"Missing required env var: {key}")

def parse_port(raw: str) -> Result[int, str]:
    try:
        port = int(raw)
    except ValueError:
        return Err(f"PORT must be an integer, got: {raw!r}")
    if not 1 <= port <= 65535:
        return Err(f"PORT {port} is out of range (1–65535)")
    return Ok(port)

def load_config() -> Result[dict, list[str]]:
    host_r = require_env("HOST")
    port_r = require_env("PORT").and_then(parse_port)
    db_r   = require_env("DATABASE_URL")

    errors = [r.unwrap_err() for r in [host_r, port_r, db_r] if r.is_err()]
    if errors:
        return Err(errors)

    return Ok({
        "host": host_r.unwrap(),
        "port": port_r.unwrap(),
        "db":   db_r.unwrap(),
    })

config = load_config()

match config:
    case Ok(cfg):
        start_server(cfg)
    case Err(errors):
        for error in errors:
            print(f"Config error: {error}")
        sys.exit(1)
```

---

### Form validation

```python
from explicit_result import Ok, Err, Result, collect_all
from dataclasses import dataclass

@dataclass
class UserForm:
    username: str
    email: str
    age: str

def validate_username(s: str) -> Result[str, str]:
    s = s.strip()
    if len(s) < 3:
        return Err("Username must be at least 3 characters")
    if not s.isalnum():
        return Err("Username must contain only letters and numbers")
    return Ok(s)

def validate_email(s: str) -> Result[str, str]:
    s = s.strip().lower()
    if "@" not in s or "." not in s.split("@")[-1]:
        return Err("Email address is not valid")
    return Ok(s)

def validate_age(s: str) -> Result[int, str]:
    try:
        age = int(s)
    except ValueError:
        return Err("Age must be a whole number")
    if not 13 <= age <= 120:
        return Err("Age must be between 13 and 120")
    return Ok(age)

def validate_form(form: UserForm) -> Result[dict, list[str]]:
    results = [
        validate_username(form.username),
        validate_email(form.email),
        validate_age(form.age),
    ]
    combined = collect_all(results)

    if combined.is_err():
        return Err(combined.unwrap_err())

    values = combined.unwrap()
    return Ok({"username": values[0], "email": values[1], "age": values[2]})

# Usage
form = UserForm(username="a", email="notanemail", age="twelve")
result = validate_form(form)

if result.is_err():
    errors = result.unwrap_err()
    # ["Username must be at least 3 characters",
    #  "Email address is not valid",
    #  "Age must be a whole number"]
```

---

### Database queries

```python
from explicit_result import Ok, Err, Result, Option, Some, Nothing, safe

# Wrap the ORM call to convert exceptions into Results
@safe(catch=(DatabaseError, TimeoutError))
def _fetch_user_row(user_id: int) -> Row | None:
    return db.execute("SELECT * FROM users WHERE id = ?", user_id).fetchone()

def get_user(user_id: int) -> Result[User, str]:
    return (
        _fetch_user_row(user_id)
        .map_err(lambda e: f"Database error: {e}")
        .and_then(lambda row:
            Ok(User.from_row(row)) if row is not None
            else Err(f"User {user_id} not found")
        )
    )

# At the call site — no try/except needed
def handle_profile_request(user_id: int) -> Response:
    return get_user(user_id).map_or_else(
        lambda error: Response({"error": error}, status=404),
        lambda user:  Response({"user": user.to_dict()}, status=200),
    )
```

### FastAPI Integration

When building REST APIs, you often need to unwrap a `Result` or `Option` and immediately raise an HTTP exception if it failed/is missing. `explicit_result` provides a non-intrusive integration for this:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from explicit_result import Result, Ok, Err
from explicit_result.integrations.fastapi import unwrap_or_http

app = FastAPI()

def get_user_from_db(user_id: int) -> Result[dict, str]:
    if user_id != 1:
        return Err("User not found in database")
    return Ok({"id": 1, "name": "Archy"})

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # If Ok, returns the user dict.
    # If Err, automatically raises HTTPException(status_code=404, detail="User not found in database")
    user = unwrap_or_http(get_user_from_db(user_id), status_code=404)
    return user
```

The integration handles both `Result` and `Option` values seamlessly.

---

### HTTP API calls

```python
import asyncio
from explicit_result import Ok, Err, Result, safe_async

@safe_async(catch=(aiohttp.ClientError, asyncio.TimeoutError))
async def _http_get(url: str) -> aiohttp.ClientResponse:
    async with aiohttp.ClientSession() as session:
        response = await session.get(url, timeout=aiohttp.ClientTimeout(total=10))
        response.raise_for_status()
        return await response.json()

async def get_weather(city: str) -> Result[str, str]:
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}"
    return (
        await _http_get(url)
    ).map(
        lambda data: data["weather"][0]["description"]
    ).map_err(
        lambda e: f"Could not fetch weather for {city!r}: {e}"
    )

# Usage
async def main():
    weather = await get_weather("Lagos")

    match weather:
        case Ok(description):
            print(f"Lagos weather: {description}")
        case Err(message):
            print(f"Error: {message}")
```

---

### Chained lookups

```python
from explicit_result import Some, Nothing, Option

users    = {1: {"name": "Archy", "dept_id": 10}}
depts    = {10: {"name": "Engineering", "lead_id": 2}}
leaders  = {2: {"name": "Chuks", "email": "chuks@company.com"}}

def get_user(uid: int) -> Option[dict]:
    return Some(users[uid]) if uid in users else Nothing

def get_dept(did: int) -> Option[dict]:
    return Some(depts[did]) if did in depts else Nothing

def get_leader(lid: int) -> Option[dict]:
    return Some(leaders[lid]) if lid in leaders else Nothing

def get_dept_lead_email(user_id: int) -> Option[str]:
    return (
        get_user(user_id)
        .and_then(lambda u:  get_dept(u["dept_id"]))
        .and_then(lambda d:  get_leader(d["lead_id"]))
        .map(lambda lead:    lead["email"])
    )

get_dept_lead_email(1)    # Some("chuks@company.com")
get_dept_lead_email(99)   # Nothing
```

Without `Option`, this same logic requires nested `if x is not None` checks or a try/except block around dictionary accesses. With chaining, the happy path reads as a linear sequence.

---

## Error Handling Philosophy

### What belongs in Result

`Result` is for **recoverable, expected failures** — things that are part of normal program operation.

- User input that doesn't match expected format
- A file that might not exist
- A network request that might time out
- A database record that might not be found
- A business rule that might not be satisfied (e.g., insufficient balance)

The key question: **"Is this failure a valid state that my program should know how to respond to?"** If yes, use `Result`.

### What should stay as exceptions

**Programming bugs.** If code reaches an `AttributeError` because you called a method on `None` you assumed was not `None`, that is a bug in your code. It should crash loudly so you can find and fix it. Wrapping it in `Err(...)` hides the bug.

**Program-termination signals.** `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`. The user or the runtime is telling the process to stop. Catching these in a `Result` would mean your program keeps running when it should have stopped.

**Unrecoverable system failures.** `MemoryError`, `RecursionError`. At this point your program may be in an undefined state. The right response is to let it crash, not to try to continue.

**Syntax and import errors.** These happen before your code runs. No runtime library can intercept them.

The table below summarises the boundary:

| Situation | Right tool |
|---|---|
| File not found | `Result` |
| Network timeout | `Result` |
| Invalid user input | `Result` |
| Business rule violation | `Result` |
| Database row not found | `Result` or `Option` |
| `AttributeError` on assumed-not-None value | Let it crash — it's a bug |
| `IndexError` from out-of-range access | Let it crash — it's a bug |
| `KeyboardInterrupt` | Let it propagate — it's intentional |
| `MemoryError` | Let it propagate — it's unrecoverable |

---

## Type System Integration

`explicit_result` ships a `py.typed` marker file (PEP 561), which tells mypy and pyright that this package provides its own type information. No plugins, no configuration, no extra installation required.

**With mypy:**

```bash
pip install mypy
mypy your_module.py
```

**With pyright:**

```bash
pip install pyright
pyright your_module.py
```

Both type checkers understand the generic type parameters and can infer the types through method chains:

```python
r: Result[int, str] = Ok(42)

# mypy/pyright knows that x is int here
r.map(lambda x: x * 2)          # inferred as Result[int, str]

# and that e is str here
r.map_err(lambda e: e.upper())  # inferred as Result[int, str]

# and that the chain result is Result[str, str]
r.map(str).map_err(str.upper)
```

---

## API Reference

### Result[T, E]

| Method | Signature | Description |
|---|---|---|
| `is_ok()` | `() -> bool` | True if Ok |
| `is_err()` | `() -> bool` | True if Err |
| `is_ok_and(f)` | `(T -> bool) -> bool` | True if Ok and predicate passes |
| `is_err_and(f)` | `(E -> bool) -> bool` | True if Err and predicate passes |
| `unwrap()` | `() -> T` | Ok value or raises UnwrapError |
| `unwrap_or(d)` | `(T) -> T` | Ok value or default |
| `unwrap_or_else(f)` | `(E -> T) -> T` | Ok value or computed default |
| `unwrap_or_raise(exc)` | `(Exception) -> T` | Ok value or raises given exception |
| `unwrap_err()` | `() -> E` | Err value or raises UnwrapError |
| `expect(msg)` | `(str) -> T` | Ok value or raises UnwrapError with message |
| `expect_err(msg)` | `(str) -> E` | Err value or raises UnwrapError with message |
| `map(f)` | `(T -> U) -> Result[U, E]` | Transform Ok value |
| `map_or(d, f)` | `(U, T -> U) -> U` | Transform Ok or return default |
| `map_or_else(df, f)` | `(E -> U, T -> U) -> U` | Transform Ok or compute from Err |
| `map_err(f)` | `(E -> F) -> Result[T, F]` | Transform Err value |
| `and_then(f)` | `(T -> Result[U, E]) -> Result[U, E]` | Chain on Ok (flatmap) |
| `or_else(f)` | `(E -> Result[T, F]) -> Result[T, F]` | Recover from Err |
| `and_(other)` | `(Result[U, E]) -> Result[U, E]` | Return other if Ok |
| `or_(other)` | `(Result[T, F]) -> Result[T, F]` | Return self if Ok, other if Err |
| `ok()` | `() -> Option[T]` | Convert to Option, dropping error |
| `err()` | `() -> Option[E]` | Convert error to Option |
| `from_optional(v, e)` | `(Optional[T], E) -> Result[T, E]` | Ok(v) if v is not None, else Err(e) |


### Option[T]

| Method | Signature | Description |
|---|---|---|
| `is_some()` | `() -> bool` | True if Some |
| `is_nothing()` | `() -> bool` | True if Nothing |
| `is_some_and(f)` | `(T -> bool) -> bool` | True if Some and predicate passes |
| `unwrap()` | `() -> T` | Some value or raises UnwrapError |
| `unwrap_or(d)` | `(T) -> T` | Some value or default |
| `unwrap_or_else(f)` | `(() -> T) -> T` | Some value or computed default |
| `unwrap_or_raise(exc)` | `(Exception) -> T` | Some value or raises given exception |
| `expect(msg)` | `(str) -> T` | Some value or raises UnwrapError with message |
| `map(f)` | `(T -> U) -> Option[U]` | Transform Some value |
| `map_or(d, f)` | `(U, T -> U) -> U` | Transform Some or return default |
| `map_or_else(df, f)` | `(() -> U, T -> U) -> U` | Transform Some or compute default |
| `filter(pred)` | `(T -> bool) -> Option[T]` | Some if predicate passes, else Nothing |
| `and_then(f)` | `(T -> Option[U]) -> Option[U]` | Chain on Some (flatmap) |
| `or_else(f)` | `(() -> Option[T]) -> Option[T]` | Recover from Nothing |
| `and_(other)` | `(Option[U]) -> Option[U]` | Return other if Some |
| `or_(other)` | `(Option[T]) -> Option[T]` | Return self if Some, other if Nothing |
| `zip(other)` | `(Option[U]) -> Option[(T, U)]` | Combine two Somes into a tuple |
| `flatten()` | `() -> Option[T]` | Flatten Option[Option[T]] |
| `ok_or(e)` | `(E) -> Result[T, E]` | Convert to Result with given error |
| `ok_or_else(f)` | `(() -> E) -> Result[T, E]` | Convert to Result with computed error |

### Combinators

| Function | Signature | Description |
|---|---|---|
| `collect(results)` | `Iterable[Result[T, E]] -> Result[List[T], E]` | All Ok or first Err |
| `collect_all(results)` | `Iterable[Result[T, E]] -> Result[List[T], List[E]]` | All Ok or all Errs |
| `partition(results)` | `Iterable[Result[T, E]] -> (List[T], List[E])` | Split into ok values and errors |
| `sequence(options)` | `Iterable[Option[T]] -> Option[List[T]]` | All Some or Nothing |
| `transpose(opt)` | `Option[Result[T, E]] -> Result[Option[T], E]` | Flip Option/Result |
| `transpose_result(r)` | `Result[Option[T], E] -> Option[Result[T, E]]` | Flip Result/Option |
| `flatten_result(r)` | `Result[Result[T, E], E] -> Result[T, E]` | Flatten nested Result |

---

## FAQ

**Can I use `explicit_result` alongside existing exception-based code?**

Yes. The `@safe` and `@safe_async` decorators exist precisely for this purpose. You can wrap any exception-throwing function and convert it to a `Result`-returning one. You do not need to adopt `explicit_result` everywhere at once.

**Does `explicit_result` work with async code?**

Yes. Use `@safe_async` for async functions. `Result` and `Option` themselves are synchronous data types — they can hold `Awaitable` values like any other value.

**What Python versions are supported?**

Python 3.9 and later. Pattern matching (the `match` statement) requires Python 3.10+ but is not required to use the library — it is an optional convenience.

**Is `explicit_result` thread-safe?**

`Ok`, `Err`, `Some`, and `Nothing` are all immutable after construction. The `Nothing` singleton is created at import time. There are no shared mutable state issues.

**Can I use `Result` values in sets or as dictionary keys?**

Yes. `Ok` and `Err` both implement `__hash__` and `__eq__`. However, like Python tuples, they are only hashable if their contained values are also hashable. For safety and predictability, it is strongly recommended to use **immutable values** inside `Result` and `Option` types.

**How is this different from just checking `if value is None`?**

Several ways. First, `Option` carries explicit type information — `Option[str]` is clearer than `str | None`. Second, absence and error are distinguished: `Option` for "might not exist," `Result` for "might fail with a reason." Third, the chaining methods (`.and_then`, `.map`, `.or_else`) let you compose optional lookups without nested `if` statements. Fourth, `Nothing` cannot be confused with a legitimate `None` value.

**Why does `@safe` warn when I use `catch=Exception`?**

Because `Exception` catches `AttributeError`, `IndexError`, `TypeError`, `NameError`, and dozens of other exceptions that indicate programming bugs, not expected failures. Catching them silently and converting them to `Err(...)` hides bugs from you. The warning is a reminder to be specific about what you expect to fail.

---

## Integrations

explicit-result provides native support for modern Python frameworks.

### FastAPI
Use `explicit_result.integrations.fastapi.unwrap_or_http` to cleanly convert `Result` or `Option` values into `HTTPException` responses.

```python
from explicit_result.integrations.fastapi import unwrap_or_http

@app.get("/users/{id}")
def read_user(id: int):
    # Returns Ok(user) or Err("not_found")
    result = user_service.find(id)
    return unwrap_or_http(result, status_code=404)
```

### Pydantic v2
`Option[T]` and `Result[T, E]` types are compatible with Pydantic v2 models out of the box. They handle validation from JSON and serialize back to standard formats.

```python
from pydantic import BaseModel
from explicit_result import Option, Result, Nothing

class UserProfile(BaseModel):
    username: str
    bio: Option[str] = Nothing  # Validates from None -> Nothing
    status: Result[str, str]    # Validates from {"ok": "..."} or {"err": "..."}
```

---

## Performance

explicit-result is optimized for minimal overhead. In micro-benchmarks, it adds fixed overhead (~300ns) compared to raw Python features.

| Pattern | Native Python | explicit-result | Overhead |
| :--- | :--- | :--- | :--- |
| **Happy Path** (Ok vs Return) | ~95ns | ~400ns | +305ns |
| **Error Path** (@safe vs try) | ~600ns | ~900ns | +300ns |

*Measured on Python 3.12.6 using `pytest-benchmark`.*

---

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request for significant changes.

When contributing:
- Add tests for any new behaviour
- Ensure the test suite passes: `python3 tests/run_tests.py`
- Follow the existing code style — type annotations on all public methods, docstrings with examples

---

## License

MIT License. See [LICENSE](LICENSE) for details.
