"""Natural-language deadline parsing and automatic deadline creation."""

from __future__ import annotations

import datetime as dt
import re
from typing import Dict, Optional

from sqlalchemy.orm import Session

from db.models import CaseDeadline
from .timeline_service import timeline_service


_APPEAL_CONTEXT_PATTERNS = (
    r"file(?:\s+an?)?\s+appeal",
    r"notice\s+of\s+appeal",
    r"appeal\s+(?:should|must)\s+be\s+filed",
    r"appeal\s+(?:to|within|in|against)",
    r"challenge(?:d)?(?:\s+the)?(?:\s+\w+)?",
)


def _extract_days_from_text(text: str) -> Optional[int]:
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    if text.isdigit():
        return int(text)

    appeal_context = r"(?:" + "|".join(_APPEAL_CONTEXT_PATTERNS) + r")"
    patterns = (
        re.compile(
            rf"\b(?P<context>{appeal_context})\b(?:[^.\n]{{0,80}})?\b(?P<days>\d+)\s*days?\b",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?P<days>\d+)\s*days?\b(?:[^.\n]{{0,80}})?\b(?P<context>{appeal_context})\b",
            re.IGNORECASE,
        ),
    )

    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return int(match.group("days"))

    return None


def _validate_days_value(days: int) -> bool:
    return 1 <= days <= 365


def auto_create_deadlines_from_remedies(
    db: Session,
    user_id: int,
    case_id: int,
    case_title: str,
    remedies: Dict,
    document_id: int,
) -> None:
    appeal_days = remedies.get("appeal_days")
    if not appeal_days:
        return

    appeal_days_str = str(appeal_days).strip()
    days = _extract_days_from_text(appeal_days_str)
    if days is None or not _validate_days_value(days):
        return

    current_time = dt.datetime.now(dt.timezone.utc)
    deadline_date = current_time + dt.timedelta(days=days)

    existing_deadline = db.query(CaseDeadline).filter(
        CaseDeadline.case_id == case_id,
        CaseDeadline.deadline_type == "appeal",
        CaseDeadline.is_completed == False,
        CaseDeadline.deadline_date >= deadline_date - dt.timedelta(days=1),
        CaseDeadline.deadline_date <= deadline_date + dt.timedelta(days=1),
    ).first()

    if existing_deadline:
        return

    deadline = CaseDeadline(
        user_id=user_id,
        case_id=case_id,
        case_title=case_title,
        deadline_date=deadline_date,
        deadline_type="appeal",
        description=f"Appeal deadline - {remedies.get('appeal_court', 'Unknown court')}",
    )
    db.add(deadline)
    db.flush()

    timeline_service.create_event(
        db=db,
        case_id=case_id,
        event_type="deadline_created",
        description=f"Appeal deadline set for {deadline_date.strftime('%d %B %Y')} based on document analysis",
        metadata={
            "deadline_id": deadline.id,
            "document_id": document_id,
            "source_days": days,
            "original_text": appeal_days_str,
        },
    )
