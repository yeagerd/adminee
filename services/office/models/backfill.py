#!/usr/bin/env python3
"""
Data models for backfill functionality
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class BackfillStatusEnum(str, Enum):
    """Status of a backfill job"""
    STARTED = "started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProviderEnum(str, Enum):
    """Email provider types"""
    MICROSOFT = "microsoft"
    GOOGLE = "google"

class BackfillRequest(BaseModel):
    """Request to start a backfill job"""
    provider: ProviderEnum = Field(..., description="Email provider to backfill")
    start_date: Optional[datetime] = Field(None, description="Start date for email range")
    end_date: Optional[datetime] = Field(None, description="End date for email range")
    folders: Optional[List[str]] = Field(None, description="Specific folders to backfill")
    batch_size: Optional[int] = Field(100, ge=1, le=1000, description="Batch size for processing")
    rate_limit: Optional[int] = Field(100, ge=1, le=1000, description="Emails per second limit")
    include_attachments: bool = Field(False, description="Whether to include attachment metadata")
    include_deleted: bool = Field(False, description="Whether to include deleted emails")
    
    class Config:
        extra = "forbid"

class BackfillResponse(BaseModel):
    """Response from starting a backfill job"""
    job_id: str = Field(..., description="Unique identifier for the backfill job")
    status: BackfillStatusEnum = Field(..., description="Status of the job")
    message: str = Field(..., description="Human-readable message")
    
    class Config:
        extra = "forbid"

class BackfillStatus(BaseModel):
    """Current status of a backfill job"""
    job_id: str = Field(..., description="Unique identifier for the backfill job")
    user_id: str = Field(..., description="User who owns this job")
    status: BackfillStatusEnum = Field(..., description="Current status of the job")
    start_time: datetime = Field(..., description="When the job started")
    end_time: Optional[datetime] = Field(None, description="When the job ended")
    pause_time: Optional[datetime] = Field(None, description="When the job was paused")
    resume_time: Optional[datetime] = Field(None, description="When the job was resumed")
    request: BackfillRequest = Field(..., description="Original backfill request")
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Progress percentage")
    total_emails: int = Field(0, ge=0, description="Total emails to process")
    processed_emails: int = Field(0, ge=0, description="Number of emails processed")
    failed_emails: int = Field(0, ge=0, description="Number of emails that failed")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    
    class Config:
        extra = "forbid"

class BackfillJobSummary(BaseModel):
    """Summary of backfill job statistics"""
    total_jobs: int = Field(..., description="Total number of backfill jobs")
    running_jobs: int = Field(..., description="Number of currently running jobs")
    completed_jobs: int = Field(..., description="Number of completed jobs")
    failed_jobs: int = Field(..., description="Number of failed jobs")
    total_emails_processed: int = Field(..., description="Total emails processed across all jobs")
    total_emails_failed: int = Field(..., description="Total emails that failed across all jobs")
    
    class Config:
        extra = "forbid"

class EmailBatch(BaseModel):
    """Batch of emails for processing"""
    emails: List[Dict[str, Any]] = Field(..., description="List of email data")
    batch_number: int = Field(..., description="Sequential batch number")
    total_batches: int = Field(..., description="Total number of batches")
    is_last_batch: bool = Field(..., description="Whether this is the final batch")
    
    class Config:
        extra = "forbid"
