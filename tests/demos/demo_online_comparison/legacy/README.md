# Documented Broken Code: Database Handler

This code implements a pattern documented as a major anti-pattern at [Python Anti-Patterns](https://github.com/quantifiedcode/python-anti-patterns/blob/master/anti_patterns/silent_exception_swallowing/index.md).

## The Bug: Silent Exception Swallowing

The `update_user_balance` function uses a bare `except:` block with `pass`. 

### Consequences:
1.  **Debugging Nightmare:** If the database crashes or the connection drops, the app just returns `False`. The developer has no stack trace to find out *where* it failed.
2.  **Inconsistent State:** If `db.update` fails halfway through a complex operation, the app proceeds as if everything is normal, but just "didn't work".
3.  **Hides Logic Bugs:** Even if the database code has a typo (like calling a non-existent method), this code will swallow it, making the bug invisible until production.
