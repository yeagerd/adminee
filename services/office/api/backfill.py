#!/usr/bin/env python3
"""
Backfill API endpoints for the office service
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from services.common.logging_config import get_logger
from services.office.core.auth import verify_backfill_api_key
from services.office.core.email_crawler import EmailCrawler
from services.office.core.pubsub_publisher import PubSubPublisher
from services.office.core.settings import get_settings
from services.office.models.backfill import (
    BackfillRequest,
    BackfillResponse,
    BackfillStatus,
    BackfillStatusEnum,
)

logger = get_logger(__name__)

internal_router = APIRouter(prefix="/internal/backfill", tags=["internal-backfill"])

# Global backfill job tracking
active_backfill_jobs: Dict[str, BackfillStatus] = {}


async def _resolve_email_to_user_id(email: str) -> Optional[str]:
    """Resolve email address to internal user ID using the user service"""
    try:
        import httpx

        user_service_url = get_settings().USER_SERVICE_URL
        # Log what we're getting from settings
        api_key_from_settings = get_settings().api_office_user_key
        logger.info(f"Email resolution - User service URL: {user_service_url}")
        logger.info(
            f"Email resolution - API key from settings: {api_key_from_settings}"
        )

        # Use the API key from settings if available, otherwise log an error
        if api_key_from_settings:
            api_key = api_key_from_settings
            logger.info(
                f"Email resolution - Using API key from settings: {api_key[:10]}..."
            )
        else:
            logger.error("Email resolution - No API key configured in settings")
            return None

        if not user_service_url or not api_key:
            logger.error("User service URL or API key not configured")
            return None

        # Call user service to resolve email to user ID
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{user_service_url}/v1/internal/users/exists",
                params={"email": email},
                headers={"X-API-Key": api_key},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("exists"):
                    user_id = data.get("user_id")
                    logger.info(f"Resolved email {email} to user ID {user_id}")
                    return user_id
                else:
                    logger.warning(f"Email {email} not found in user service")
                    return None
            else:
                logger.error(
                    f"Failed to resolve email {email}: {response.status_code} - {response.text}"
                )
                return None

    except Exception as e:
        logger.error(f"Error resolving email {email} to user ID: {e}")
        return None


# Internal endpoints for service-to-service communication
@internal_router.post("/start", response_model=BackfillResponse)
async def start_internal_backfill(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Query(..., description="User email address"),
    api_key: str = Depends(verify_backfill_api_key),
) -> BackfillResponse:
    """Internal endpoint for starting backfill jobs (service-to-service)"""
    try:
        # Validate user_id format (basic email validation)
        if "@" not in user_id or "." not in user_id:
            raise HTTPException(
                status_code=400, detail="Invalid email format for user_id"
            )

        # Check if user already has an active backfill job
        if user_id in active_backfill_jobs:
            existing_job = active_backfill_jobs[user_id]
            if existing_job.status in [
                BackfillStatusEnum.RUNNING,
                BackfillStatusEnum.PAUSED,
            ]:
                raise HTTPException(
                    status_code=409,
                    detail=f"User already has an active backfill job: {existing_job.job_id}",
                )

        # Create new backfill job
        job_id = (
            f"backfill_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        backfill_status = BackfillStatus(
            job_id=job_id,
            user_id=user_id,
            status=BackfillStatusEnum.RUNNING,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            pause_time=None,
            resume_time=None,
            request=request,
            progress=0,
            total_emails=0,
            processed_emails=0,
            failed_emails=0,
            error_message=None,
        )

        # Store job status
        active_backfill_jobs[user_id] = backfill_status

        # Start backfill job in background
        background_tasks.add_task(run_backfill_job, job_id, user_id, request)

        logger.info(f"Started internal backfill job {job_id} for user {user_id}")

        return BackfillResponse(
            job_id=job_id,
            status=BackfillStatusEnum.STARTED,
            message="Internal backfill job started successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start internal backfill job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Function end

@internal_router.get("/status/{job_id}", response_model=BackfillStatus)
async def get_internal_backfill_status(
    job_id: str,
    user_id: str = Query(..., description="User email address"),
    api_key: str = Depends(verify_backfill_api_key),
) -> BackfillStatus:
    """Internal endpoint for getting backfill job status"""
    try:
        # Find job by ID and user_id
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
        logger.error(f"Failed to get internal backfill job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@internal_router.get("/status", response_model=List[BackfillStatus])
async def list_internal_backfill_jobs(
    user_id: str = Query(..., description="User email address"),
    api_key: str = Depends(verify_backfill_api_key),
) -> List[BackfillStatus]:
    """Internal endpoint for listing backfill jobs for a user"""
    try:
        # Filter jobs by user_id
        user_jobs = [
            job for job in active_backfill_jobs.values() if job.user_id == user_id
        ]

        return user_jobs

    except Exception as e:
        logger.error(f"Failed to list internal backfill jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@internal_router.delete("/{job_id}")
async def cancel_internal_backfill_job(
    job_id: str,
    user_id: str = Query(..., description="User email address"),
    api_key: str = Depends(verify_backfill_api_key),
) -> Dict[str, str]:
    """Internal endpoint for cancelling a backfill job"""
    try:
        # Find job by ID and user_id
        job = None
        for active_job in active_backfill_jobs.values():
            if active_job.job_id == job_id and active_job.user_id == user_id:
                job = active_job
                break

        if not job:
            raise HTTPException(status_code=404, detail="Backfill job not found")

        if job.status in [
            BackfillStatusEnum.COMPLETED,
            BackfillStatusEnum.FAILED,
            BackfillStatusEnum.CANCELLED,
        ]:
            raise HTTPException(
                status_code=400, detail=f"Cannot cancel job with status: {job.status}"
            )

        # Cancel the job
        job.status = BackfillStatusEnum.CANCELLED
        job.end_time = datetime.now(timezone.utc)

        logger.info(f"Cancelled internal backfill job {job_id}")

        return {"message": f"Backfill job {job_id} cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel internal backfill job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_backfill_job(
    job_id: str, user_id: str, request: BackfillRequest, resume_from: int = 0
) -> None:
    """Run the backfill job in the background"""
    try:
        # Update job status
        job = active_backfill_jobs[user_id]
        job.status = BackfillStatusEnum.RUNNING  # Use enum value

        # Resolve email to internal user ID for API calls
        internal_user_id = await _resolve_email_to_user_id(user_id)
        if not internal_user_id:
            raise Exception(f"Failed to resolve email {user_id} to internal user ID")

        # Initialize email crawler and pubsub publisher
        email_crawler = EmailCrawler(
            internal_user_id,
            request.provider,
            user_id,
            max_email_count=request.max_emails or 10,
        )
        pubsub_publisher = PubSubPublisher()

        # Start crawling emails
        total_emails = await email_crawler.get_total_email_count()
        job.total_emails = total_emails

        logger.info(
            f"Starting backfill job {job_id} for {total_emails} emails (max: {request.max_emails or 'unlimited'})",
            extra={
                "job_id": job_id,
                "user_id": user_id,
                "total_emails": total_emails,
                "max_emails": request.max_emails,
                "provider": request.provider,
            },
        )

        # Process emails in batches
        batch_size = request.batch_size or 100
        processed_count = resume_from

        async for email_batch in email_crawler.crawl_emails(
            batch_size=batch_size,
            start_date=request.start_date,
            end_date=request.end_date,
            folders=request.folders,
            resume_from=resume_from,
            max_emails=request.max_emails,
        ):
            # Publish emails to pubsub
            for email in email_batch:
                try:
                    await pubsub_publisher.publish_email(email)
                    processed_count += 1
                    job.processed_emails = processed_count
                    # Update progress based on max_emails if available, otherwise use total_emails
                    if request.max_emails:
                        job.progress = min(
                            100.0, (processed_count / request.max_emails) * 100
                        )
                    else:
                        job.progress = min(
                            100.0, (processed_count / total_emails) * 100
                        )

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
            if job.status in [
                BackfillStatusEnum.CANCELLED,
                BackfillStatusEnum.PAUSED,
            ]:  # Use enum values
                logger.info(f"Backfill job {job_id} {job.status}")
                return

        # Mark job as completed
        job.status = BackfillStatusEnum.COMPLETED  # Use enum value
        job.end_time = datetime.now(timezone.utc)
        job.progress = 100

        logger.info(
            f"Completed backfill job {job_id}: {processed_count} emails processed",
            extra={
                "job_id": job_id,
                "user_id": user_id,
                "processed_count": processed_count,
                "total_emails": total_emails,
                "failed_emails": job.failed_emails,
                "provider": request.provider,
            },
        )

    except Exception as e:
        logger.error(f"Backfill job {job_id} failed: {e}")
        if user_id in active_backfill_jobs:
            job = active_backfill_jobs[user_id]
            job.status = BackfillStatusEnum.FAILED  # Use enum value
            job.end_time = datetime.now(timezone.utc)
            job.error_message = str(e)
