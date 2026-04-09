# Legacy Codebase: Documented Errors

This codebase demonstrates common pitfalls in Python error handling that lead to fragile, hard-to-maintain applications.

## Identified Issues

1.  **Implicit failure (`None` returns):** `load_config` returns `None` on failure. This forces the caller to use `if config:` checks, which are easy to miss.
2.  **Swallowed Exceptions:** In `load_config`, `except Exception: return None` hides the root cause. It could be a permission error, a missing file, or malformed JSON.
3.  **Exception-only logic:** `get_user_data` raises a `ValueError` for a missing user—a common business case. This forces callers into `try/except` blocks instead of simple branching.
4.  **Fragile Calculations:** The calculation `user["points"] / user["tasks"]` is unprotected. If a user has 0 tasks (like Bob), the app crashes with `ZeroDivisionError` unless the caller specifically catches it.
5.  **Information Loss:** All errors are eventually converted into simple strings (e.g., `return f"Error: {e}"`). This makes it impossible for higher-level logic to retry or handle specific error types programmatically.
