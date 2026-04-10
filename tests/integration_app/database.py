"""
Database layer — raises real exceptions.
No explicit_result imports here. This is pure, legacy Python code.
"""

import json

# Simulated in-memory "database"
_USERS = {
    1: {"name": "Archy", "email": "archy@example.com", "balance": 150.00},
    2: {"name": "Chuks", "email": "chuks@example.com", "balance": 20.00},
}

_PRODUCTS = {
    "LAPTOP": {"name": "Laptop Pro", "price": 999.99, "stock": 3},
    "MOUSE": {"name": "Wireless Mouse", "price": 29.99, "stock": 0},  # Out of stock!
    "KEYBOARD": {"name": "Mech Keyboard", "price": 79.99, "stock": 10},
}


def get_user(user_id: int) -> dict:
    """Raises KeyError if user doesn't exist."""
    return _USERS[user_id]  # Will raise KeyError for unknown IDs


def get_product(sku: str) -> dict:
    """Raises KeyError if product doesn't exist."""
    return _PRODUCTS[sku]  # Will raise KeyError for unknown SKUs


def charge_user(user_id: int, amount: float) -> dict:
    """Raises ValueError if insufficient balance."""
    user = _USERS[user_id]
    if amount > user["balance"]:
        raise ValueError(
            f"Insufficient balance: {user['name']} has ${user['balance']:.2f}, "
            f"but ${amount:.2f} is required"
        )
    user["balance"] -= amount
    return {"transaction_id": f"TXN-{user_id}-{int(amount*100)}", "charged": amount}


def read_config(path: str) -> dict:
    """Raises FileNotFoundError for missing files, json.JSONDecodeError for bad JSON."""
    with open(path, "r") as f:
        return json.load(f)


def calculate_discount(price: float, discount_percent: float) -> float:
    """Raises ZeroDivisionError if called incorrectly."""
    if discount_percent == 100:
        raise ZeroDivisionError("Cannot apply 100% discount — results in zero price")
    return price * (1 - discount_percent / 100)
