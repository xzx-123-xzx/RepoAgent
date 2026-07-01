"""Parse and normalize LLM JSON output to match Pydantic schemas."""

from __future__ import annotations

import json
import re
from typing import Any

from app.utils.exceptions import LLMError

CODE_AUDIT_DIMENSIONS = [
    "directory_structure",
    "architecture_quality",
    "tech_debt",
    "dependency_risk",
    "code_standards",
]

PRODUCT_DIMENSIONS = [
    "documentation",
    "practicality",
    "open_source_activity",
    "maintainability",
    "popularity",
]

CODE_AUDIT_ALIASES = {
    "directory_structure": ["目录规范性", "directory", "structure", "目录结构"],
    "architecture_quality": ["架构合理性", "architecture", "架构"],
    "tech_debt": ["技术债务", "tech_debt", "debt"],
    "dependency_risk": ["依赖风险", "dependency", "dependencies"],
    "code_standards": ["代码规范", "standards", "规范"],
}

PRODUCT_ALIASES = {
    "documentation": ["文档完整性", "documentation", "文档"],
    "practicality": ["项目实用性", "practicality", "实用性"],
    "open_source_activity": ["开源活跃度", "activity", "活跃度"],
    "maintainability": ["维护可持续性", "maintainability", "维护性"],
    "popularity": ["传播度", "popularity", "热度"],
}


