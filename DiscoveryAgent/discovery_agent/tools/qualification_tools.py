"""BANT scoring and opportunity persistence (PostgreSQL ``opportunities`` table).

Scoring is deterministic: each BANT component maps to 0-3, the weighted score
is their mean, and the 0-100 score drives the A/B/C priority bucket.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sales_common import db


# ==================== BANT SCORING ====================

def calculate_budget_score(budget: Optional[str]) -> int:
    """Budget score (0-3)."""
    if not budget:
        return 0
    budget = budget.lower()
    if "approved" in budget:
        return 3
    if "identified" in budget:
        return 2
    if "estimated" in budget:
        return 1
    return 0


def calculate_authority_score(authority: Optional[str]) -> int:
    """Authority score (0-3)."""
    if not authority:
        return 0
    authority = authority.lower()
    if "confirmed" in authority:
        return 3
    if "identified" in authority:
        return 2
    if "suspected" in authority:
        return 1
    return 0


def calculate_need_score(need: Optional[str]) -> int:
    """Need score (0-3)."""
    if not need:
        return 0
    need = need.lower()
    if "high" in need or "critical" in need:
        return 3
    if "medium" in need or "moderate" in need:
        return 2
    if "low" in need:
        return 1
    return 0


def calculate_timing_score(timeline_days: Optional[int]) -> int:
    """Timing score (0-3)."""
    if not timeline_days:
        return 0
    if timeline_days <= 30:
        return 3
    if timeline_days <= 90:
        return 2
    if timeline_days <= 180:
        return 1
    return 0


def get_priority_bucket(score: float) -> str:
    """Priority bucket from the 0-100 BANT score."""
    if score >= 66.7:
        return "A (High)"
    if score >= 33.3:
        return "B (Medium)"
    return "C (Low)"


def identify_data_gaps(
    budget: Optional[str], authority: Optional[str], need: Optional[str], timeline: Optional[int]
) -> str:
    """Comma-separated list of missing BANT components ('' when complete)."""
    gaps = []
    if not budget or budget.lower() == "unknown":
        gaps.append("Budget")
    if not authority or authority.lower() == "unknown":
        gaps.append("Authority")
    if not need or need.lower() == "unknown":
        gaps.append("Need")
    if not timeline:
        gaps.append("Timeline")
    return ", ".join(gaps) if gaps else ""


# ==================== PERSISTENCE ====================

def get_opportunity_qualification(
    company_name: str, opportunity_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """BANT qualification rows for a company (optionally one opportunity)."""
    query = """
    SELECT o."Company Name", o."Opportunity Name", o."Stage", o."Total MRC (Est)",
           o."Budget", o."Authority", o."Need", o."Timeline (days)",
           o."Target Close Date", o."Next Step",
           o."BANT_Budget_Score", o."BANT_Authority_Score", o."BANT_Need_Score",
           o."BANT_Timing_Score", o."BANT_Weighted_0to3", o."BANT_Score_0to100",
           o."BANT_Priority_Bucket", o."BANT_Data_Gaps"
    FROM opportunities o
    WHERE o."Company Name" = %s
    """
    params: list[Any] = [company_name]
    if opportunity_name:
        query += ' AND o."Opportunity Name" = %s'
        params.append(opportunity_name)
    query += ' ORDER BY o."BANT_Score_0to100" DESC NULLS LAST'
    return db.fetch_all(query, params)


def find_opportunity(conn, company_name: str, opportunity_name: str) -> Optional[Dict[str, Any]]:
    """Existing opportunity with the same company + name (case-insensitive), else None."""
    return conn.execute(
        'SELECT "Company Name", "Opportunity Name", "Stage", "BANT_Score_0to100", '
        '"BANT_Priority_Bucket" FROM opportunities '
        'WHERE lower("Company Name") = lower(%s) AND lower("Opportunity Name") = lower(%s) '
        "LIMIT 1",
        (company_name.strip(), opportunity_name.strip()),
    ).fetchone()


def add_opportunity(
    company_name: str,
    opportunity_name: str,
    stage: str,
    total_mrc: Optional[float] = None,
    budget: Optional[str] = None,
    authority: Optional[str] = None,
    need: Optional[str] = None,
    timeline_days: Optional[int] = None,
    target_close_date: Optional[str] = None,
    next_step: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert an opportunity with computed BANT scores.

    ``opportunities`` has no unique key, so duplicates are detected explicitly:
    when the company already has an opportunity with the same name
    (case-insensitive) nothing is inserted. The check and insert run in one
    transaction under a per-company advisory lock.

    Returns ``{"created": bool, "duplicate": bool, "existing": row | None}``.
    """
    bant_budget = calculate_budget_score(budget)
    bant_authority = calculate_authority_score(authority)
    bant_need = calculate_need_score(need)
    bant_timing = calculate_timing_score(timeline_days)

    bant_weighted = (bant_budget + bant_authority + bant_need + bant_timing) / 4
    bant_score_100 = (bant_weighted / 3) * 100
    bant_priority = get_priority_bucket(bant_score_100)
    bant_gaps = identify_data_gaps(budget, authority, need, timeline_days)

    # "Total MRC (Est)" is BIGINT in the schema.
    mrc = round(total_mrc) if total_mrc is not None else None
    now = db.now_iso()

    query = """
    INSERT INTO opportunities (
        "Company Name", "Opportunity Name", "Stage", "Total MRC (Est)",
        "Budget", "Authority", "Need", "Timeline (days)", "Target Close Date", "Next Step",
        "BANT_Budget_Score", "BANT_Authority_Score", "BANT_Need_Score", "BANT_Timing_Score",
        "BANT_Weighted_0to3", "BANT_Score_0to100", "BANT_Priority_Bucket", "BANT_Data_Gaps",
        created_at, updated_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    with db.transaction() as conn:
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtext('discovery.opportunity:' || lower(%s)))",
            (company_name.strip(),),
        )
        existing = find_opportunity(conn, company_name, opportunity_name)
        if existing:
            return {"created": False, "duplicate": True, "existing": existing}
        rows = conn.execute(query, (
            company_name, opportunity_name, stage, mrc,
            budget, authority, need, timeline_days, target_close_date, next_step,
            bant_budget, bant_authority, bant_need, bant_timing,
            bant_weighted, bant_score_100, bant_priority, bant_gaps,
            now, now,
        )).rowcount
    return {"created": rows > 0, "duplicate": False, "existing": None}
