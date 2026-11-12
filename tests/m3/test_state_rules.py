"""验证真实状态规则；不依赖工单、会话或数据库夹具。"""

import pytest

from app.m3.state_rules import InvalidStateTransition, validate_transition


@pytest.mark.parametrize(
    ("current_state", "target_state"),
    [
        pytest.param("REPORTED", "ASSIGNED", id="M3-R02-assign"),
        pytest.param("ASSIGNED", "IN_REPAIR", id="M3-R03-start-repair"),
    ],
)
def test_m3_r02_r03_allow_adjacent_forward_transitions(current_state, target_state):
    assert validate_transition(current_state, target_state) is None


@pytest.mark.parametrize(
    ("current_state", "target_state"),
    [
        pytest.param("REPORTED", "IN_REPAIR", id="skip-assignment"),
        pytest.param("ASSIGNED", "REPORTED", id="reverse-assignment"),
        pytest.param("IN_REPAIR", "ASSIGNED", id="reverse-start"),
        pytest.param("IN_REPAIR", "REPORTED", id="reverse-to-reported"),
        pytest.param("REPORTED", "REPORTED", id="repeat-reported"),
        pytest.param("ASSIGNED", "ASSIGNED", id="repeat-assigned"),
        pytest.param("IN_REPAIR", "IN_REPAIR", id="repeat-in-repair"),
    ],
)
def test_m3_r02_r03_reject_skip_reverse_and_repeat(current_state, target_state):
    with pytest.raises(InvalidStateTransition, match="不允许的工单状态转换") as caught:
        validate_transition(current_state, target_state)
    assert caught.value.current_state == current_state
    assert caught.value.target_state == target_state


@pytest.mark.parametrize(
    ("current_state", "target_state"),
    [
        pytest.param("UNKNOWN", "ASSIGNED", id="unknown-current"),
        pytest.param("REPORTED", "UNKNOWN", id="unknown-target"),
        pytest.param("UNKNOWN", "UNKNOWN", id="both-unknown"),
        pytest.param("", "ASSIGNED", id="empty-current"),
        pytest.param("REPORTED", "", id="empty-target"),
        pytest.param("reported", "ASSIGNED", id="lowercase-current"),
        pytest.param("REPORTED", "assigned", id="lowercase-target"),
        pytest.param(" REPORTED", "ASSIGNED", id="leading-space"),
        pytest.param("ASSIGNED", "IN_REPAIR ", id="trailing-space"),
        pytest.param("IN_REPAIR", "PENDING_ACCEPT", id="deferred-acceptance"),
        pytest.param("DONE", "REPORTED", id="deferred-done"),
    ],
)
def test_m3_r02_r03_reject_unknown_states(current_state, target_state):
    with pytest.raises(InvalidStateTransition, match="未知的工单状态") as caught:
        validate_transition(current_state, target_state)
    assert caught.value.current_state == current_state
    assert caught.value.target_state == target_state


@pytest.mark.parametrize(
    ("current_state", "target_state"),
    [
        pytest.param(None, "ASSIGNED", id="none-current"),
        pytest.param("REPORTED", None, id="none-target"),
        pytest.param(1, "ASSIGNED", id="number-current"),
        pytest.param("REPORTED", False, id="boolean-target"),
        pytest.param([], "ASSIGNED", id="unhashable-current"),
        pytest.param("REPORTED", {}, id="unhashable-target"),
    ],
)
def test_m3_r02_r03_reject_non_string_states(current_state, target_state):
    with pytest.raises(InvalidStateTransition, match="未知的工单状态") as caught:
        validate_transition(current_state, target_state)
    assert caught.value.current_state == current_state
    assert caught.value.target_state == target_state
