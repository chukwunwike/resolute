import sys
import os

# Add root directory to path for resolute
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("="*60)
print("ONLINE COMPARISON: DATABASE UPDATE FAILURES")
print("="*60)

print("\n--- RUNNING LEGACY (DOCUMENTED AS BROKEN) ---")
import legacy.db_handler as legacy
print("Alice: ", legacy.update_user_balance("user_1", 10))
print("Bob (0):", legacy.update_user_balance("user_2", 0))    # Swallows ZeroDivisionError
print("None:  ", legacy.update_user_balance("user_99", 10)) # Swallows KeyError

print("\n--- RUNNING MODERN (RESOLUTE HARDENED) ---")
# We reload to ensure fresh state if needed, though they use their own imports
import modern.db_handler as modern
print("Alice: ", modern.update_user_balance("user_1", 10))
print("Bob (0):", modern.update_user_balance("user_2", 0))    # Explicitly shows error
print("None:  ", modern.update_user_balance("user_99", 10)) # Explicitly shows error
