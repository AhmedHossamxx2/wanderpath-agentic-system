"""
Tests for DAG cycle detection.
"""
import pytest
from planning.dag.acyclicity import verify_acyclic, CycleDetectedError

def test_valid_acyclic_plan():
    """Test a valid rebooking plan without cycles."""
    # rebook_flight -> modify_hotel -> notify_client
    plan = {
        "rebook_flight": ["modify_hotel", "modify_transfer"],
        "modify_hotel": ["notify_client"],
        "modify_transfer": ["notify_client"],
        "notify_client": []
    }
    assert verify_acyclic(plan) is True

def test_invalid_cyclic_plan():
    """Test a malformed plan where tasks depend on each other in a loop."""
    # modify_hotel depends on notify_client, but notify_client depends on modify_hotel
    plan = {
        "rebook_flight": ["modify_hotel"],
        "modify_hotel": ["notify_client"],
        "notify_client": ["modify_hotel"]  # CYCLE!
    }
    
    with pytest.raises(CycleDetectedError, match="Cycle detected"):
        verify_acyclic(plan)