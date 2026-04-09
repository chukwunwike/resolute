# Modern Codebase: Resolute Benefits

This codebase demonstrates how `resolute` transforms fragile, nested logic into robust, readable pipelines.

## Key Improvements

1.  **Explicit Failure (Result/Option):** `get_user_data` returns a `Result`. This signals to the developer that this operation *can* fail and must be handled.
2.  **Context-Aware Safety:** `@safe(catch=...)` captures specific exceptions (like `JSONDecodeError`) without swallowing unrelated system errors, providing a clean boundary for external I/O.
3.  **Flat Logic (Do-notation):** `generate_report` uses the `@do()` decorator. Notice there are **zero nested try/except blocks** and **no manual None checks**. The `yield` keyword handles early returns automatically if an error occurs.
4.  **Graceful Defaults:** `load_config(path).or_else(...)` allows providing a fallback value inline, keeping the main logic focused on the "happy path".
5.  **Type Safety:** Errors are first-class citizens. Instead of returning error strings, the functions return `Err` objects that preserve type information and can be matched using Python's `match` statement.
