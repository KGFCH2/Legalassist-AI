import os
import uuid
import structlog
import json
import re
import hashlib
import io
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from types import SimpleNamespace
from celery import Celery, Task
from api.validation import validate_file_url, fetch_url_safe

# Database & Core Imports
from database import SessionLocal, DocumentProcessingState
from core.app_utils import (
    PipelineStateManager, extract_text_from_pdf, get_client, 
    build_prompt, build_remedies_prompt, parse_remedies_response, 
    compress_text
)
from api.idempotency import IdempotencyManager
from api.validation import ValidationConfig
from db.crud.reports import update_report_status
from db.session import db_session
from database import Attachment, User, SessionLocal, get_case_by_id, get_case_document_by_id, update_case_document, create_timeline_event

# ============================================================================
# INITIALIZATION & LOGGING
# ============================================================================

# Initialize the settings object to fetch global configurations
settings = get_settings()

# Initialize
logger = structlog.get_logger(__name__)
celery_app = Celery("legalassist", broker=os.getenv("REDIS_URL"), backend=os.getenv("REDIS_URL"))

@celery_app.task(bind=True, name="analyze_document")
def analyze_document_task(self, user_id, document_id, text=None, file_bytes=None, document_type="unknown", file_path=None, file_url=None) -> Dict[str, Any]:
    db = SessionLocal()
    idemp = IdempotencyManager()
    
    # 1. State Recovery
    state = PipelineStateManager.get_state(db, document_id)
    stage = state.current_stage if state else "PENDING"
    data = state.stage_data if state else {}

    try:
        # Phase 1: Text Pre-processing
        self.update_state(
            state="PROGRESS",
            meta={"status": "Extracting and cleaning text", "progress": 25},
        )

        logger.info(
            "Starting document analysis",
            task_id=self.request.id,
            user_id=user_id,
            document_id=document_id,
        )
        
        extracted_text = text
        if extracted_text:
            if len(extracted_text.encode("utf-8")) > ValidationConfig.MAX_TEXT_LENGTH:
                raise ValueError(f"Input text exceeds max limit of {ValidationConfig.MAX_TEXT_LENGTH} bytes.")
        if not extracted_text and file_bytes:
            if len(file_bytes) > ValidationConfig.MAX_TEXT_LENGTH:
                raise ValueError(f"File too large: {len(file_bytes)} bytes exceeds limit of {ValidationConfig.MAX_TEXT_LENGTH} bytes.")
            extracted_text = extract_text_from_pdf(io.BytesIO(file_bytes))
        if not extracted_text:
            if file_url:
                response = requests.get(file_url, timeout=30)
                response.raise_for_status()
                if len(response.content) > ValidationConfig.MAX_TEXT_LENGTH:
                    raise ValueError(f"Downloaded file too large: {len(response.content)} bytes exceeds limit of {ValidationConfig.MAX_TEXT_LENGTH} bytes.")
                content_type = response.headers.get("Content-Type", "")
                if "application/pdf" in content_type or file_url.lower().endswith(".pdf"):
                    extracted_text = extract_text_from_pdf(io.BytesIO(response.content))
                else:
                    extracted_text = response.content.decode("utf-8", errors="ignore")
            elif file_path:
                # Validate the path is within the upload jail before any
                # file system access.  This blocks path traversal attacks
                # where a crafted file_path (e.g. ../../etc/passwd) passed
                # through the Celery JSON queue could read arbitrary files.
                from api.validation import validate_upload_file_path
                file_path = validate_upload_file_path(file_path)
                if os.path.getsize(file_path) > ValidationConfig.MAX_TEXT_LENGTH:
                    raise ValueError(f"File too large: {os.path.getsize(file_path)} bytes exceeds limit of {ValidationConfig.MAX_TEXT_LENGTH} bytes.")
                if file_path.lower().endswith(".pdf"):
                    with open(file_path, "rb") as f:
                        extracted_text = extract_text_from_pdf(io.BytesIO(f.read()))
                else:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        extracted_text = f.read()
        if not extracted_text:
            raise ValueError("No text provided or extracted from document.")

        # Enforce size limits
        if len(extracted_text.encode("utf-8")) > ValidationConfig.MAX_TEXT_LENGTH:
            raise ValueError(f"Extracted text exceeds max limit of {ValidationConfig.MAX_TEXT_LENGTH} bytes.")

        # Phase 2: Content Analysis
        self.update_state(
            state="PROGRESS", meta={"status": "Analyzing legal content", "progress": 50}
        )
        
        safe_text = compress_text(extracted_text)
        client = get_client()
        if not client:
            raise RuntimeError("Failed to initialize LLM client.")

        summary_prompt = build_prompt(safe_text, "English")
        if _celery_tracer:
            with _celery_tracer.start_as_current_span(
                f"llm.{Config.DEFAULT_MODEL}.summary",
                attributes={
                    "llm.model": Config.DEFAULT_MODEL,
                    "llm.operation": "summary",
                    "celery.task_id": self.request.id or "",
                },
            ) as span:
                summary_response = client.chat.completions.create(
                    model=Config.DEFAULT_MODEL,
                    messages=[{"role": "user", "content": summary_prompt}],
                    max_tokens=800,
                    temperature=0.3,
                )
                if hasattr(summary_response, 'usage') and summary_response.usage:
                    span.set_attribute("llm.prompt_tokens", summary_response.usage.prompt_tokens or 0)
                    span.set_attribute("llm.completion_tokens", summary_response.usage.completion_tokens or 0)
                    span.set_attribute("llm.total_tokens", summary_response.usage.total_tokens or 0)
                raw_summary = summary_response.choices[0].message.content
        else:
            summary_response = client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=800,
                temperature=0.3,
            )
            raw_summary = summary_response.choices[0].message.content
        # Extract JSON bullets if possible, otherwise use raw text
        summary_text = ""
        key_points = []
        try:
            import json
            import re
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_summary, re.DOTALL)
            json_str = match.group(1) if match else raw_summary
            data = json.loads(json_str)
            key_points = data.get("bullets", [])
            summary_text = " ".join(key_points)
        except Exception:
            summary_text = raw_summary

        # Phase 3: Remedy Extraction
        self.update_state(
            state="PROGRESS",
            meta={"status": "Extracting identified remedies", "progress": 75},
        )
        
        remedies_prompt = build_remedies_prompt(safe_text, "English")
        if _celery_tracer:
            with _celery_tracer.start_as_current_span(
                f"llm.{Config.DEFAULT_MODEL}.remedies",
                attributes={
                    "llm.model": Config.DEFAULT_MODEL,
                    "llm.operation": "remedies",
                    "celery.task_id": self.request.id or "",
                },
            ) as span:
                remedies_response = client.chat.completions.create(
                    model=Config.DEFAULT_MODEL,
                    messages=[{"role": "user", "content": remedies_prompt}],
                    max_tokens=900,
                    temperature=0.3,
                )
                if hasattr(remedies_response, 'usage') and remedies_response.usage:
                    span.set_attribute("llm.prompt_tokens", remedies_response.usage.prompt_tokens or 0)
                    span.set_attribute("llm.completion_tokens", remedies_response.usage.completion_tokens or 0)
                    span.set_attribute("llm.total_tokens", remedies_response.usage.total_tokens or 0)
                remedies_data = parse_remedies_response(remedies_response.choices[0].message.content)
        else:
            remedies_response = client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[{"role": "user", "content": remedies_prompt}],
                max_tokens=900,
                temperature=0.3,
            )
            remedies_data = parse_remedies_response(remedies_response.choices[0].message.content)

        # Phase 4: Finalization
        self.update_state(
            state="PROGRESS",
            meta={"status": "Finalizing analysis results", "progress": 90},
        )
        
        analysis_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Combine remedies into a structured array
        remedies_list = []
        if remedies_data.get("first_action"):
            remedies_list.append(f"Action: {remedies_data['first_action']}")
        if remedies_data.get("can_appeal") == "yes":
            remedies_list.append(f"Appeal allowed in {remedies_data.get('appeal_court', 'court')} within {remedies_data.get('appeal_days', 'unknown')} days.")
            
            PipelineStateManager.update_stage(db, document_id, "OCR_DONE", {"text": extracted_text})
            stage = "OCR_DONE"
            data["text"] = extracted_text

        # STAGE 2: Summary
        if stage == "OCR_DONE":
            safe_text = compress_text(data["text"])
            client = get_client()
            summary_prompt = build_prompt(safe_text, "English")
            # ... [Paste your LLM call logic here] ...
            raw_summary = "..." # result from LLM
            
            # (Keep your summary JSON parsing logic here)
            summary_text = raw_summary 
            key_points = [] 
            
            PipelineStateManager.update_stage(db, document_id, "SUMMARY_DONE", {"summary": summary_text, "key_points": key_points})
            stage = "SUMMARY_DONE"
            data.update({"summary": summary_text, "key_points": key_points})

        # STAGE 3: Remedies
        if stage == "SUMMARY_DONE":
            remedies_prompt = build_remedies_prompt(compress_text(data["text"]), "English")
            # ... [Paste your remedies LLM call here] ...
            remedies_data = parse_remedies_response("...") 
            
            final_result = {"status": "complete", "remedies": remedies_data}
            PipelineStateManager.update_stage(db, document_id, "COMPLETED", {"result": final_result})
            return final_result

        return data.get("result", {"status": "pending"})
    finally:
        db.close()