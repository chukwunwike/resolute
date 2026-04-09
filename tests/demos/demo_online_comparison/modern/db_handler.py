from resolute import Result, Ok, Err, safe, do
import sys
import os

# Ensure we can import the legacy Database object to compare apples-to-apples
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from legacy.db_handler import Database

db = Database()

@do()
def update_user_balance(user_id, amount) -> Result[bool, str]:
    """
    MODERN RESOLUTE CODE:
    We use @safe to wrap the database call. This automatically converts 
    exceptions into Err objects, preserving the original error context.
    """
    # Wrap the fragile legacy method call in a safe boundary
    # We catch everything since this is an external DB call
    safe_update = safe(catch=Exception)(db.update)
    
    # In one line, we execute and propagate any error
    yield safe_update(user_id, amount)
    
    return Ok(True)

if __name__ == "__main__":
    print("="*40)
    print("RESOLUTE MODERN HANDLER")
    print("="*40)
    
    print("Updating Alice (Valid):")
    res = update_user_balance("user_1", 10)
    print(f"  Result: {res}")

    print("\nUpdating Bob (Amount 0 - Division Error):")
    res = update_user_balance("user_2", 0)
    if res.is_err():
        print(f"  Result: {res}")
