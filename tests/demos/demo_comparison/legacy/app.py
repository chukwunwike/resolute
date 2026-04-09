import json
import os

def load_config(path):
    # Smell: Returns None on failure, forcing caller to check every time
    try:
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        # Smell: Swallows all errors, no idea if it's permission or invalid JSON
        return None

def get_user_data(user_id):
    # Simulated database
    db = [
        {"id": 1, "name": "Alice", "points": 100, "tasks": 5},
        {"id": 2, "name": "Bob", "points": 50, "tasks": 0},
    ]
    # Smell: Raising exceptions for business logic
    for user in db:
        if user["id"] == user_id:
            return user
    raise ValueError(f"User {user_id} not found")

def generate_report(user_id, config_path):
    # Smell: Deep nesting and manual None-checking
    config = load_config(config_path)
    if config:
        try:
            user = get_user_data(user_id)
            # Smell: Unsafe division, no protection against tasks=0
            # Bob has 0 tasks, this will crash
            ratio = user["points"] / user["tasks"]
            
            return {
                "user": user["name"],
                "efficiency": ratio,
                "theme": config.get("theme", "light")
            }
        except ValueError as e:
            # Smell: Generic error return that loses type info
            return f"Error: {e}"
        except ZeroDivisionError:
            return "Error: Cannot calculate ratio for inactive user"
        except Exception as e:
            return f"Unexpected: {e}"
    else:
        return "Critical: Config missing or invalid"

# Example usages
if __name__ == "__main__":
    print("Normal Case:", generate_report(1, "config.json"))
    
    # Create a dummy config
    with open("config.json", "w") as f:
        json.dump({"theme": "dark"}, f)
    
    print("Normal Case (with file):", generate_report(1, "config.json"))
    print("Zero Division Case (Bob):", generate_report(2, "config.json"))
    print("Missing User Case:", generate_report(99, "config.json"))
    print("Invalid File Case:", generate_report(1, "non_existent.json"))
    
    # Cleanup config for demo
    if os.path.exists("config.json"):
        os.remove("config.json")
