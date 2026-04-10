import pytest
import asyncio
from explicit_result import Some, Nothing, Option
from explicit_result import from_optional_async, map_option_async, and_then_option_async

@pytest.mark.asyncio
async def test_from_optional_async():
    async def get_val():
        await asyncio.sleep(0.01)
        return 42

    async def get_none():
        await asyncio.sleep(0.01)
        return None

    assert await from_optional_async(get_val()) == Some(42)
    assert await from_optional_async(get_none()) == Nothing

@pytest.mark.asyncio
async def test_map_option_async():
    async def async_double(x):
        await asyncio.sleep(0.01)
        return x * 2

    assert await map_option_async(Some(10), async_double) == Some(20)
    assert await map_option_async(Nothing, async_double) == Nothing

@pytest.mark.asyncio
async def test_and_then_option_async():
    async def async_some(x):
        await asyncio.sleep(0.01)
        return Some(x + 1)
    
    async def async_nothing(x):
        await asyncio.sleep(0.01)
        return Nothing

    assert await and_then_option_async(Some(10), async_some) == Some(11)
    assert await and_then_option_async(Some(10), async_nothing) == Nothing
    assert await and_then_option_async(Nothing, async_some) == Nothing
