import sys
import pytest
from explicit_result import Ok, Err

@pytest.mark.skipif(sys.version_info < (3, 10), reason="match requires Python 3.10+")
class TestResultPatternMatching:
    def test_ok_match(self):
        result = Ok(42)
        matched = None
        match result:
            case Ok(v):
                matched = ("ok", v)
            case Err(e):
                matched = ("err", e)
        assert matched == ("ok", 42)

    def test_err_match(self):
        result = Err("bad")
        matched = None
        match result:
            case Ok(v):
                matched = ("ok", v)
            case Err(e):
                matched = ("err", e)
        assert matched == ("err", "bad")
