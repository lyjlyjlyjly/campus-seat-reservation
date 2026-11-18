"""创建入口的严格业务输入；不改变 PR #2 通用规范化函数的约定。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.m3.errors import ReportError


CATEGORIES = ("ELECTRICAL", "WATER", "FURNITURE", "OTHER")


def parse_order_id(value: str) -> int | None:
    """路径十进制正整数；超出 SQLite 范围返回 None，不执行危险的大整数转换。"""
    if not value.isascii() or not value.isdecimal() or not value.strip("0"):
        raise ReportError(422, "invalid_request", "order_id 必须为十进制正整数")
    digits = value.lstrip("0")
    if len(digits) > 19 or (len(digits) == 19 and digits > "9223372036854775807"):
        return None
    return int(digits)


class ReportCreate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    room_id: int = Field(gt=0)
    fault_type: str
    description: str

    @field_validator("fault_type")
    @classmethod
    def category(cls, value: str) -> str:
        value = value.strip()
        if value not in CATEGORIES:
            raise ValueError("请选择有效的故障分类")
        return value

    @field_validator("description")
    @classmethod
    def report_text(cls, value: str) -> str:
        # 后续在此复用 PR #2 的规范化；具体业务约束仍保留在本层。
        value = value.strip()
        if not 1 <= len(value) <= 1000:
            raise ValueError("故障描述去除首尾空白后须为 1–1000 个 Unicode 字符")
        if "\x00" in value:
            raise ValueError("故障描述不能包含 U+0000")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("故障描述包含无效的 Unicode 字符") from error
        return value
