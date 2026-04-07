"""
Real-World Developer Scenario Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
These tests simulate the ACTUAL problems Python developers face every day.
No toy examples. Each test is a situation you'd hit in a real codebase.
"""

import asyncio
import json
import csv
import io
import os
import tempfile
from dataclasses import dataclass
from typing import List, Dict, Optional

import pytest
from resolute import (
    Ok, Err, Result, Some, Nothing, Option,
    safe, safe_async, collect, collect_all, partition,
)


# ========================================================================
# SCENARIO 1: Parsing JSON from an API response
# Every developer deals with unreliable JSON from external APIs.
# ========================================================================

class TestParsingJsonApiResponses:

    @safe(catch=(json.JSONDecodeError, KeyError, TypeError))
    def _parse_api_response(self, raw: str) -> dict:
        """Simulates parsing a raw HTTP body into structured data."""
        data = json.loads(raw)
        return {
            "user_id": data["user"]["id"],
            "username": data["user"]["name"],
            "email": data["user"]["email"],
        }

    def test_valid_json_returns_ok(self):
        raw = '{"user": {"id": 1, "name": "Archy", "email": "a@b.com"}}'
        result = self._parse_api_response(raw)
        assert result.is_ok()
        assert result.unwrap()["username"] == "Archy"

    def test_malformed_json_returns_err(self):
        """Broken JSON from a flaky API — no crash, just Err."""
        raw = '{"user": INVALID}'
        result = self._parse_api_response(raw)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), json.JSONDecodeError)

    def test_missing_nested_key_returns_err(self):
        """API changed their schema — 'email' field removed."""
        raw = '{"user": {"id": 1, "name": "Archy"}}'
        result = self._parse_api_response(raw)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), KeyError)

    def test_null_user_object_returns_err(self):
        """API returns null for user — TypeError on subscript."""
        raw = '{"user": null}'
        result = self._parse_api_response(raw)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), TypeError)


# ========================================================================
# SCENARIO 2: Form validation — collecting ALL errors at once
# Users hate fixing one error, resubmitting, and finding another.
# ========================================================================

class TestFormValidation:

    def _validate_field(self, name: str, value: str, rules: dict) -> Result[str, str]:
        if rules.get("required") and not value.strip():
            return Err(f"{name} is required")
        if "min_len" in rules and len(value) < rules["min_len"]:
            return Err(f"{name} must be at least {rules['min_len']} characters")
        if "max_len" in rules and len(value) > rules["max_len"]:
            return Err(f"{name} must be at most {rules['max_len']} characters")
        if rules.get("is_email") and "@" not in value:
            return Err(f"{name} must be a valid email")
        return Ok(value.strip())

    def test_valid_form_returns_all_values(self):
        results = [
            self._validate_field("Name", "Archy", {"required": True, "min_len": 2}),
            self._validate_field("Email", "a@b.com", {"required": True, "is_email": True}),
            self._validate_field("Password", "secret123", {"required": True, "min_len": 8}),
        ]
        collected = collect(results)
        assert collected.is_ok()
        assert collected.unwrap() == ["Archy", "a@b.com", "secret123"]

    def test_invalid_form_returns_all_errors_at_once(self):
        """The key feature: show ALL errors, not just the first one."""
        results = [
            self._validate_field("Name", "", {"required": True}),
            self._validate_field("Email", "not-an-email", {"required": True, "is_email": True}),
            self._validate_field("Password", "short", {"required": True, "min_len": 8}),
        ]
        collected = collect_all(results)
        assert collected.is_err()
        errors = collected.unwrap_err()
        assert len(errors) == 3
        assert "Name is required" in errors
        assert "Email must be a valid email" in errors
        assert "Password must be at least 8 characters" in errors

    def test_partition_separates_valid_and_invalid_fields(self):
        results = [
            self._validate_field("Name", "Archy", {"required": True}),
            self._validate_field("Email", "bad", {"is_email": True}),
            self._validate_field("Age", "25", {}),
        ]
        valid, invalid = partition(results)
        assert valid == ["Archy", "25"]
        assert len(invalid) == 1
        assert "email" in invalid[0].lower()


# ========================================================================
# SCENARIO 3: Reading and parsing files
# Config files, CSVs, logs — files break in a hundred ways.
# ========================================================================

