import random
from typing import List, Tuple

import pytest

from explicit_result import Ok, Err
from explicit_result._combinators import partition
from explicit_result._exceptions import UnwrapError


def generate_mixed_results(n: int, fail_ratio: float = 0.3):
    """
    Helper to generate a list of Results with controlled failure ratio.
    """
    results = []
    for i in range(n):
        if random.random() < fail_ratio:
            results.append(Err(f"error_{i}"))
        else:
            results.append(Ok(i))
    return results


def test_partition_basic_mixed() -> None:
    results = [Ok(1), Err("a"), Ok(2), Err("b")]

    ok_values, err_values = partition(results)

    assert ok_values == [1, 2]
    assert err_values == ["a", "b"]


def test_partition_all_ok() -> None:
    results = [Ok(i) for i in range(10)]

    ok_values, err_values = partition(results)

    assert ok_values == list(range(10))
    assert err_values == []


def test_partition_all_err() -> None:
    results = [Err(f"e{i}") for i in range(10)]

    ok_values, err_values = partition(results)

    assert ok_values == []
    assert err_values == [f"e{i}" for i in range(10)]


def test_partition_empty_input() -> None:
    results: List = []

    ok_values, err_values = partition(results)

    assert ok_values == []
    assert err_values == []


def test_partition_large_random_input() -> None:
    random.seed(42)

    results = generate_mixed_results(1000, fail_ratio=0.25)
    ok_values, err_values = partition(results)

    # Validate counts match expectations
    expected_ok = [r.unwrap() for r in results if r.is_ok()]
    expected_err = [r.unwrap_err() for r in results if r.is_err()]

    assert ok_values == expected_ok
    assert err_values == expected_err

    assert len(ok_values) + len(err_values) == 1000


def test_partition_preserves_order() -> None:
    results = [Ok(1), Err("a"), Ok(2), Err("b"), Ok(3)]

    ok_values, err_values = partition(results)

    # Order must be preserved relative to original sequence
    assert ok_values == [1, 2, 3]
    assert err_values == ["a", "b"]


def test_partition_with_complex_types() -> None:
    results = [
        Ok({"id": 1}),
        Err(ValueError("bad")),
        Ok({"id": 2}),
    ]

    ok_values, err_values = partition(results)

    assert ok_values == [{"id": 1}, {"id": 2}]
    assert isinstance(err_values[0], ValueError)


def test_partition_does_not_mutate_input() -> None:
    results = [Ok(1), Err("x")]

    original = list(results)
    partition(results)

    assert results == original


def test_partition_unwrap_error_propagation_safety() -> None:
    """
    Ensure that partition itself does NOT raise when encountering Err.
    """
    results = [Ok(1), Err("fail"), Ok(2)]

    try:
        ok_values, err_values = partition(results)
    except UnwrapError:
        pytest.fail("partition should not raise UnwrapError")

    assert ok_values == [1, 2]
    assert err_values == ["fail"]


def test_partition_type_integrity() -> None:
    results = [Ok(10), Err("x")]

    ok_values, err_values = partition(results)

    # Type expectations
    assert isinstance(ok_values, list)
    assert isinstance(err_values, list)

    assert isinstance(ok_values[0], int)
    assert isinstance(err_values[0], str)


def test_partition_with_nested_results() -> None:
    """
    Ensure partition does not unwrap nested structures accidentally.
    """
    results = [Ok(Ok(1)), Err(Err("nested"))]

    ok_values, err_values = partition(results)

    assert isinstance(ok_values[0], type(Ok(1)))
    assert isinstance(err_values[0], type(Err("nested")))


@pytest.mark.parametrize(
    "inputs,expected_ok,expected_err",
    [
        ([Ok(1)], [1], []),
        ([Err("x")], [], ["x"]),
        ([Ok(1), Ok(2)], [1, 2], []),
        ([Err("a"), Err("b")], [], ["a", "b"]),
    ],
)
def test_partition_parametrized(
    inputs: List,
    expected_ok: List,
    expected_err: List,
) -> None:
    ok_values, err_values = partition(inputs)

    assert ok_values == expected_ok
    assert err_values == expected_err
