#!/bin/bash

# Start All Services Script
# This script starts the chat, user, and office services with proper environment variables

set -e

echo "🚀 Starting all Briefly services..."

# Set environment variables
export API_FRONTEND_USER_KEY=test-frontend-api-key
export DB_URL_CHAT=sqlite:///$(pwd)/services/chat/chat.db
export DB_URL_USER_MANAGEMENT=sqlite:///$(pwd)/services/user/user_service.db
export DB_URL_OFFICE=sqlite:///$(pwd)/services/office/office_service.db
export CLERK_SECRET_KEY=test-clerk-secret
export TOKEN_ENCRYPTION_SALT=dGVzdC1zYWx0LTE2Ynl0ZQ==
export REDIS_URL=redis://localhost:6379

# Activate virtual environment
source venv/bin/activate

echo "📊 Environment variables set:"
echo "  API_FRONTEND_USER_KEY: ${API_FRONTEND_USER_KEY}"
echo "  DB_URL_CHAT: ${DB_URL_CHAT}"
echo "  DB_URL_USER_MANAGEMENT: ${DB_URL_USER_MANAGEMENT}"
echo "  DB_URL_OFFICE: ${DB_URL_OFFICE}"
echo "  REDIS_URL: ${REDIS_URL}"
echo ""

echo "🔧 Starting User Service on port 8001..."
python -m uvicorn services.user.main:app --port 8001 --host 0.0.0.0 &
USER_PID=$!

echo "💬 Starting Chat Service on port 8002..."
python -m uvicorn services.chat.main:app --port 8002 --host 0.0.0.0 &
CHAT_PID=$!

echo "🏢 Starting Office Service on port 8003..."
python -m uvicorn services.office.app.main:app --port 8003 --host 0.0.0.0 &
OFFICE_PID=$!

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

echo ""
echo "🔍 Checking service health..."
echo "User Service (8001):"
curl -s http://localhost:8001/health | jq . || echo "❌ User service not responding"

echo ""
echo "Chat Service (8002):"
curl -s http://localhost:8002/health | jq . || echo "❌ Chat service not responding"

echo ""
echo "Office Service (8003):"
curl -s http://localhost:8003/health/ | jq . || echo "❌ Office service not responding"

echo ""
echo "✅ All services started!"
echo "Process IDs:"
echo "  User Service: ${USER_PID}"
echo "  Chat Service: ${CHAT_PID}"
echo "  Office Service: ${OFFICE_PID}"
echo ""
echo "To stop all services:"
echo "  kill ${USER_PID} ${CHAT_PID} ${OFFICE_PID}"
echo ""
echo "🎯 Ready to run demo:"
echo "  cd services/demos && python chat.py" 