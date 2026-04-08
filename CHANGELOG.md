# Changelog

## 0.3.0

### Added
- **Pydantic v2 support**: `Option[T]` and `Result[T, E]` work as Pydantic model fields
  with automatic validation and serialization
- **FastAPI integration**: `resolute.integrations.fastapi.unwrap_or_http()` converts
  `Result`/`Option` to `HTTPException` responses
- **Benchmark suite**: `benchmarks/` directory with `pytest-benchmark` tests proving
  ~300ns overhead per operation
- `Result.from_optional(value, error)` — bridge nullable values to `Result`
- `Option` identity optimizations (`is` checks for `Nothing` singleton)

### Changed
- Upgraded project status from Alpha to Beta
- Build now excludes `integration_app/`, `benchmarks/`, `examples/` from wheel
- FastAPI import is now guarded with a clear `ImportError` message

### Fixed
- Pydantic serializer signature compatibility with `pydantic-core`

## 0.2.0

### Added
- `@do()` decorator — generator-based do-notation for `Result`
- `@do_option()` decorator — do-notation for `Option`
- `ContextError` — error context propagation with `root_cause` and `chain()`
- `Result.context(msg)` and `Result.with_context(f)` — error wrapping
- `Result.root_cause()` — traverse `ContextError` chains
- Async helpers: `from_awaitable`, `map_async`, `and_then_async`
- CI badge in README
- Hashability documentation and immutability warnings

## 0.1.0 (initial release)

### Added
- `Result[T, E]` type with `Ok` and `Err` variants
- `Option[T]` type with `Some` and `Nothing` variants
- Full method suite: `map`, `map_err`, `and_then`, `or_else`, `and_`, `or_`,
  `unwrap`, `unwrap_or`, `unwrap_or_else`, `unwrap_or_raise`, `expect`, `expect_err`,
  `map_or`, `map_or_else`, `is_ok_and`, `is_err_and`, `ok`, `err`, `zip`, `flatten`,
  `filter`, `ok_or`, `ok_or_else`
- `@safe` decorator with forbidden exception enforcement
- `@safe_async` decorator for async functions
- Combinators: `collect`, `collect_all`, `partition`, `sequence`,
  `transpose`, `transpose_result`, `flatten_result`
- Python 3.10+ structural pattern matching via `__match_args__`
- Full `__hash__` and `__eq__` — Results usable in sets and as dict keys
- `__iter__` support — Results and Options are iterable
- `__bool__` semantics — Ok/Some are truthy, Err/Nothing are falsy
- `py.typed` marker for mypy/pyright (PEP 561)
- Zero runtime dependencies
- Verified: 550,120,301 adversarial assertions — zero defects
