# Demo Instructions

## Common Setup

```bash
./setup-dev.sh
cp .example.env .env
```

Populate

## chat.py

Server (using repo root .env):
```bash
cd services/chat
./start.sh
```

Client:
```bash
# From repository root with unified environment
source venv/bin/activate
python services/demos/chat.py
```

## Troubleshooting

* Try `unset DB_URL_USER` to clear the env variable.

## Running with Docker and OpenTelemetry

This service can be containerized using Docker. The provided `Dockerfile.chat-service` is configured to run the service with OpenTelemetry instrumentation.

### 1. Build the Docker Image

Navigate to the root of the repository and run:

```bash
docker build -t chat-service -f Dockerfile.chat-service .
```

### 2. Run the Docker Container

Once the image is built, you can run the service using:

```bash
docker run -d -p 8002:8002 --name chat_service chat-service
```

This command will:
- Run the container in detached mode (`-d`).
- Map port 8002 of the host to port 8002 of the container (`-p 8002:8002`).
- Name the container `chat_service` for easier management.

OpenTelemetry is automatically enabled because the Docker image's entrypoint is set to `opentelemetry-instrument`. You can configure the OpenTelemetry exporter and other settings via environment variables when running the container. For example, to send traces to a local Jaeger instance:

```bash
docker run -d -p 8002:8002 \
  --name chat_service \
  -e OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317" \
  -e OTEL_SERVICE_NAME="chat-service" \
  chat-service
```

Refer to the OpenTelemetry documentation for more details on configuration options.

### 3. Using the Service

After starting the container, the chat service will be available at `http://localhost:8002`.
You can then run the demo script:
```bash
python services/demos/chat.py
```