class TestFileOperations:

    @safe(catch=FileNotFoundError)
    def _read_file(self, path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    @safe(catch=(json.JSONDecodeError, FileNotFoundError))
    def _load_json_config(self, path: str) -> dict:
        with open(path, "r") as f:
            return json.load(f)

    def test_read_existing_file(self):
        # Create a real temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            path = f.name
        try:
            result = self._read_file(path)
            assert result.is_ok()
            assert result.unwrap() == "hello world"
        finally:
            os.unlink(path)

    def test_read_missing_file_returns_err(self):
        result = self._read_file("/this/path/does/not/exist.txt")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), FileNotFoundError)

    def test_parse_valid_json_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"db_host": "localhost", "db_port": 5432}, f)
            path = f.name
        try:
            result = self._load_json_config(path)
            assert result.is_ok()
            assert result.unwrap()["db_port"] == 5432
        finally:
            os.unlink(path)

    def test_parse_corrupted_json_returns_err(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{broken json !!!}")
            path = f.name
        try:
            result = self._load_json_config(path)
            assert result.is_err()
            assert isinstance(result.unwrap_err(), json.JSONDecodeError)
        finally:
            os.unlink(path)


# ========================================================================
# SCENARIO 4: Nested dictionary lookups
# Config objects, API payloads, deeply nested data structures.
# ========================================================================

class TestNestedLookups:

    def _get_nested(self, data: dict, *keys: str) -> Option[object]:
        """Safely traverse nested dicts. Any missing key -> Nothing."""
        current: object = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return Nothing
        return Some(current)

    def test_deep_key_exists(self):
        data = {"server": {"db": {"host": "localhost", "port": 5432}}}
        result = self._get_nested(data, "server", "db", "host")
        assert result == Some("localhost")

    def test_deep_key_missing_at_level_2(self):
        data = {"server": {"db": {"host": "localhost"}}}
        result = self._get_nested(data, "server", "cache", "ttl")
        assert result == Nothing

    def test_chaining_nested_lookups(self):
        """Chain multiple lookups — first match wins."""
        data = {"server": {}}
        result = (
            self._get_nested(data, "server", "db", "host")
            .or_else(lambda: self._get_nested(data, "server", "fallback_host"))
            .or_else(lambda: Some("127.0.0.1"))
        )
        assert result == Some("127.0.0.1")


# ========================================================================
# SCENARIO 5: Data pipeline — CSV row processing
# Parse each row, keep the good ones, report the bad ones.
# ========================================================================

class TestCsvDataPipeline:

    def _parse_row(self, row: dict) -> Result[dict, str]:
        """Parse a CSV row into a validated record."""
        try:
            age = int(row.get("age", ""))
        except ValueError:
            return Err(f"Invalid age for {row.get('name', '?')}: '{row.get('age')}'")

        if age < 0 or age > 150:
            return Err(f"Unrealistic age for {row['name']}: {age}")

        return Ok({"name": row["name"], "age": age, "email": row.get("email", "")})

    def test_process_csv_with_mixed_data(self):
        csv_data = """name,age,email
Archy,28,archy@test.com
BadAge,xyz,bad@test.com
Chuks,25,chuks@test.com
TooOld,999,old@test.com"""

        reader = csv.DictReader(io.StringIO(csv_data))
        results = [self._parse_row(row) for row in reader]

        valid, errors = partition(results)
        assert len(valid) == 2
        assert valid[0]["name"] == "Archy"
        assert valid[1]["name"] == "Chuks"
        assert len(errors) == 2
        assert "Invalid age" in errors[0]
        assert "Unrealistic age" in errors[1]


# ========================================================================
# SCENARIO 6: Async operations — network calls, database queries
# Modern Python apps are async. The library must handle it.
# ========================================================================

class TestAsyncOperations:

    @safe_async(catch=ConnectionError)
    async def _fetch_data(self, url: str) -> dict:
        """Simulates an async HTTP call that might fail."""
        if "bad-host" in url:
            raise ConnectionError(f"Could not connect to {url}")
        return {"status": 200, "data": "ok"}

    @pytest.mark.asyncio
    async def test_async_success(self):
        result = await self._fetch_data("https://api.example.com/users")
        assert result.is_ok()
        assert result.unwrap()["status"] == 200

    @pytest.mark.asyncio
    async def test_async_connection_error(self):
        result = await self._fetch_data("https://bad-host.example.com/users")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ConnectionError)

    @pytest.mark.asyncio
    async def test_async_chaining(self):
        """Chain async results with sync transformations."""
        result = await self._fetch_data("https://api.example.com/users")
        final = result.map(lambda r: r["data"]).map(str.upper)
        assert final == Ok("OK")


# ========================================================================
# SCENARIO 7: Type conversions — Result <-> Option in real workflows
# Developers constantly need to convert between these.
# ========================================================================

class TestTypeConversions:

    def test_result_to_option_drops_error_detail(self):
        """When you don't care WHY it failed, just IF it failed."""
        result: Result[int, str] = Err("database timeout after 30s")
        option = result.ok()
        assert option == Nothing  # Error detail is gone, but that's intentional

    def test_option_to_result_adds_error_context(self):
        """When you need to explain WHY something is missing."""
        config_value: Option[str] = Nothing
        result = config_value.ok_or("DATABASE_URL environment variable is not set")
        assert result == Err("DATABASE_URL environment variable is not set")

    def test_unwrap_or_provides_sensible_defaults(self):
        """Real-world: config with fallback defaults."""
        db_host = Nothing.unwrap_or("localhost")
        db_port = Some(3306).unwrap_or(5432)
        timeout = Nothing.unwrap_or(30)

        assert db_host == "localhost"
        assert db_port == 3306  # Some value wins over default
        assert timeout == 30


# ========================================================================
# SCENARIO 8: Error recovery chains
# Try primary, fallback to secondary, fallback to default.
# ========================================================================

class TestErrorRecoveryChains:

    def _from_env(self, key: str) -> Result[str, str]:
        val = os.environ.get(key)
        if val:
            return Ok(val)
        return Err(f"${key} not set")

    def _from_file(self, path: str) -> Result[str, str]:
        if os.path.exists(path):
            with open(path) as f:
                return Ok(f.read().strip())
        return Err(f"File {path} not found")

    def test_fallback_chain(self):
        """Try env var -> try file -> use hardcoded default."""
        result = (
            self._from_env("RESOLUTE_TEST_SECRET_KEY_THAT_DOESNT_EXIST")
            .or_else(lambda _: self._from_file("/nonexistent/secret.key"))
            .or_else(lambda _: Ok("default-dev-key-12345"))
        )
        assert result == Ok("default-dev-key-12345")

    def test_first_success_stops_chain(self):
        """If env var exists, don't even try the file."""
        os.environ["_RESOLUTE_TEST_KEY"] = "from-env"
        try:
            result = (
                self._from_env("_RESOLUTE_TEST_KEY")
                .or_else(lambda _: self._from_file("/should/not/be/read"))
            )
            assert result == Ok("from-env")
        finally:
            del os.environ["_RESOLUTE_TEST_KEY"]
