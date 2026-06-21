import re
from app.models.schemas import InsightType, RiskLevel, LegalInsight
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Raw Pattern Definitions ───────────────────────────────────────────────────
_PATTERNS = {
    InsightType.obligation: {
        "keywords": [r"\bshall\b", r"\bmust\b", r"\bis required to\b", r"\bobligation\b"],
        "base_risk": RiskLevel.medium,
        "amplifiers": [r"\bsole discretion\b", r"\bunconditional\b"]
    },
    InsightType.penalty: {
        "keywords": [r"\bpenalt(?:y|ies)\b", r"\bdamages\b", r"\bliable\b", r"\bbreach\b"],
        "base_risk": RiskLevel.high,
        "amplifiers": [r"\bunlimited liability\b", r"\bpunitive damages\b", r"\bliquidated damages\b"]
    },
    InsightType.termination: {
        "keywords": [r"\bterminat(?:e|ed|es|ing|ion)\b", r"\bcancel(?:led|ling|s)?\b", r"\bexpir(?:e|ed|es|ing|y|ation)\b"],
        "base_risk": RiskLevel.medium,
        "amplifiers": [r"\bimmediate(?:ly)?\b", r"\bwithout notice\b", r"\bsole discretion\b"]
    },
    InsightType.risk: {
        "keywords": [r"\brisk\b", r"\bhazard\b", r"\bexposure\b", r"\buncertain\b"],
        "base_risk": RiskLevel.high,
        "amplifiers": [r"\bmaterial risk\b", r"\bsubstantial risk\b"]
    },
    InsightType.definition: {
        "keywords": [r"\bmeans\b", r"\bdefined as\b", r"\bshall mean\b", r"\brefers to\b"],
        "base_risk": RiskLevel.low,
        "amplifiers": []
    },
    InsightType.deadline: {
        "keywords": [r"\bwithin\s+\d+\s+days\b", r"\bdeadline\b", r"\bdue date\b", r"\bno later than\b"],
        "base_risk": RiskLevel.medium,
        "amplifiers": [r"\btime is of the essence\b", r"\bstrict(?:ly)?\b"]
    },
    InsightType.confidentiality: {
        "keywords": [r"\bconfidential\b", r"\bnon-disclosure\b", r"\bproprietary\b", r"\btrade secret\b"],
        "base_risk": RiskLevel.medium,
        "amplifiers": [r"\bperpetual\b", r"\bindefinitely\b"]
    },
    InsightType.indemnification: {
        "keywords": [r"\bindemnif(?:y|ies|ied|ying|ication)\b", r"\bhold harmless\b", r"\bdefend\b"],
        "base_risk": RiskLevel.high,
        "amplifiers": [r"\bunlimited liability\b", r"\ball claims\b", r"\bany and all\b"]
    },
    InsightType.governing_law: {
        "keywords": [r"\bgoverning law\b", r"\bjurisdiction\b", r"\bvenue\b", r"\bgoverned by\b"],
        "base_risk": RiskLevel.low,
        "amplifiers": []
    },
}

# ── Pre-compiled Patterns ─────────────────────────────────────────────────────
_COMPILED_PATTERNS = {
    insight_type: {
        "keywords": [re.compile(kw, re.IGNORECASE) for kw in config["keywords"]],
        "amplifiers": [re.compile(amp, re.IGNORECASE) for amp in config["amplifiers"]],
        "base_risk": config["base_risk"]
    }
    for insight_type, config in _PATTERNS.items()
}

_ESCALATION = {
    RiskLevel.low: RiskLevel.medium,
    RiskLevel.medium: RiskLevel.high,
    RiskLevel.high: RiskLevel.critical,
    RiskLevel.critical: RiskLevel.critical,
}


def extract_insights(text: str) -> list[LegalInsight]:
    insights: list[LegalInsight] = []

    for insight_type, config in _COMPILED_PATTERNS.items():
        matched_keywords = []

        for pattern in config["keywords"]:
            match = pattern.search(text)
            if match:
                matched_keywords.append(match.group())

        if not matched_keywords:
            continue

        risk_level = config["base_risk"]
        amplifier_found = False
        for amp_pattern in config["amplifiers"]:
            amp_match = amp_pattern.search(text)
            if amp_match:
                matched_keywords.append(amp_match.group())
                amplifier_found = True

        if amplifier_found:
            risk_level = _ESCALATION[risk_level]

        confidence_score = min(1.0, 0.5 + (0.15 * len(matched_keywords)))

        insights.append(LegalInsight(
            insight_type=insight_type,
            risk_level=risk_level,
            description=f"Detected {insight_type.value} language in this section",
            matched_keywords=matched_keywords,
            confidence_score=confidence_score
        ))

    logger.info("insights extracted", count=len(insights))
    return insights


def aggregate_insights(all_insights: list[list[LegalInsight]]) -> dict:
    type_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {
        RiskLevel.low.value: 0,
        RiskLevel.medium.value: 0,
        RiskLevel.high.value: 0,
        RiskLevel.critical.value: 0,
    }

    risk_rank = {
        RiskLevel.low: 0,
        RiskLevel.medium: 1,
        RiskLevel.high: 2,
        RiskLevel.critical: 3,
    }
    highest_risk = RiskLevel.low

    for chunk_insights in all_insights:
        for insight in chunk_insights:
            type_key = insight.insight_type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1

            risk_key = insight.risk_level.value
            risk_counts[risk_key] += 1

            if risk_rank[insight.risk_level] > risk_rank[highest_risk]:
                highest_risk = insight.risk_level

    summary = {
        "counts_by_type": type_counts,
        "counts_by_risk": risk_counts,
        "overall_risk": highest_risk.value,
        "total_insights": sum(type_counts.values())
    }

    logger.info("insights aggregated", overall_risk=highest_risk.value, total=summary["total_insights"])
    return summary