import pytest
from pydantic import BaseModel, Field, ValidationError
from resolute import Ok, Err, Some, Nothing, Option, Result
from resolute.integrations.fastapi import unwrap_or_http
from fastapi import HTTPException

# Pydantic Model for testing
class User(BaseModel):
    id: int
    nickname: Option[str] = Nothing
    balance: Result[float, str] = Field(default_factory=lambda: Ok(0.0))

def test_pydantic_option_some():
    u = User(id=1, nickname="archy")
    assert u.nickname == Some("archy")
    assert u.model_dump()["nickname"] == "archy"

def test_pydantic_option_none():
    u = User(id=2, nickname=None)
    assert u.nickname is Nothing
    assert u.model_dump()["nickname"] is None

def test_pydantic_result_ok():
    u = User(id=3, balance={"ok": 100.0})
    assert u.balance == Ok(100.0)
    assert u.model_dump()["balance"] == {"ok": 100.0}

def test_pydantic_result_err():
    u = User(id=4, balance={"err": "unauthorized"})
    assert u.balance == Err("unauthorized")
    assert u.model_dump()["balance"] == {"err": "unauthorized"}

def test_fastapi_unwrap_ok():
    res = Ok("success")
    assert unwrap_or_http(res) == "success"

def test_fastapi_unwrap_err():
    res = Err("failed")
    with pytest.raises(HTTPException) as exc:
        unwrap_or_http(res, status_code=400)
    assert exc.value.status_code == 400
    assert exc.value.detail == "failed"

def test_fastapi_unwrap_option_some():
    opt = Some("found")
    assert unwrap_or_http(opt) == "found"

def test_fastapi_unwrap_option_nothing():
    opt = Nothing
    with pytest.raises(HTTPException) as exc:
        unwrap_or_http(opt, status_code=404)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Not found"

# Logic from reproduce_pydantic.py
class UserProfile(BaseModel):
    status: Result[str, str]
    bio: Option[str] = Nothing

def test_pydantic_profile_success():
    p = UserProfile(status=Ok("active"), bio=Some("hey"))
    assert p.status == Ok("active")
    assert p.bio == Some("hey")
    assert isinstance(p.status, Result)
    assert isinstance(p.bio, Option)

def test_pydantic_profile_dict_init():
    # Test with dict-based initialization which triggers Resolute validator
    p = UserProfile(status={"ok": "active"}, bio=None)
    assert p.status == Ok("active")
    assert p.bio is Nothing
