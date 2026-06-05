"""
Report Generation Endpoints
POST /api/v1/reports/generate - Generate report asynchronously
GET /api/v1/reports/{report_id} - Get report status
GET /api/v1/reports/{report_id}/download - Download report
"""
import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse
from pathlib import Path

from api.models import ReportGenerationRequest, ReportGenerationResponse
from api.auth import get_current_user, CurrentUser
from celery_app import generate_report_task
from report_service import get_report_by_id
import structlog
from datetime import datetime

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
logger = structlog.get_logger(__name__)


@router.post(
    "/generate",
    response_model=ReportGenerationResponse,
    summary="Generate report asynchronously"
)
async def generate_report(
    request: ReportGenerationRequest,
    current_user: CurrentUser = Depends(get_current_user)
) -> ReportGenerationResponse:
    """
    Generate a legal report asynchronously
    
    - **case_id**: Case ID to generate report for
    - **report_type**: comprehensive, summary, or legal_brief
    - **include_remedies**: Include remedy clauses
    - **include_timeline**: Include case timeline
    - **include_similar_cases**: Include similar cases
    - **format**: pdf or docx
    - **style**: formal or casual
    
    Returns immediately with job ID
    """
    
    logger.info(
        "Starting report generation",
        user_id=current_user.user_id,
        case_id=request.case_id,
        report_type=request.report_type
    )
    
    # Queue async task
    task = generate_report_task.delay(
        user_id=current_user.user_id,
        case_id=request.case_id,
        report_type=request.report_type,
        format=request.format
    )
    
    return ReportGenerationResponse(
        report_id=str(uuid.uuid4()),
        job_id=task.id,
        case_id=request.case_id,
        status="pending",
        report_type=request.report_type,
        format=request.format,
        created_at=datetime.utcnow()
    )


@router.get(
    "/{report_id}",
    response_model=ReportGenerationResponse,
    summary="Get report status"
)
async def get_report_status(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user)
) -> ReportGenerationResponse:
    """Get status of report generation job with ownership validation."""

    report = get_report_by_id(report_id, current_user.user_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return ReportGenerationResponse(
        report_id=report["report_id"],
        job_id=report_id,
        case_id="unknown",
        status=report["status"],
        report_type="comprehensive",
        format="pdf",
        download_url=report["download_url"],
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow() if report["status"] == "completed" else None,
    )


@router.get(
    "/{report_id}/download",
    summary="Download generated report"
)
async def download_report(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Download the generated report file."""

    report = get_report_by_id(report_id, current_user.user_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=f"Report is still {report['status']}",
        )

    if not report["file_path"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found",
        )

    return FileResponse(
        path=report["file_path"],
        media_type="application/pdf",
        filename=Path(report["file_path"]).name,
    )



@router.get(
    "",
    summary="List user's reports"
)
async def list_reports(
    limit: int = 10,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Get list of generated reports for current user"""
    
    return {
        "total": 0,
        "limit": limit,
        "offset": offset,
        "reports": []
    }
