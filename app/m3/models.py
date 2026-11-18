"""创建入口的严格业务输入；不改变 PR #2 通用规范化函数的约定。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


CATEGORIES = ("ELECTRICAL", "WATER", "FURNITURE", "OTHER")


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
