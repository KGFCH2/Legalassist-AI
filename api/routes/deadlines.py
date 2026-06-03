"""
Deadline Endpoints
GET /api/v1/deadlines/upcoming - Get user's upcoming deadlines
GET /api/v1/deadlines/{deadline_id} - Get deadline details
POST /api/v1/deadlines - Create new deadline
"""
from fastapi import APIRouter, HTTPException, status, Depends
from api.models import DeadlineResponse, UpcomingDeadlinesResponse
from api.auth import get_current_user, CurrentUser
import structlog
from datetime import datetime, timezone, timedelta

from database import (
    get_db,
    get_upcoming_deadlines,
    get_deadline_by_id,
    create_case_deadline,
    CaseDeadline,
)

router = APIRouter(prefix="/api/v1/deadlines", tags=["deadlines"])
logger = structlog.get_logger(__name__)


def _to_response(d: CaseDeadline) -> DeadlineResponse:
    now = datetime.now(timezone.utc)
    due = d.deadline_date
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    days_until = max(0, (due - now).days)
    if d.is_completed:
        status_val = "completed"
    elif due < now:
        status_val = "overdue"
    else:
        status_val = "pending"
    return DeadlineResponse(
        deadline_id=str(d.id),
        user_id=str(d.user_id),
        case_id=str(d.case_id),
        title=d.case_title,
        description=d.description or "",
        due_date=due,
        days_until_due=days_until,
        priority=d.priority or "medium",
        status=status_val,
        reminder_enabled=d.reminder_enabled,
        reminder_days=d.reminder_days,
        created_at=d.created_at,
    )


@router.get(
    "/upcoming",
    response_model=UpcomingDeadlinesResponse,
    summary="Get user's upcoming deadlines"
)
async def get_upcoming_deadlines_endpoint(
    days: int = 30,
    current_user: CurrentUser = Depends(get_current_user)
) -> UpcomingDeadlinesResponse:
    """Get upcoming deadlines for user"""

    logger.info(
        "Fetching upcoming deadlines",
        user_id=current_user.user_id,
        days=days
    )

    db = get_db()
    try:
        user_id_int = int(current_user.user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    deadlines = get_upcoming_deadlines(db, days_before=days, user_id=user_id_int)
    responses = [_to_response(d) for d in deadlines]
    critical = sum(1 for r in responses if r.priority == "critical")
    high = sum(1 for r in responses if r.priority == "high")
    medium = sum(1 for r in responses if r.priority == "medium")
    low = sum(1 for r in responses if r.priority == "low")
    return UpcomingDeadlinesResponse(
        user_id=current_user.user_id,
        total_deadlines=len(responses),
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        low_count=low,
        deadlines=responses,
        generated_at=datetime.now(timezone.utc)
    )


@router.get(
    "/{deadline_id}",
    response_model=DeadlineResponse,
    summary="Get deadline details"
)
async def get_deadline_details(
    deadline_id: int,
    current_user: CurrentUser = Depends(get_current_user)
) -> DeadlineResponse:
    """Get complete deadline details"""

    logger.info(
        "Fetching deadline",
        deadline_id=deadline_id,
        user_id=current_user.user_id
    )

    db = get_db()
    try:
        user_id_int = int(current_user.user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    deadline = get_deadline_by_id(db, deadline_id=deadline_id, user_id=user_id_int)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return _to_response(deadline)


@router.post(
    "",
    response_model=DeadlineResponse,
    summary="Create new deadline"
)
async def create_deadline(
    case_id: int,
    title: str,
    due_date: datetime,
    description: str = "",
    deadline_type: str = "filing",
    priority: str = "medium",
    reminder_enabled: bool = True,
    reminder_days: int = 7,
    current_user: CurrentUser = Depends(get_current_user)
) -> DeadlineResponse:
    """Create a new deadline"""

    logger.info(
        "Creating deadline",
        user_id=current_user.user_id,
        title=title
    )

    db = get_db()
    try:
        user_id_int = int(current_user.user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    try:
        deadline = create_case_deadline(
            db=db,
            user_id=user_id_int,
            case_id=case_id,
            case_title=title,
            deadline_date=due_date,
            deadline_type=deadline_type,
            description=description,
        )
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    deadline.priority = priority
    deadline.reminder_enabled = reminder_enabled
    deadline.reminder_days = reminder_days
    db.commit()
    db.refresh(deadline)
    return _to_response(deadline)


@router.put(
    "/{deadline_id}",
    response_model=DeadlineResponse,
    summary="Update deadline"
)
async def update_deadline(
    deadline_id: int,
    title: str = None,
    due_date: datetime = None,
    deadline_type: str = None,
    priority: str = None,
    reminder_enabled: bool = None,
    reminder_days: int = None,
    current_user: CurrentUser = Depends(get_current_user)
) -> DeadlineResponse:
    """Update a deadline"""

    logger.info(
        "Updating deadline",
        deadline_id=deadline_id,
        user_id=current_user.user_id
    )

    db = get_db()
    try:
        user_id_int = int(current_user.user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    deadline = get_deadline_by_id(db, deadline_id=deadline_id, user_id=user_id_int)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    if title is not None:
        deadline.case_title = title
    if due_date is not None:
        deadline.deadline_date = due_date
    if deadline_type is not None:
        deadline.deadline_type = deadline_type
    if priority is not None:
        deadline.priority = priority
    if reminder_enabled is not None:
        deadline.reminder_enabled = reminder_enabled
    if reminder_days is not None:
        deadline.reminder_days = reminder_days
    db.commit()
    db.refresh(deadline)
    return _to_response(deadline)
