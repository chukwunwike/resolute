import pytest
import random
from typing import List, Tuple

from resolute import Ok, Err, Some, Nothing, Result, Option
from resolute import partition, collect
from resolute import safe, do
from resolute import UnwrapError


class TestPartitionCombinator:
    """Tests for the partition combinator focusing on scale and edge cases."""

    def test_partition_large_dataset_with_random_failures(self) -> None:
        """Scenario: Handling 1000 items with random Ok/Err variants."""
        item_count = 1000
        raw_data = [random.randint(1, 100) for _ in range(item_count)]
        
        # Randomly assign Ok or Err
        results: List[Result[int, str]] = []
        expected_oks: List[int] = []
        expected_errs: List[str] = []

        for val in raw_data:
            if val > 30:  # ~70% success rate
                results.append(Ok(val))
                expected_oks.append(val)
            else:
                err_msg = f"Error at {val}"
                results.append(Err(err_msg))
                expected_errs.append(err_msg)

        # Execute partition
        oks, errs = partition(results)

        assert len(oks) == len(expected_oks)
        assert len(errs) == len(expected_errs)
        assert oks == expected_oks
        assert errs == expected_errs

    def test_partition_empty_list(self) -> None:
        """Ensure partitioning an empty iterable returns two empty lists."""
        oks, errs = partition([])
        assert oks == []
        assert errs == []

    def test_partition_all_err(self) -> None:
        """Ensure it handles a list containing only Err variants."""
        results: List[Result[int, str]] = [Err("fail1"), Err("fail2")]
        oks, errs = partition(results)
        assert oks == []
        assert errs == ["fail1", "fail2"]


class TestCollectCombinator:
    """Tests for the collect combinator focusing on short-circuiting."""

    def test_collect_success(self) -> None:
        """Should aggregate all values into an Ok list if all are Ok."""
        results = [Ok(1), Ok(2), Ok(3)]
        final_result = collect(results)
        assert final_result.is_ok()
        assert final_result.unwrap() == [1, 2, 3]

    def test_collect_short_circuit_on_first_err(self) -> None:
        """Should stop and return the first Err encountered."""
        results = [Ok(1), Err("first crash"), Err("second crash")]
        final_result = collect(results)
        
        assert final_result.is_err()
        assert final_result.unwrap_err() == "first crash"


class TestErrorContextAndEdgeCases:
    """Tests for context tracking and the mandatory 'things gone wrong' scenarios."""

    def test_context_chaining_and_root_cause(self) -> None:
        """Verifies that error context is preserved and the root cause is accessible."""
        base_err = Err("Database connection failed")
        wrapped_err = base_err.context("Failed to fetch user").context("API request failed")

        assert wrapped_err.unwrap_err().root_cause == "Database connection failed"
        
        # Verify the chain length (API -> User -> Database)
        chain = wrapped_err.unwrap_err().chain()
        assert len(chain) == 3
        assert "API request failed" in str(chain[0])

    def test_unwrap_err_raises_unwrap_error(self) -> None:
        """Edge Case: Unwrapping an Err should raise the specific library exception."""
        err_instance = Err("Something went wrong")
        
        with pytest.raises(UnwrapError) as excinfo:
            err_instance.unwrap()
        
        assert "Something went wrong" in str(excinfo.value)

    def test_ok_or_conversion(self) -> None:
        """Testing Option to Result conversion."""
        some_val = Some(42)
        nothing_val = Nothing

        assert some_val.ok_or("Error").unwrap() == 42
        assert nothing_val.ok_or("Is Nothing").unwrap_err() == "Is Nothing"


class TestDecorators:
    """Tests for @safe and @do notation."""

    def test_safe_decorator_catches_specific_exceptions(self) -> None:
        @safe(catch=(ValueError,))
        def risk_function(should_fail: bool) -> int:
            if should_fail:
                raise ValueError("Boom")
            return 42

        assert risk_function(False).unwrap() == 42
        assert risk_function(True).is_err()
        assert isinstance(risk_function(True).unwrap_err(), ValueError)

    def test_do_notation_short_circuit(self) -> None:
        @do()
        def workflow(x: int, y: int) -> Result[int, str]:
            # If x_res is Err, the function should exit here
            val_x = yield Ok(x) if x > 0 else Err("x too low")
            val_y = yield Ok(y) if y > 0 else Err("y too low")
            return Ok(val_x + val_y)

        # Success path
        assert workflow(10, 20).unwrap() == 30
        # Failure path (short-circuits at x)
        result = workflow(-1, 20)
        assert result.is_err()
        assert result.unwrap_err() == "x too low"
