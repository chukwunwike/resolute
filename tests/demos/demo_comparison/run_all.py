import sys
import os
import json

# Add parent directory to path to import resolute
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def setup_config(content):
    with open("config.json", "w") as f:
        f.write(content)

def cleanup():
    if os.path.exists("config.json"):
        os.remove("config.json")

from legacy.app import generate_report as legacy_report
from modern.app import generate_report as modern_report

def run_suite(label):
    print(f"\n--- {label} ---")
    
    print("Normal User (Alice):")
    print(f"  Legacy: {legacy_report(1, 'config.json')}")
    print(f"  Modern: {modern_report(1, 'config.json')}")

    print("Inactive User (Bob):")
    print(f"  Legacy: {legacy_report(2, 'config.json')}")
    print(f"  Modern: {modern_report(2, 'config.json')}")

    print("Missing User (99):")
    print(f"  Legacy: {legacy_report(99, 'config.json')}")
    print(f"  Modern: {modern_report(99, 'config.json')}")

# Scenario 1: No file
cleanup()
run_suite("SCENARIO 1: CONFIG FILE MISSING")

# Scenario 2: Valid file
setup_config('{"theme": "dark"}')
run_suite("SCENARIO 2: VALID CONFIG (DARK THEME)")

# Scenario 3: Invalid JSON
setup_config('{invalid_json: "oops"}')
run_suite("SCENARIO 3: INVALID JSON CONFIG")

cleanup()
