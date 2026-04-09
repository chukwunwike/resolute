import json
import os
from resolute import Result, Ok, Err, Option, Some, Nothing, safe, do

@safe(catch=(FileNotFoundError, json.JSONDecodeError))
def load_config(path: str):
    """Safely loads config, capturing specific failure types."""
    with open(path, 'r') as f:
        return json.load(f)

def get_user_data(user_id: int) -> Result[dict, str]:
    """Returns a Result instead of raising for expected business missing cases."""
    db = [
        {"id": 1, "name": "Alice", "points": 100, "tasks": 5},
        {"id": 2, "name": "Bob", "points": 50, "tasks": 0},
    ]
    for user in db:
        if user["id"] == user_id:
            return Ok(user)
    return Err(f"User {user_id} not found")

@do()
def generate_report(user_id: int, config_path: str) -> Result[dict, str]:
    """
    Modern orchestrator using do-notation to flatten logic.
    Each 'yield' automatically unwraps Ok/Some and handles Err/Nothing.
    """
    # 1. Load config (converts Option-style safe output to a default if needed)
    config = yield load_config(config_path).or_else(lambda _: Ok({"theme": "light"}))
    
    # 2. Get user
    user = yield get_user_data(user_id)
    
    # 3. Calculate metrics safely
    if user["tasks"] == 0:
        return Err("Cannot calculate ratio for inactive user")
        
    ratio = user["points"] / user["tasks"]
    
    return {
        "user": user["name"],
        "efficiency": ratio,
        "theme": config.get("theme", "light")
    }

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
    
    if os.path.exists("config.json"):
        os.remove("config.json")
