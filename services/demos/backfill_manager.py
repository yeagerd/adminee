#!/usr/bin/env python3
"""
Backfill Job Controller - Orchestration service for managing backfill jobs
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
import json
import uuid

from services.office.api.backfill import BackfillRequest, BackfillStatus
from services.office.core.email_crawler import EmailCrawler
from services.office.core.pubsub_publisher import PubSubPublisher

logger = logging.getLogger(__name__)

class BackfillManager:
    """Manages and orchestrates backfill jobs across multiple users and providers"""
    
    def __init__(self):
        self.active_jobs: Dict[str, BackfillStatus] = {}
        self.job_history: List[BackfillStatus] = []
        self.max_concurrent_jobs = 5
        self.job_timeout_hours = 24
        
    async def start_backfill_job(
        self,
        user_id: str,
        request: BackfillRequest,
        priority: int = 0
    ) -> str:
        """Start a new backfill job with the specified priority"""
        try:
            # Check if user already has an active job
            if self._user_has_active_job(user_id):
                raise ValueError(f"User {user_id} already has an active backfill job")
            
            # Check if we can start more jobs
            if len(self.active_jobs) >= self.max_concurrent_jobs:
                # Queue the job or raise an error
                raise ValueError("Maximum concurrent jobs reached. Please try again later.")
            
            # Create job ID
            job_id = f"backfill_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create job status
            job_status = BackfillStatus(
                job_id=job_id,
                user_id=user_id,
                status="running",
                start_time=datetime.utcnow(),
                request=request,
                progress=0.0,
                total_emails=0,
                processed_emails=0,
                failed_emails=0
            )
            
            # Store job
            self.active_jobs[job_id] = job_status
            
            # Start job execution
            asyncio.create_task(self._execute_backfill_job(job_id, user_id, request))
            
            logger.info(f"Started backfill job {job_id} for user {user_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to start backfill job for user {user_id}: {e}")
            raise
    
    async def _execute_backfill_job(
        self,
        job_id: str,
        user_id: str,
        request: BackfillRequest
    ):
        """Execute a backfill job"""
        try:
            job = self.active_jobs[job_id]
            
            # Initialize components
            email_crawler = EmailCrawler(user_id, request.provider)
            pubsub_publisher = PubSubPublisher()
            
            # Set rate limit if specified
            if request.rate_limit:
                email_crawler.set_rate_limit(request.rate_limit)
            
            # Get total email count
            total_emails = await email_crawler.get_total_email_count()
            job.total_emails = total_emails
            
            logger.info(f"Starting backfill job {job_id}: {total_emails} emails to process")
            
            # Process emails in batches
            batch_size = request.batch_size or 100
            processed_count = 0
            
            async for email_batch in email_crawler.crawl_emails(
                batch_size=batch_size,
                start_date=request.start_date,
                end_date=request.end_date,
                folders=request.folders
            ):
                # Check if job was cancelled
                if job.status in ["cancelled", "failed"]:
                    logger.info(f"Backfill job {job_id} {job.status}")
                    break
                
                # Publish emails to pubsub
                try:
                    await pubsub_publisher.publish_batch_emails(email_batch)
                    processed_count += len(email_batch)
                    job.processed_emails = processed_count
                    job.progress = (processed_count / total_emails) * 100
                    
                    logger.debug(f"Job {job_id}: Processed {processed_count}/{total_emails} emails ({job.progress:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"Failed to publish email batch in job {job_id}: {e}")
                    job.failed_emails += len(email_batch)
                
                # Check for timeout
                if datetime.utcnow() - job.start_time > timedelta(hours=self.job_timeout_hours):
                    job.status = "failed"
                    job.error_message = "Job timed out"
                    logger.warning(f"Backfill job {job_id} timed out after {self.job_timeout_hours} hours")
                    break
            
            # Mark job as completed
            if job.status == "running":
                job.status = "completed"
                job.end_time = datetime.utcnow()
                job.progress = 100.0
                logger.info(f"Completed backfill job {job_id}: {processed_count} emails processed")
            
        except Exception as e:
            logger.error(f"Backfill job {job_id} failed: {e}")
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job.status = "failed"
                job.end_time = datetime.utcnow()
                job.error_message = str(e)
        finally:
            # Move job to history
            if job_id in self.active_jobs:
                job = self.active_jobs.pop(job_id)
                self.job_history.append(job)
                
                # Clean up old history entries
                self._cleanup_old_history()
    
    def pause_job(self, job_id: str, user_id: str) -> bool:
        """Pause a running backfill job"""
        try:
            job = self._get_user_job(job_id, user_id)
            if job.status != "running":
                return False
            
            job.status = "paused"
            job.pause_time = datetime.utcnow()
            
            logger.info(f"Paused backfill job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str, user_id: str) -> bool:
        """Resume a paused backfill job"""
        try:
            job = self._get_user_job(job_id, user_id)
            if job.status != "paused":
                return False
            
            job.status = "running"
            job.resume_time = datetime.utcnow()
            
            # Restart job execution
            asyncio.create_task(self._execute_backfill_job(
                job_id, user_id, job.request
            ))
            
            logger.info(f"Resumed backfill job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            return False
    
    def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancel a backfill job"""
        try:
            job = self._get_user_job(job_id, user_id)
            if job.status in ["completed", "failed", "cancelled"]:
                return False
            
            job.status = "cancelled"
            job.end_time = datetime.utcnow()
            
            logger.info(f"Cancelled backfill job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    def get_job_status(self, job_id: str, user_id: str) -> Optional[BackfillStatus]:
        """Get the status of a specific job"""
        try:
            return self._get_user_job(job_id, user_id)
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None
    
    def list_user_jobs(self, user_id: str, status: Optional[str] = None) -> List[BackfillStatus]:
        """List all jobs for a specific user"""
        try:
            # Check active jobs
            user_jobs = [
                job for job in self.active_jobs.values()
                if job.user_id == user_id
            ]
            
            # Check history
            user_jobs.extend([
                job for job in self.job_history
                if job.user_id == user_id
            ])
            
            # Filter by status if specified
            if status:
                user_jobs = [job for job in user_jobs if job.status == status]
            
            # Sort by start time (newest first)
            user_jobs.sort(key=lambda x: x.start_time, reverse=True)
            
            return user_jobs
            
        except Exception as e:
            logger.error(f"Failed to list jobs for user {user_id}: {e}")
            return []
    
    def get_job_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of backfill jobs for a user"""
        try:
            user_jobs = self.list_user_jobs(user_id)
            
            summary = {
                "total_jobs": len(user_jobs),
                "running_jobs": len([j for j in user_jobs if j.status == "running"]),
                "paused_jobs": len([j for j in user_jobs if j.status == "paused"]),
                "completed_jobs": len([j for j in user_jobs if j.status == "completed"]),
                "failed_jobs": len([j for j in user_jobs if j.status == "failed"]),
                "cancelled_jobs": len([j for j in user_jobs if j.status == "cancelled"]),
                "total_emails_processed": sum(j.processed_emails for j in user_jobs),
                "total_emails_failed": sum(j.failed_emails for j in user_jobs),
                "average_progress": sum(j.progress for j in user_jobs) / len(user_jobs) if user_jobs else 0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get job summary for user {user_id}: {e}")
            return {}
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get a summary of all backfill jobs across the system"""
        try:
            all_jobs = list(self.active_jobs.values()) + self.job_history
            
            summary = {
                "total_jobs": len(all_jobs),
                "active_jobs": len(self.active_jobs),
                "completed_jobs": len([j for j in all_jobs if j.status == "completed"]),
                "failed_jobs": len([j for j in all_jobs if j.status == "failed"]),
                "total_emails_processed": sum(j.processed_emails for j in all_jobs),
                "total_emails_failed": sum(j.failed_emails for j in all_jobs),
                "max_concurrent_jobs": self.max_concurrent_jobs,
                "job_timeout_hours": self.job_timeout_hours
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get system summary: {e}")
            return {}
    
    def _user_has_active_job(self, user_id: str) -> bool:
        """Check if a user has an active backfill job"""
        return any(
            job.user_id == user_id and job.status in ["running", "paused"]
            for job in self.active_jobs.values()
        )
    
    def _get_user_job(self, job_id: str, user_id: str) -> BackfillStatus:
        """Get a job by ID for the specified user"""
        # Check active jobs
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            if job.user_id == user_id:
                return job
        
        # Check history
        for job in self.job_history:
            if job.job_id == job_id and job.user_id == user_id:
                return job
        
        raise ValueError(f"Job {job_id} not found for user {user_id}")
    
    def _cleanup_old_history(self, max_history_size: int = 1000):
        """Clean up old history entries to prevent memory bloat"""
        if len(self.job_history) > max_history_size:
            # Remove oldest entries
            self.job_history.sort(key=lambda x: x.start_time)
            self.job_history = self.job_history[-max_history_size:]
            logger.debug(f"Cleaned up job history, keeping {max_history_size} most recent entries")
    
    def set_max_concurrent_jobs(self, max_jobs: int):
        """Set the maximum number of concurrent backfill jobs"""
        if max_jobs > 0:
            self.max_concurrent_jobs = max_jobs
            logger.info(f"Set maximum concurrent jobs to {max_jobs}")
    
    def set_job_timeout(self, timeout_hours: int):
        """Set the job timeout in hours"""
        if timeout_hours > 0:
            self.job_timeout_hours = timeout_hours
            logger.info(f"Set job timeout to {timeout_hours} hours")
