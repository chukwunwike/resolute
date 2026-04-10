"""
Service layer — wraps the raw database module with explicit_result.
This is where @safe converts real exceptions into Result types.
"""

from explicit_result import safe, Ok, Err, Result, Some, Nothing, Option
from integration_app import database


# --- Wrapped database calls using @safe ---

@safe(catch=KeyError)
def find_user(user_id: int) -> dict:
    """KeyError from database.get_user becomes Err(KeyError)."""
    return database.get_user(user_id)


@safe(catch=KeyError)
def find_product(sku: str) -> dict:
    """KeyError from database.get_product becomes Err(KeyError)."""
    return database.get_product(sku)


@safe(catch=(ValueError, KeyError))
def process_payment(user_id: int, amount: float) -> dict:
    """ValueError (insufficient funds) or KeyError (user not found) become Err."""
    return database.charge_user(user_id, amount)


@safe(catch=FileNotFoundError)
def load_config(path: str) -> dict:
    """FileNotFoundError becomes Err."""
    return database.read_config(path)


@safe(catch=ZeroDivisionError)
def apply_discount(price: float, percent: float) -> float:
    """ZeroDivisionError becomes Err."""
    return database.calculate_discount(price, percent)


# --- Business logic using Result chaining ---

def check_stock(product: dict) -> Result[dict, str]:
    """Returns Err if product is out of stock."""
    if product["stock"] <= 0:
        return Err(f"'{product['name']}' is out of stock")
    return Ok(product)


def lookup_user_email(user_id: int) -> Option[str]:
    """Returns Some(email) or Nothing."""
    result = find_user(user_id)
    if result.is_ok():
        return Some(result.unwrap()["email"])
    return Nothing
