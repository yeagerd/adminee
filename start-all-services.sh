#!/bin/bash

# Start All Services Script
# This script starts the chat, user, and office services using their individual start.sh scripts

set -e

# Ensure we're in the repo root (where this script is located)
cd "$(dirname "$0")"

echo "🚀 Starting all Briefly services..."
echo "📁 Working directory: $(pwd)"
echo ""

echo "🔧 Starting User Service on port 8001..."
./services/user/start.sh &
USER_PID=$!

echo "💬 Starting Chat Service on port 8002..."
./services/chat/start.sh &
CHAT_PID=$!

echo "🏢 Starting Office Service on port 8003..."
./services/office/start.sh &
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