"""
Test metadata preservation for @do and @do_option decorators.
Converted from root test_metadata.py.
"""
from resolute import do, Ok, Result

@do()
def pipeline() -> Result[int, str]:
    """Test documentation."""
    x = yield Ok(1)
    return x

def test_pipeline_metadata():
    assert pipeline.__name__ == "pipeline"
    assert pipeline.__doc__ == "Test documentation."
    assert "test_do_metadata" in pipeline.__module__
    assert hasattr(pipeline, "__wrapped__")

if __name__ == "__main__":
    test_pipeline_metadata()
    print("Metadata tests passed.")