def parse_json_content(content: str) -> dict[str, Any]:
    content = content.strip()
    if not content:
        raise LLMError("LLM 返回内容为空")

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```\s*$", "", content)

    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 尝试提取最外层 JSON 对象
    start = content.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(content)):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(content[start : i + 1])
                        if isinstance(data, dict):
                            return data
                    except json.JSONDecodeError:
                        break

    raise LLMError("LLM 返回内容无法解析为 JSON")


def _clamp_score(value: Any, default: int = 70) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        score = default
    return max(0, min(100, score))


def _ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_dimension(value: Any, default_summary: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "score": _clamp_score(value.get("score", value.get("分数", value.get("rating", 70)))),
            "summary": str(value.get("summary", value.get("总结", value.get("description", default_summary)))),
            "issues": _ensure_list(value.get("issues", value.get("问题", value.get("problems", [])))),
        }
    if isinstance(value, (int, float)):
        return {"score": _clamp_score(value), "summary": default_summary, "issues": []}
    if isinstance(value, str):
        return {"score": 70, "summary": value, "issues": []}
    return {"score": 70, "summary": default_summary, "issues": []}


def _extract_dimensions(data: dict[str, Any], keys: list[str], aliases: dict[str, list[str]]) -> dict[str, dict]:
    raw_dims = data.get("dimensions") or data.get("dimension") or data.get("维度") or {}
    if not isinstance(raw_dims, dict):
        raw_dims = {}

    # 有时维度散落在顶层
    for key in keys:
        if key not in raw_dims and key in data and isinstance(data[key], dict):
            raw_dims[key] = data[key]

    for key, alias_list in aliases.items():
        if key in raw_dims:
            continue
        for alias in alias_list:
            if alias in raw_dims:
                raw_dims[key] = raw_dims[alias]
                break
            if alias in data:
                raw_dims[key] = data[alias]
                break

    return {key: _normalize_dimension(raw_dims.get(key), f"{key} 评估") for key in keys}


def _average_score(dimensions: dict[str, dict]) -> int:
    scores = [d["score"] for d in dimensions.values()]
    return round(sum(scores) / len(scores)) if scores else 70


def normalize_code_audit_report(data: dict[str, Any]) -> dict[str, Any]:
    if "code_audit_report" in data and isinstance(data["code_audit_report"], dict):
        data = data["code_audit_report"]
    if "code_audit" in data and isinstance(data["code_audit"], dict):
        data = data["code_audit"]

    dimensions = _extract_dimensions(data, CODE_AUDIT_DIMENSIONS, CODE_AUDIT_ALIASES)
    overall = data.get("overall_code_score", data.get("overall_score", data.get("score", data.get("总分"))))
    if overall is None:
        overall = _average_score(dimensions)

    return {
        "agent_id": "code_auditor",
        "overall_code_score": _clamp_score(overall),
        "dimensions": dimensions,
        "highlights": _ensure_list(data.get("highlights", data.get("亮点", []))),
        "critical_issues": _ensure_list(data.get("critical_issues", data.get("严重问题", data.get("issues", [])))),
        "recommendations": _ensure_list(data.get("recommendations", data.get("建议", data.get("suggestions", [])))),
    }


def normalize_product_value_report(data: dict[str, Any]) -> dict[str, Any]:
    if "product_value_report" in data and isinstance(data["product_value_report"], dict):
        data = data["product_value_report"]
    if "product_analysis" in data and isinstance(data["product_analysis"], dict):
        data = data["product_analysis"]

    dimensions = _extract_dimensions(data, PRODUCT_DIMENSIONS, PRODUCT_ALIASES)
    overall = data.get("overall_product_score", data.get("overall_score", data.get("score", data.get("总分"))))
    if overall is None:
        overall = _average_score(dimensions)

    return {
        "agent_id": "product_analyst",
        "overall_product_score": _clamp_score(overall),
        "dimensions": dimensions,
        "highlights": _ensure_list(data.get("highlights", data.get("亮点", []))),
        "critical_issues": _ensure_list(data.get("critical_issues", data.get("严重问题", []))),
        "recommendations": _ensure_list(data.get("recommendations", data.get("建议", []))),
    }


def normalize_final_report(data: dict[str, Any], fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    fb = fallback or {}
    scores_raw = data.get("scores") or {}
    if isinstance(scores_raw, (int, float)):
        scores_raw = {"total_score": scores_raw}

    code_score = scores_raw.get("code_score", data.get("code_score", fb.get("code_score", 70)))
    product_score = scores_raw.get("product_score", data.get("product_score", fb.get("product_score", 70)))
    total = scores_raw.get("total_score", data.get("total_score", data.get("score")))
    if total is None:
        total = round(_clamp_score(code_score) * 0.5 + _clamp_score(product_score) * 0.5)

    total_i = _clamp_score(total)
    grade = str(data.get("grade", data.get("等级", _score_to_grade(total_i))))

    recs = data.get("top_recommendations", data.get("recommendations", []))
    normalized_recs = []
    if isinstance(recs, list):
        for item in recs[:8]:
            if isinstance(item, str):
                normalized_recs.append({"priority": "medium", "category": "code", "action": item})
            elif isinstance(item, dict):
                normalized_recs.append({
                    "priority": str(item.get("priority", "medium")),
                    "category": str(item.get("category", "code")),
                    "action": str(item.get("action", item.get("建议", item.get("content", "")))),
                })

    return {
        "agent_id": "judge",
        "repo_name": str(data.get("repo_name", fb.get("repo_name", ""))),
        "repo_url": str(data.get("repo_url", fb.get("repo_url", ""))),
        "analyzed_at": str(data.get("analyzed_at", fb.get("analyzed_at", ""))),
        "scores": {
            "total_score": total_i,
            "code_score": _clamp_score(code_score),
            "product_score": _clamp_score(product_score),
            "weights": {"code": 0.5, "product": 0.5},
        },
        "grade": grade,
        "summary": str(data.get("summary", data.get("总结", fb.get("summary", "仓库体检完成")))),
        "repo_metrics": data.get("repo_metrics", fb.get("repo_metrics", {})),
        "code_audit": data.get("code_audit", fb.get("code_audit", {})),
        "product_analysis": data.get("product_analysis", fb.get("product_analysis", {})),
        "top_recommendations": normalized_recs,
        "verdict": str(data.get("verdict", data.get("综合结论", data.get("conclusion", "")))),
    }


def _score_to_grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 85:
        return "B+"
    if score >= 80:
        return "B"
    if score >= 75:
        return "C+"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


NORMALIZERS = {
    "code_auditor": normalize_code_audit_report,
    "product_analyst": normalize_product_value_report,
    "judge": normalize_final_report,
}

SCHEMA_EXAMPLES = {
    "code_auditor": """{
  "agent_id": "code_auditor",
  "overall_code_score": 78,
  "dimensions": {
    "directory_structure": {"score": 82, "summary": "...", "issues": ["..."]},
    "architecture_quality": {"score": 75, "summary": "...", "issues": []},
    "tech_debt": {"score": 70, "summary": "...", "issues": []},
    "dependency_risk": {"score": 85, "summary": "...", "issues": []},
    "code_standards": {"score": 80, "summary": "...", "issues": []}
  },
  "highlights": ["..."],
  "critical_issues": ["..."],
  "recommendations": ["..."]
}""",
    "product_analyst": """{
  "agent_id": "product_analyst",
  "overall_product_score": 85,
  "dimensions": {
    "documentation": {"score": 90, "summary": "...", "issues": []},
    "practicality": {"score": 82, "summary": "...", "issues": []},
    "open_source_activity": {"score": 88, "summary": "...", "issues": []},
    "maintainability": {"score": 80, "summary": "...", "issues": []},
    "popularity": {"score": 85, "summary": "...", "issues": []}
  },
  "highlights": ["..."],
  "critical_issues": ["..."],
  "recommendations": ["..."]
}""",
}
