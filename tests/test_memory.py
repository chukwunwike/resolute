"""
tests/test_memory.py
Ensures no massive memory leaks occur, particularly with exception
tracebacks captured by `resolute` wrappers.
"""
import gc
import sys
from resolute import safe, Err

@safe(catch=ValueError)
def risky_action():
    raise ValueError("Something went terribly wrong")

def test_no_traceback_leaks():
    """
    Ensure that generating millions of `Err` objects from caught exceptions 
    doesn't leak memory by permanently holding frame references.
    """
    # Force a garbage collection
    gc.collect()
    
    # Store initial object counts
    initial_counts = len(gc.get_objects())
    
    # Generate 10,000 Err objects containing exceptions
    for _ in range(10000):
        res = risky_action()
        assert res.is_err()
        # Fall out of scope
        
    # Collect garbage again
    gc.collect()
    
    # Check that we haven't permanently retained 10,000 exceptions
    final_counts = len(gc.get_objects())
    
    # Allow for some small variance, but certainly not 10,000
    assert (final_counts - initial_counts) < 100
