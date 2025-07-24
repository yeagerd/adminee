# Email Sync Service

This service handles email webhook notifications (Gmail, Microsoft) and publishes them to pubsub topics for downstream processing.

## Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in required values.
3. Run the Flask app:
   ```
   flask run --host=0.0.0.0 --port=8080
   ```

## Environment Variables
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `PUBSUB_EMULATOR_HOST`: Host for local pubsub emulator (e.g., localhost:8085)
- `GMAIL_WEBHOOK_SECRET`: Secret for Gmail webhook validation

## Message Schemas
See `schemas.py` for pubsub message formats. 

## Running Tests

Run all tests with:
```
pytest
``` 