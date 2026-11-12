"""M3 报修文本校验；不依赖 HTTP、认证或持久化。"""


class InvalidReportText(ValueError):
    """field 标识内部字段；reason 为 not_string 或 blank。"""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"{field}: {reason}")


def _normalize_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidReportText(field, "not_string")
    normalized = value.strip()
    if not normalized:
        raise InvalidReportText(field, "blank")
    return normalized


def validate_report_text(fault_type: object, description: object) -> tuple[str, str]:
    """返回去除首尾空白的 (类型, 描述)，保留正文内部内容。

    按类型、描述的顺序检查，遇到首个非法值即抛出 InvalidReportText。
    None 及其他非字符串值均拒绝；不限定分类枚举或长度。
    参数名仅为 M3 内部约定，不冻结 HTTP 参数或数据库字段。
    """
    return (
        _normalize_text(fault_type, "fault_type"),
        _normalize_text(description, "description"),
    )
