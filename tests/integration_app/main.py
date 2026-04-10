"""
Main entrypoint — runs 8 real-world scenarios that trigger
actual Python exceptions across module boundaries.
Proves explicit_result catches every one without a single try/except in this file.
"""

import sys
import os

# Add parent directory so explicit_result can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from explicit_result import collect, collect_all, partition
from integration_app.services import (
    find_user, find_product, process_payment,
    load_config, apply_discount, check_stock,
    lookup_user_email,
)


def header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def scenario(num: int, desc: str) -> None:
    print(f"\n  [{num}] {desc}")


def run_all_scenarios():
    header("RESOLUTE INTEGRATION TEST: Real Exceptions, Real Safety")
    passed = 0
    failed = 0

    # ------------------------------------------------------------------
    scenario(1, "Find a user that EXISTS (KeyError should NOT fire)")
    result = find_user(1)
    if result.is_ok() and result.unwrap()["name"] == "Archy":
        print(f"      PASS -> {result}")
        passed += 1
    else:
        print(f"      FAIL -> {result}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(2, "Find a user that DOES NOT EXIST (KeyError -> Err)")
    result = find_user(999)
    if result.is_err() and isinstance(result.unwrap_err(), KeyError):
        print(f"      PASS -> Caught KeyError: {result.unwrap_err()}")
        passed += 1
    else:
        print(f"      FAIL -> {result}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(3, "Buy a product that is IN STOCK (full pipeline)")
    result = (
        find_product("KEYBOARD")
        .map_err(lambda e: f"Product not found: {e}")
        .and_then(check_stock)
        .map(lambda p: p["price"])
    )
    if result.is_ok() and result.unwrap() == 79.99:
        print(f"      PASS -> Price is ${result.unwrap()}")
        passed += 1
    else:
        print(f"      FAIL -> {result}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(4, "Buy a product that is OUT OF STOCK (stock check -> Err)")
    result = (
        find_product("MOUSE")
        .map_err(lambda e: f"Product not found: {e}")
        .and_then(check_stock)
    )
    if result.is_err() and "out of stock" in result.unwrap_err():
        print(f"      PASS -> {result.unwrap_err()}")
        passed += 1
    else:
        print(f"      FAIL -> {result}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(5, "Buy a product that DOES NOT EXIST (KeyError -> Err)")
    result = find_product("NONEXISTENT")
    if result.is_err() and isinstance(result.unwrap_err(), KeyError):
        print(f"      PASS -> Caught KeyError: {result.unwrap_err()}")
        passed += 1
    else:
        print(f"      FAIL -> {result}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(6, "Pay with INSUFFICIENT BALANCE (ValueError -> Err)")
    result = process_payment(2, 500.00)  # Chuks only has $20
    if result.is_err() and isinstance(result.unwrap_err(), ValueError):
        print(f"      PASS -> {result.unwrap_err()}")
        passed += 1
    else:
        print(f"      FAIL -> {result}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(7, "Load a config file that DOES NOT EXIST (FileNotFoundError -> Err)")
    result = load_config("/nonexistent/path/config.json")
    if result.is_err() and isinstance(result.unwrap_err(), FileNotFoundError):
        print(f"      PASS -> Caught FileNotFoundError")
        passed += 1
    else:
        print(f"      FAIL -> {result}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(8, "Apply 100% discount (ZeroDivisionError -> Err)")
    result = apply_discount(99.99, 100)
    if result.is_err() and isinstance(result.unwrap_err(), ZeroDivisionError):
        print(f"      PASS -> Caught ZeroDivisionError: {result.unwrap_err()}")
        passed += 1
    else:
        print(f"      FAIL -> {result}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(9, "Option: lookup email for existing user -> Some")
    email = lookup_user_email(1)
    if email.is_some() and email.unwrap() == "archy@example.com":
        print(f"      PASS -> {email}")
        passed += 1
    else:
        print(f"      FAIL -> {email}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(10, "Option: lookup email for missing user -> Nothing")
    email = lookup_user_email(999)
    if email.is_nothing():
        print(f"      PASS -> {email}")
        passed += 1
    else:
        print(f"      FAIL -> {email}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(11, "collect: all succeed -> Ok([...])")
    results = [find_user(1), find_user(2)]
    collected = collect(results)
    if collected.is_ok() and len(collected.unwrap()) == 2:
        print(f"      PASS -> Collected {len(collected.unwrap())} users")
        passed += 1
    else:
        print(f"      FAIL -> {collected}")
        failed += 1

    # ------------------------------------------------------------------
    scenario(12, "collect: one fails -> first Err")
    results = [find_user(1), find_user(999), find_user(2)]
    collected = collect(results)
    if collected.is_err():
        print(f"      PASS -> Short-circuited on: {collected.unwrap_err()}")
        passed += 1
    else:
        print(f"      FAIL -> {collected}")
        failed += 1

    # ------------------------------------------------------------------
    # FINAL REPORT
    header("RESULTS")
    total = passed + failed
    print(f"\n  {passed}/{total} scenarios passed")
    if failed == 0:
        print("  ALL SCENARIOS PASSED -- explicit_result works as intended!\n")
    else:
        print(f"  {failed} SCENARIOS FAILED\n")
    
    return failed


if __name__ == "__main__":
    exit_code = run_all_scenarios()
    sys.exit(exit_code)
