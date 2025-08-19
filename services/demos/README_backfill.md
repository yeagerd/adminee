# Backfill Functionality Documentation

## Overview

The backfill functionality provides a comprehensive solution for crawling historical email data from Microsoft and Google accounts and publishing it to the message queue for downstream processing. This enables the Vespa search index to be populated with historical data while maintaining real-time updates for new emails.

## Architecture

```
Office Service → Backfill API → Email Crawler → PubSub Publisher → Office Router → Vespa Loader
```

### Components

1. **Backfill API** (`services/office/api/backfill.py`)
   - REST endpoints for managing backfill jobs
   - Job lifecycle management (start, pause, resume, cancel)
   - Progress tracking and status reporting

2. **Email Crawler** (`services/office/core/email_crawler.py`)
   - Provider-specific email crawling logic
   - Batch processing with configurable sizes
   - Rate limiting and pagination support

3. **PubSub Publisher** (`services/office/core/pubsub_publisher.py`)
   - Message publishing to PubSub topics
   - Batch publishing capabilities
   - Error handling and retry logic

4. **Backfill Manager** (`services/demos/backfill_manager.py`)
   - Job orchestration and management
   - Concurrent job handling
   - Job history and cleanup

## Usage

### Starting a Backfill Job

```python
from services.office.models.backfill import BackfillRequest
from services.office.api.backfill import start_backfill

# Create backfill request
request = BackfillRequest(
    provider="microsoft",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    batch_size=100,
    rate_limit=50,
    folders=["inbox", "sent"],
    include_attachments=True
)

# Start backfill job
response = await start_backfill(request)
job_id = response.job_id
```

### Monitoring Job Progress

```python
# Get job status
status = await get_backfill_status(job_id)

print(f"Progress: {status.progress:.1f}%")
print(f"Processed: {status.processed_emails}/{status.total_emails}")
print(f"Status: {status.status}")
```

### Job Management

```python
# Pause a running job
await pause_backfill_job(job_id)

# Resume a paused job
await resume_backfill_job(job_id)

# Cancel a job
await cancel_backfill_job(job_id)
```

## Configuration

### Environment Variables

```bash
# PubSub Configuration
PUBSUB_EMULATOR_HOST=localhost:8085
PUBSUB_PROJECT_ID=briefly-dev

# Office Service Configuration
OFFICE_SERVICE_PORT=8000
OFFICE_SERVICE_HOST=0.0.0.0

# Backfill Configuration
MAX_CONCURRENT_JOBS=5
JOB_TIMEOUT_HOURS=24
DEFAULT_BATCH_SIZE=100
DEFAULT_RATE_LIMIT=100
```

### Rate Limiting

The backfill system supports configurable rate limiting to prevent overwhelming email provider APIs:

- **Microsoft Graph API**: Default 100 requests per second
- **Gmail API**: Default 100 requests per second
- **Configurable**: Can be set per job via `rate_limit` parameter

### Batch Processing

Emails are processed in configurable batches:

- **Default batch size**: 100 emails
- **Configurable range**: 1-1000 emails per batch
- **Memory efficient**: Processes one batch at a time

## API Endpoints

### POST /api/backfill/start

Start a new backfill job.

**Request Body:**
```json
{
  "provider": "microsoft",
  "start_date": "2023-01-01T00:00:00Z",
  "end_date": "2023-12-31T23:59:59Z",
  "folders": ["inbox", "sent"],
  "batch_size": 100,
  "rate_limit": 50,
  "include_attachments": true,
  "include_deleted": false
}
```

**Response:**
```json
{
  "job_id": "backfill_user123_20231201_143022_abc12345",
  "status": "started",
  "message": "Backfill job started successfully"
}
```

### GET /api/backfill/status/{job_id}

Get the status of a specific backfill job.

**Response:**
```json
{
  "job_id": "backfill_user123_20231201_143022_abc12345",
  "user_id": "user123",
  "status": "running",
  "start_time": "2023-12-01T14:30:22Z",
  "progress": 45.5,
  "total_emails": 1000,
  "processed_emails": 455,
  "failed_emails": 2
}
```

### GET /api/backfill/status

List all backfill jobs for the current user.

**Query Parameters:**
- `status`: Filter by job status (running, paused, completed, failed, cancelled)

### POST /api/backfill/{job_id}/pause

Pause a running backfill job.

### POST /api/backfill/{job_id}/resume

Resume a paused backfill job.

### DELETE /api/backfill/{job_id}

Cancel a backfill job.

## Error Handling

### Common Error Scenarios

1. **Rate Limit Exceeded**
   - Automatic retry with exponential backoff
   - Configurable retry attempts

2. **API Authentication Failures**
   - Job marked as failed
   - Error message logged

3. **Network Timeouts**
   - Configurable timeout settings
   - Automatic retry logic

4. **Provider API Limits**
   - Respects provider-specific quotas
   - Automatic rate limiting

### Error Recovery

- **Automatic retries**: Failed batches are retried automatically
- **Resume capability**: Jobs can be resumed from where they left off
- **Progress persistence**: Job progress is maintained across restarts

## Monitoring and Observability

### Metrics

- **Job progress**: Real-time progress tracking
- **Processing rate**: Emails processed per second
- **Error rates**: Failed emails and error counts
- **Job duration**: Start to completion time

### Logging

- **Structured logging**: JSON-formatted log entries
- **Log levels**: DEBUG, INFO, WARNING, ERROR
- **Context information**: Job ID, user ID, provider

### Health Checks

- **Service health**: `/health` endpoint
- **Job status**: Real-time job status monitoring
- **System metrics**: Overall system performance

## Security Considerations

### User Isolation

- **User-specific jobs**: Jobs are isolated by user ID
- **Authentication required**: All endpoints require valid authentication
- **Authorization checks**: Users can only access their own jobs

### Data Privacy

- **No data storage**: Email content is not stored, only published
- **Temporary processing**: Data exists only during processing
- **Audit logging**: All operations are logged for compliance

## Performance Optimization

### Concurrent Processing

- **Multiple jobs**: Support for multiple concurrent backfill jobs
- **Configurable limits**: Adjustable concurrent job limits
- **Resource management**: Efficient memory and CPU usage

### Batch Optimization

- **Optimal batch sizes**: Configurable batch sizes for different scenarios
- **Memory efficiency**: Processes one batch at a time
- **Network optimization**: Minimizes API calls

## Troubleshooting

### Common Issues

1. **Job stuck in running state**
   - Check provider API status
   - Verify authentication tokens
   - Review error logs

2. **Slow processing**
   - Adjust batch size
   - Check rate limiting settings
   - Monitor network performance

3. **High failure rates**
   - Review error messages
   - Check provider API quotas
   - Verify data format compatibility

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export LOG_LEVEL=DEBUG
```

## Future Enhancements

### Planned Features

1. **Incremental backfill**: Only process new/changed emails
2. **Scheduled backfills**: Automated periodic backfill jobs
3. **Priority queuing**: Support for job priority levels
4. **Distributed processing**: Multi-instance job processing
5. **Real-time monitoring**: WebSocket-based progress updates

### Integration Points

1. **Webhook support**: Real-time email updates
2. **Analytics integration**: Processing metrics and insights
3. **Alerting system**: Job failure notifications
4. **Dashboard**: Web-based job management interface
