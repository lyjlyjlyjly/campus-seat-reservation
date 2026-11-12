import pytest

from app.m3.report_validation import InvalidReportText, validate_report_text


def test_m3_r01_accepts_chinese_report_text():
    assert validate_report_text("照明故障", "教室后排灯管闪烁") == (
        "照明故障",
        "教室后排灯管闪烁",
    )


def test_m3_r01_strips_surrounding_whitespace_from_both_fields():
    assert validate_report_text(" \t照明故障\n", "\u3000灯管闪烁\r\n ") == (
        "照明故障",
        "灯管闪烁",
    )


def test_m3_r01_preserves_internal_spaces_tabs_and_newlines():
    assert validate_report_text(
        "  灯具  故障\n其他  ", "\n第一排  左侧\n灯管\t闪烁\r\n请检查\n"
    ) == ("灯具  故障\n其他", "第一排  左侧\n灯管\t闪烁\r\n请检查")


@pytest.mark.parametrize(
    "fault_type,description,field",
    [
        ("", "灯管闪烁", "fault_type"),
        (" \t\r\n\u3000", "灯管闪烁", "fault_type"),
        ("照明故障", "", "description"),
        ("照明故障", " \t\r\n\u3000", "description"),
    ],
)
def test_m3_r01_rejects_empty_or_whitespace_text(fault_type, description, field):
    with pytest.raises(InvalidReportText) as raised:
        validate_report_text(fault_type, description)

    assert raised.value.field == field
    assert raised.value.reason == "blank"
    assert str(raised.value) == f"{field}: blank"


@pytest.mark.parametrize(
    "fault_type,description,field",
    [
        (None, "灯管闪烁", "fault_type"),
        ("照明故障", None, "description"),
        (42, "灯管闪烁", "fault_type"),
        ("照明故障", 3.5, "description"),
        (True, "灯管闪烁", "fault_type"),
        ("照明故障", False, "description"),
        (["照明故障"], "灯管闪烁", "fault_type"),
        ("照明故障", {"text": "灯管闪烁"}, "description"),
    ],
)
def test_m3_r01_rejects_missing_and_non_string_values(fault_type, description, field):
    with pytest.raises(InvalidReportText) as raised:
        validate_report_text(fault_type, description)

    assert raised.value.field == field
    assert raised.value.reason == "not_string"
    assert str(raised.value) == f"{field}: not_string"


def test_m3_r01_does_not_impose_unconfirmed_categories_or_length_limit():
    description = "需要现场检查。" * 200
    assert validate_report_text("其他现场问题", description) == ("其他现场问题", description)
