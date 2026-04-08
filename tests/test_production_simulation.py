import asyncio
import random
from dataclasses import dataclass
from typing import List, Dict, Any
import pytest
from pydantic import BaseModel, ValidationError

from fastapi import FastAPI
from fastapi.testclient import TestClient

from resolute import Ok, Err, Result, Option, Some, Nothing, safe, safe_async
from resolute.integrations.fastapi import unwrap_or_http
from resolute._context import ContextError
from resolute._combinators import partition

# ============================================================================
# Test 1: The "End-to-End FastAPI & Pydantic" Test
# Proves: Result/Option integrate seamlessly with FastAPI and Pydantic V2
# ============================================================================

app = FastAPI()

class UserPayload(BaseModel):
    id: int
    name: str
    email: str

class UserService:
    @staticmethod
    def create_user(payload: UserPayload) -> Result[Dict[str, Any], str]:
        if payload.email == "taken@example.com":
            return Err("Email already in use")
        return Ok({"user_id": payload.id, "status": "created"})

    @staticmethod
    def get_user(user_id: int) -> Option[UserPayload]:
        if user_id == 404:
            return Nothing
        return Some(UserPayload(id=user_id, name="Alice", email="alice@example.com"))

@app.post("/users")
def register_user(payload: UserPayload) -> Dict[str, Any]:
    # unwrap_or_http automatically translates an Err to an HTTPException(400)
    result = UserService.create_user(payload)
    return unwrap_or_http(result, status_code=400)

@app.get("/users/{user_id}")
def fetch_user(user_id: int) -> UserPayload:
    # unwrap_or_http automatically translates Nothing to HTTPException(404)
    opt = UserService.get_user(user_id)
    return unwrap_or_http(opt, status_code=404)

client = TestClient(app)

def test_fastapi_and_pydantic_integration():
    # 1. Successful POST (Ok is unwrapped and returned as JSON)
    resp = client.post("/users", json={"id": 1, "name": "Bob", "email": "bob@example.com"})
    assert resp.status_code == 200
    assert resp.json() == {"user_id": 1, "status": "created"}

    # 2. Failed POST (Err is caught and turned into 400)
    resp = client.post("/users", json={"id": 2, "name": "Eve", "email": "taken@example.com"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Email already in use"

    # 3. Successful GET (Some is unwrapped and returned)
    resp = client.get("/users/1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alice"

    # 4. Failed GET (Nothing is caught and turned into 404)
    resp = client.get("/users/404")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Not found"

    # 5. Pydantic validation failure (FastAPI handles this before our logic)
    resp = client.post("/users", json={"id": "not_an_int", "name": "Bob"})
    assert resp.status_code == 422


# ============================================================================
# Test 2: The "Flaky Microservice / Network Chaos" Test
# Proves: Resolute handles massive concurrency and random failures gracefully
# ============================================================================

class NetworkTimeout(Exception): pass
class BadGateway(Exception): pass

@safe_async(catch=(NetworkTimeout, BadGateway, ValueError))
async def flaky_network_call(request_id: int) -> str:
    await asyncio.sleep(0.01) # Simulate network transit

    chance = random.random()
    if chance < 0.1:
        raise NetworkTimeout(f"Req {request_id} timed out")
    elif chance < 0.2:
        raise BadGateway(f"Req {request_id} hit bad gateway")
    elif chance < 0.3:
        raise ValueError(f"Req {request_id} returned malformed JSON")
    
    return f"Success {request_id}"

@pytest.mark.asyncio
async def test_flaky_microservices_chaos():
    # Freeze randomness for deterministic testing
    random.seed(42)
    
    # Launch 100 concurrent requests
    tasks = [flaky_network_call(i) for i in range(100)]
    results: List[Result[str, Exception]] = await asyncio.gather(*tasks)
    
    # Partition them cleanly without a single try/except block
    successes, failures = partition(results)
    
    # We launched 100 requests. All should be accounted for.
    assert len(successes) + len(failures) == 100
    assert len(successes) > 60  # Around ~70% should succeed based on setup above
    assert len(failures) > 10   # Ensure failures were caught

    # Verify that the failures are exactly the exceptions we expected
    for err in failures:
        assert isinstance(err, (NetworkTimeout, BadGateway, ValueError))


# ============================================================================
# Test 3: The "Distributed Saga (Rollback)" Test
# Proves: Complex multi-step transactions can rollback and track causal chains
# ============================================================================

@dataclass
class Order:
    item: str
    qty: int

class InsufficientInventory(Exception): pass
class CreditCardDeclined(Exception): pass
class EmailServiceDown(Exception): pass

class PaymentGateway:
    @staticmethod
    def charge(amount: float) -> Result[str, Exception]:
        if amount > 100:
            return Err(CreditCardDeclined("Card limit exceeded"))
        return Ok("txn_999")

class InventorySystem:
    @staticmethod
    def reserve(item: str) -> Result[str, Exception]:
        if item == "Out of Stock Item":
            return Err(InsufficientInventory("Only 0 left"))
        return Ok("res_123")

    @staticmethod
    def rollback(reservation_id: str) -> None:
        pass # Release the hold

def process_checkout_saga(item: str, amount: float) -> Result[str, Exception]:
    """
    Step 1: Reserve Inventory
    Step 2: Charge Card (If fails -> Rollback Inventory!)
    Step 3: Send Confirmation
    """
    # Step 1
    res = InventorySystem.reserve(item).context("Failed to reserve inventory")
    if res.is_err():
        return res
    
    reservation_id = res.unwrap()

    # Step 2
    charge = PaymentGateway.charge(amount).context(f"Failed to charge for {item}")
    if charge.is_err():
        # SAGA ROLLBACK
        InventorySystem.rollback(reservation_id)
        return charge # Return the failure chain
    
    # Step 3
    # Simulating a safe email send
    email_res = Err(EmailServiceDown("SMTP unreachable")).context("Failed to send receipt")
    if email_res.is_err():
        # Note: Depending on business rules, failing to send a receipt might not
        # cancel the order, but we'll return the error here to show context chaining.
        return email_res

    return Ok("Order Complete")

def test_distributed_saga_rollback_and_context():
    # Scenario A: Inventory fails immediately
    res_a = process_checkout_saga("Out of Stock Item", 50.0)
    assert res_a.is_err()
    assert isinstance(res_a.unwrap_err(), ContextError)
    assert "Failed to reserve inventory" in str(res_a.unwrap_err())
    assert isinstance(res_a.root_cause().unwrap(), InsufficientInventory)

    # Scenario B: Card declines (triggers rollback, preserves context)
    res_b = process_checkout_saga("In Stock Item", 500.0)
    assert res_b.is_err()
    err_b = res_b.unwrap_err()
    
    assert isinstance(err_b, ContextError)
    assert "Failed to charge for In Stock Item" in str(err_b)
    assert isinstance(res_b.root_cause().unwrap(), CreditCardDeclined)
    
    # We can walk the exact chain of failure for observability/logging
    causal_chain = err_b.chain()
    assert len(causal_chain) == 2
    assert isinstance(causal_chain[0], ContextError)
    assert isinstance(causal_chain[1], CreditCardDeclined)
