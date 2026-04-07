"""
tests/test_integration.py
Mock frameworks showing that `resolute` works flawlessly within 
ecosystems like FastAPI and Pydantic.
"""
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from resolute import Ok, Err, Result

app = FastAPI()

class Item(BaseModel):
    id: int
    name: str

def fetch_item(item_id: int) -> Result[Item, str]:
    if item_id == 404:
        return Err("Item not found in database")
    return Ok(Item(id=item_id, name="Test Item"))

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int):
    result = fetch_item(item_id)
    
    # Demonstrating how Result elegantly unpacks into FastAPI HTTPExceptions
    if result.is_err():
        raise HTTPException(status_code=404, detail=result.unwrap_err())
        
    # FastAPI can directly serialize the Pydantic models extracted
    return result.unwrap()

client = TestClient(app)

def test_fastapi_success_integration():
    """Test successful unpacking of an Ok item."""
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Test Item"}

def test_fastapi_failure_integration():
    """Test correctly piping an Err into a 404 response."""
    response = client.get("/items/404")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found in database"}
