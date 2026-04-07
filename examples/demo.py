"""
Resolute Real-World Demo: Weather Processing Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This example simulates a production data pipeline that:
1. Fetches raw JSON from a "Weather API".
2. Parases the data into a safe object.
3. Calculates an average temperature.
4. Handles missing sensors and network timeouts without any try/except blocks in core logic.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import random
import time

from resolute import Ok, Err, Result, Some, Nothing, Option, safe, collect

# --- 1. Domain Models ---

@dataclass
class Reading:
    sensor_id: str
    temp: float

@dataclass
class WeatherReport:
    city: str
    readings: List[Reading]

# --- 2. Simulated External Services ---

class WeatherAPI:
    """Simulates an unreliable external API."""
    
    def fetch_raw_data(self, city: str) -> Dict:
        """Fetch raw JSON. Might raise various exceptions."""
        # Simulate network or API errors
        if random.random() < 0.2:
            raise ConnectionError(f"Failed to reach weather service for {city}")
        
        # Simulate malformed data
        if city == "InvalidCity":
            return {"err": "Not Found"}
            
        # Success case
        return {
            "city": city,
            "data": [
                {"id": "S1", "t": 22.5},
                {"id": "S2", "t": 23.1},
                {"id": "S3", "t": None},  # Missing reading
            ]
        }

# --- 3. Functional Pipeline using Resolute ---

api = WeatherAPI()

@safe(catch=(ConnectionError, KeyError))
def fetch_from_api(city: str) -> Dict:
    """Wrapped API call. Errors become Err(Exception)."""
    return api.fetch_raw_data(city)

def parse_reading(raw: Dict) -> Option[Reading]:
    """Parse a single reading. Missing values become Nothing."""
    temp = raw.get("t")
    sensor_id = raw.get("id")
    
    if temp is None or sensor_id is None:
        return Nothing
        
    return Some(Reading(sensor_id=sensor_id, temp=temp))

def process_city_weather(city: str) -> Result[float, str]:
    """
    Main pipeline logic.
    Beautifully combines Results and Options to calculate average temp.
    """
    return (
        fetch_from_api(city)
        .map_err(lambda e: f"Network Error: {e}")
        .and_then(lambda payload: 
            Ok(payload.get("data", [])) 
            if "data" in payload 
            else Err(f"API Error: {payload.get('err', 'Unknown')}")
        )
        .map(lambda raw_list: [parse_reading(r) for r in raw_list])
        # Flatten list of Options: keep only the Some values
        .map(lambda opt_list: [r.unwrap() for r in opt_list if r.is_some()])
        .and_then(lambda readings:
            Ok(sum(r.temp for r in readings) / len(readings))
            if readings else
            Err("No valid sensor readings found")
        )
    )

# --- 4. Running the Demo ---

def run_demo():
    print("=== Resolute Production Pipeline Demo ===\n")
    cities = ["London", "Paris", "InvalidCity", "New York (Timeout Simulation)"]
    
    for city in cities:
        print(f"Processing weather for: {city}...")
        
        # We can handle the final result with a simple match-like structure
        result = process_city_weather(city)
        
        if result.is_ok():
            print(f"  [SUCCESS] Avg Temperature is {result.unwrap():.1f}C")
        else:
            print(f"  [FAILED] {result.unwrap_err()}")
            
        print("-" * 40)

if __name__ == "__main__":
    # Seed randomness for consistent demo if needed, or leave it for realism
    # random.seed(42) 
    run_demo()
