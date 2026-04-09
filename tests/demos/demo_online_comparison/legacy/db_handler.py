# Source: Based on https://github.com/quantifiedcode/python-anti-patterns/
# Anti-pattern: Silent Exception Swallowing

class Database:
    def __init__(self):
        self.data = {"user_1": 100, "user_2": 200}
        self.is_connected = True

    def update(self, user_id, amount):
        if not self.is_connected:
            raise ConnectionError("Lost connection to DB")
        if user_id not in self.data:
            raise KeyError(f"User {user_id} not found")
        # Logic bug: accidental division by zero if amount is 0
        self.data[user_id] = 1000 / amount

db = Database()

def update_user_balance(user_id, amount):
    """
    DOCUMENTED BROKEN CODE:
    This function swallows all exceptions, making it impossible to know 
    why an update failed. It could be a connection error, a missing user, 
    or a logical crash (DivisionByZero).
    """
    try:
        db.update(user_id, amount)
        return True
    except:
        # Documented Anti-pattern: The 'pass' swallows the traceback!
        pass
    return False

if __name__ == "__main__":
    print("Updating Alice (Valid):", update_user_balance("user_1", 10))
    print("Updating Bob (Amount 0 - Crashes DB):", update_user_balance("user_2", 0))
    print("Updating Unknown User:", update_user_balance("user_99", 10))
    
    db.is_connected = False
    print("Updating after DB goes offline:", update_user_balance("user_1", 10))
