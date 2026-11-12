"""M3 基础状态顺序；只校验，不处理权限或修改工单。"""


_STATES = frozenset({"REPORTED", "ASSIGNED", "IN_REPAIR"})
_ALLOWED_TRANSITIONS = frozenset({
    ("REPORTED", "ASSIGNED"),
    ("ASSIGNED", "IN_REPAIR"),
})


class InvalidStateTransition(ValueError):
    """状态未知或转换不允许；保留原始输入供业务层处理。"""

    def __init__(self, current_state: object, target_state: object, reason: str) -> None:
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(f"{reason}：{current_state!r} -> {target_state!r}")


def validate_transition(current_state: str, target_state: str) -> None:
    """合法时返回 None，否则抛 InvalidStateTransition；不执行状态更新。

    仅允许 REPORTED → ASSIGNED → IN_REPAIR 的相邻转换。
    后续调用方仍须负责授权、事务内读取状态及条件写入。
    """
    if (
        not isinstance(current_state, str)
        or not isinstance(target_state, str)
        or current_state not in _STATES
        or target_state not in _STATES
    ):
        raise InvalidStateTransition(current_state, target_state, "未知的工单状态")
    if (current_state, target_state) not in _ALLOWED_TRANSITIONS:
        raise InvalidStateTransition(current_state, target_state, "不允许的工单状态转换")
