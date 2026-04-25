#!/bin/bash

# Start SuperAgent Backend and Frontend Servers

# Resolve project root (parent of SuperAgent/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
AGENT_LOG_DIR="$LOG_DIR/agents"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
SPLITTER_PID_FILE="$LOG_DIR/log_splitter.pid"

echo "Starting SuperAgent servers..."
echo "Project root: $PROJECT_ROOT"

# Determine Python command: require .venv for consistent runtime
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
    echo "Using .venv Python: $PYTHON"
else
    echo "ERROR: .venv not found at $PROJECT_ROOT/.venv/bin/python"
    echo "Create it with: python3 -m venv .venv && source .venv/bin/activate"
    exit 1
fi

# Kill any existing processes
echo "Cleaning up existing processes..."
BACKEND_PORT_PIDS="$(lsof -ti tcp:8000 2>/dev/null)"
if [ -n "$BACKEND_PORT_PIDS" ]; then
    echo "Killing stale processes on port 8000: $BACKEND_PORT_PIDS"
    kill -9 $BACKEND_PORT_PIDS 2>/dev/null
fi

FRONTEND_PORT_PIDS="$(lsof -ti tcp:3000 2>/dev/null)"
if [ -n "$FRONTEND_PORT_PIDS" ]; then
    echo "Killing stale processes on port 3000: $FRONTEND_PORT_PIDS"
    kill -9 $FRONTEND_PORT_PIDS 2>/dev/null
fi

pkill -9 -f "uvicorn main:app" 2>/dev/null
pkill -9 -f "vite" 2>/dev/null

# Stop previous log splitter if running
if [ -f "$SPLITTER_PID_FILE" ]; then
    OLD_SPLITTER_PID="$(cat "$SPLITTER_PID_FILE" 2>/dev/null)"
    if [ -n "$OLD_SPLITTER_PID" ]; then
        kill "$OLD_SPLITTER_PID" 2>/dev/null
    fi
    rm -f "$SPLITTER_PID_FILE"
fi

# Prepare log directories/files
mkdir -p "$AGENT_LOG_DIR"
: > "$BACKEND_LOG"
: > "$FRONTEND_LOG"

# Reset per-agent logs each run
for f in \
    super_agent.log \
    discovery_agent.log \
    serviceability_agent.log \
    product_agent.log \
    offer_management_agent.log \
    order_agent.log \
    payment_agent.log \
    service_fulfillment_agent.log \
    customer_communication_agent.log \
    greeting_agent.log \
    faq_agent.log \
    infra_uvicorn.log
do
    : > "$AGENT_LOG_DIR/$f"
done

sleep 2

# Start backend
echo "Starting backend on port 8000..."
cd "$SCRIPT_DIR/server"
$PYTHON -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Split backend log into per-agent files in the background
nohup bash -c "tail -n 0 -F '$BACKEND_LOG' | awk \
    -v base='$AGENT_LOG_DIR' \
    '{\
        line = \$0;\
        if (line ~ /discovery_agent/) print line >> (base \"/discovery_agent.log\");\
        if (line ~ /serviceability_agent/) print line >> (base \"/serviceability_agent.log\");\
        if (line ~ /product_agent/) print line >> (base \"/product_agent.log\");\
        if (line ~ /offer_management_agent/) print line >> (base \"/offer_management_agent.log\");\
        if (line ~ /order_agent/) print line >> (base \"/order_agent.log\");\
        if (line ~ /payment_agent/) print line >> (base \"/payment_agent.log\");\
        if (line ~ /service_fulfillment_agent/) print line >> (base \"/service_fulfillment_agent.log\");\
        if (line ~ /customer_communication_agent/) print line >> (base \"/customer_communication_agent.log\");\
        if (line ~ /greeting_agent/) print line >> (base \"/greeting_agent.log\");\
        if (line ~ /faq_agent/) print line >> (base \"/faq_agent.log\");\
        if (line ~ /super_sales_agent|superagent\./) print line >> (base \"/super_agent.log\");\
        if (line ~ /uvicorn|Uvicorn|INFO:|ERROR:|WARNING:/) print line >> (base \"/infra_uvicorn.log\");\
        fflush();\
    }'" >/dev/null 2>&1 &
LOG_SPLITTER_PID=$!
echo "$LOG_SPLITTER_PID" > "$SPLITTER_PID_FILE"
echo "Log splitter started (PID: $LOG_SPLITTER_PID)"

# Wait for backend to initialize
sleep 8

# Check backend health
echo "Checking backend health..."
curl -s http://localhost:8000/health | $PYTHON -m json.tool

# Start frontend
echo ""
echo "Starting frontend on port 3000..."
cd "$SCRIPT_DIR/client"
echo "Installing frontend dependencies..."
npm install --silent
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

sleep 3

echo ""
echo "Both servers are running!"
echo "   Backend:  http://localhost:8000 (PID: $BACKEND_PID)"
echo "   Frontend: http://localhost:3000 (PID: $FRONTEND_PID)"
echo ""
echo "Logs:"
echo "   Backend (all):      tail -f $BACKEND_LOG"
echo "   Frontend:           tail -f $FRONTEND_LOG"
echo "   Agent logs dir:     $AGENT_LOG_DIR"
echo "   Example (product):  tail -f $AGENT_LOG_DIR/product_agent.log"
echo "   Example (service):  tail -f $AGENT_LOG_DIR/serviceability_agent.log"
echo ""
echo "To stop: pkill -9 -f 'uvicorn main:app'; pkill -9 -f 'vite'; [ -f $SPLITTER_PID_FILE ] && kill \$(cat $SPLITTER_PID_FILE)"
