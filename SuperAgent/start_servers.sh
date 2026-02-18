#!/bin/bash

# Start SuperAgent Backend and Frontend Servers

echo "🚀 Starting SuperAgent servers..."

# Kill any existing processes
echo "Cleaning up existing processes..."
pkill -9 -f "uvicorn main:app" 2>/dev/null
pkill -9 -f "vite" 2>/dev/null
sleep 2

# Start backend
echo "Starting backend on port 8000..."
cd /Users/rbarat738@cable.comcast.com/Documents/GitHub/ConversationalSalesAgent/SuperAgent/server
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Wait for backend to initialize
sleep 8

# Check backend health
echo "Checking backend health..."
curl -s http://localhost:8000/health | python3 -m json.tool

# Start frontend
echo ""
echo "Starting frontend on port 3000..."
cd /Users/rbarat738@cable.comcast.com/Documents/GitHub/ConversationalSalesAgent/SuperAgent/client
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

sleep 3

echo ""
echo "✅ Both servers are running!"
echo "   Backend:  http://localhost:8000 (PID: $BACKEND_PID)"
echo "   Frontend: http://localhost:3000 (PID: $FRONTEND_PID)"
echo ""
echo "Logs:"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Frontend: tail -f /tmp/frontend.log"
echo ""
echo "To stop: pkill -9 -f 'uvicorn main:app'; pkill -9 -f 'vite'"
