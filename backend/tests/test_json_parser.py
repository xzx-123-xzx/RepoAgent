from app.schemas.code_audit import CodeAuditReport
from app.llm.json_parser import normalize_code_audit_report, normalize_product_value_report


def test_normalize_malformed_code_audit():
    raw = {"summary": "FastAPI 是一个优秀的 Web 框架，代码规范良好。"}
    normalized = normalize_code_audit_report(raw)
    report = CodeAuditReport.model_validate(normalized)
    assert report.overall_code_score >= 0
    assert len(report.dimensions) == 5
    assert "directory_structure" in report.dimensions


def test_normalize_partial_dimensions():
    raw = {
        "overall_code_score": 80,
        "dimensions": {
            "directory_structure": {"score": 85, "summary": "结构清晰", "issues": []},
        },
        "highlights": ["测试覆盖较好"],
    }
    report = CodeAuditReport.model_validate(normalize_code_audit_report(raw))
    assert report.overall_code_score == 80
    assert report.dimensions["architecture_quality"].score == 70


def test_normalize_product_report():
    raw = {"summary": "文档完善", "score": 88}
    report_data = normalize_product_value_report(raw)
    from app.schemas.product_value import ProductValueReport

    report = ProductValueReport.model_validate(report_data)
    assert report.overall_product_score == 88
