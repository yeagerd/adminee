#!/usr/bin/env python3
"""
Backfill API endpoints for the office service
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta, timezone

from services.office.core.email_crawler import EmailCrawler
from services.office.core.pubsub_publisher import PubSubPublisher
from services.office.models.backfill import BackfillRequest, BackfillResponse, BackfillStatus, BackfillStatusEnum
from services.office.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backfill", tags=["backfill"])

# Global backfill job tracking
active_backfill_jobs: Dict[str, BackfillStatus] = {}

@router.post("/start", response_model=BackfillResponse)
async def start_backfill(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Start a new backfill job for the current user"""
    try:
        user_id = current_user["user_id"]
        
        # Check if user already has an active backfill job
        if user_id in active_backfill_jobs:
            existing_job = active_backfill_jobs[user_id]
            if existing_job.status in [BackfillStatusEnum.RUNNING, BackfillStatusEnum.PAUSED]:  # Use enum values
                raise HTTPException(
                    status_code=409,
                    detail=f"User already has an active backfill job: {existing_job.job_id}"
                )
        
        # Create new backfill job
        job_id = f"backfill_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        backfill_status = BackfillStatus(
            job_id=job_id,
            user_id=user_id,
            status="running",
            start_time=datetime.now(timezone.utc),
            request=request,
            progress=0,
            total_emails=0,
            processed_emails=0,
            failed_emails=0
        )
        
        # Store job status
        active_backfill_jobs[user_id] = backfill_status
        
        # Start backfill job in background
        background_tasks.add_task(
            run_backfill_job,
            job_id,
            user_id,
            request
        )
        
        logger.info(f"Started backfill job {job_id} for user {user_id}")
        
        return BackfillResponse(
            job_id=job_id,
            status=BackfillStatusEnum.STARTED,  # Use enum value
            message="Backfill job started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start backfill job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}", response_model=BackfillStatus)
async def get_backfill_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the status of a backfill job"""
    try:
        user_id = current_user["user_id"]
        
        # Find job by ID
        job = None
        for active_job in active_backfill_jobs.values():
            if active_job.job_id == job_id and active_job.user_id == user_id:
                job = active_job
                break
        
        if not job:
            raise HTTPException(status_code=404, detail="Backfill job not found")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backfill status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=List[BackfillStatus])
async def list_backfill_jobs(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by job status")
):
    """List all backfill jobs for the current user"""
    try:
        user_id = current_user["user_id"]
        
        # Filter jobs by user and optionally by status
        user_jobs = [
            job for job in active_backfill_jobs.values()
            if job.user_id == user_id
        ]
        
        if status:
            user_jobs = [job for job in user_jobs if job.status == status]
        
        return user_jobs
        
    except Exception as e:
        logger.error(f"Failed to list backfill jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/pause")
async def pause_backfill_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Pause a running backfill job"""
    try:
        user_id = current_user["user_id"]
        
        # Find and pause job
        job = _find_user_job(job_id, user_id)
        if job.status != BackfillStatusEnum.RUNNING:  # Use enum value
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause job with status: {job.status}"
            )
        
        job.status = BackfillStatusEnum.PAUSED  # Use enum value
        job.pause_time = datetime.now(timezone.utc)
        
        logger.info(f"Paused backfill job {job_id}")
        
        return {"message": "Backfill job paused successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause backfill job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/resume")
async def resume_backfill_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Resume a paused backfill job"""
    try:
        user_id = current_user["user_id"]
        
        # Find and resume job
        job = _find_user_job(job_id, user_id)
        if job.status != BackfillStatusEnum.PAUSED:  # Use enum value
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume job with status: {job.status}"
            )
        
        job.status = BackfillStatusEnum.RUNNING  # Use enum value
        job.resume_time = datetime.now(timezone.utc)
        
        # Resume job in background
        background_tasks.add_task(
            run_backfill_job,
            job_id,
            user_id,
            job.request,
            resume_from=job.processed_emails
        )
        
        logger.info(f"Resumed backfill job {job_id}")
        
        return {"message": "Backfill job resumed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume backfill job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{job_id}")
async def cancel_backfill_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a backfill job"""
    try:
        user_id = current_user["user_id"]
        
        # Find and cancel job
        job = _find_user_job(job_id, user_id)
        if job.status in [BackfillStatusEnum.COMPLETED, BackfillStatusEnum.FAILED]:  # Use enum values
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status: {job.status}"
            )
        
        job.status = BackfillStatusEnum.CANCELLED  # Use enum value
        job.end_time = datetime.now(timezone.utc)
        
        logger.info(f"Cancelled backfill job {job_id}")
        
        return {"message": "Backfill job cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel backfill job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_backfill_job(
    job_id: str,
    user_id: str,
    request: BackfillRequest,
    resume_from: int = 0
):
    """Run the backfill job in the background"""
    try:
        # Update job status
        job = active_backfill_jobs[user_id]
        job.status = BackfillStatusEnum.RUNNING  # Use enum value
        
        # Initialize email crawler and pubsub publisher
        email_crawler = EmailCrawler(user_id, request.provider, max_email_count=10)  # Limit to 10 emails for testing
        pubsub_publisher = PubSubPublisher()
        
        # Start crawling emails
        total_emails = await email_crawler.get_total_email_count()
        job.total_emails = total_emails
        
        logger.info(f"Starting backfill job {job_id} for {total_emails} emails")
        
        # Process emails in batches
        batch_size = request.batch_size or 100
        processed_count = resume_from
        
        async for email_batch in email_crawler.crawl_emails(
            batch_size=batch_size,
            start_date=request.start_date,
            end_date=request.end_date,
            folders=request.folders,
            resume_from=resume_from
        ):
            # Publish emails to pubsub
            for email in email_batch:
                try:
                    await pubsub_publisher.publish_email(email)
                    processed_count += 1
                    job.processed_emails = processed_count
                    job.progress = (processed_count / total_emails) * 100
                    
                except RuntimeError as e:
                    # Fatal error (e.g., topic not found) - halt the job
                    logger.error(f"Fatal error in backfill job {job_id}: {e}")
                    job.status = BackfillStatusEnum.FAILED  # Use enum value
                    job.end_time = datetime.now(timezone.utc)
                    job.error_message = f"Fatal Pub/Sub error: {e}"
                    return
                except Exception as e:
                    logger.error(f"Failed to publish email {email.get('id')}: {e}")
                    job.failed_emails += 1
            
            # Check if job was cancelled or paused
            if job.status in [BackfillStatusEnum.CANCELLED, BackfillStatusEnum.PAUSED]:  # Use enum values
                logger.info(f"Backfill job {job_id} {job.status}")
                return
        
        # Mark job as completed
        job.status = BackfillStatusEnum.COMPLETED  # Use enum value
        job.end_time = datetime.now(timezone.utc)
        job.progress = 100
        
        logger.info(f"Completed backfill job {job_id}: {processed_count} emails processed")
        
    except Exception as e:
        logger.error(f"Backfill job {job_id} failed: {e}")
        if user_id in active_backfill_jobs:
            job = active_backfill_jobs[user_id]
            job.status = BackfillStatusEnum.FAILED  # Use enum value
            job.end_time = datetime.now(timezone.utc)
            job.error_message = str(e)

def _find_user_job(job_id: str, user_id: str) -> BackfillStatus:
    """Find a job by ID for the specified user"""
    for job in active_backfill_jobs.values():
        if job.job_id == job_id and job.user_id == user_id:
            return job
    
    raise HTTPException(status_code=404, detail="Backfill job not found")
