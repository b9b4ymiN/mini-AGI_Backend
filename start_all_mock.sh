#!/bin/bash
# Start all mock servers for testing Mini-AGI Backend

echo "Starting all mock servers for testing..."
echo "=========================================="
echo ""

# Function to kill all background processes on exit
cleanup() {
    echo ""
    echo "Stopping all servers..."
    jobs -p | xargs -r kill 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Mock Ollama Server (port 11434)
echo "Starting Mock Ollama Server (port 11434)..."
python mock_ollama_server.py &
OLLAMA_PID=$!

# Wait a bit
sleep 1

# Start Mock Filesystem MCP Server (port 8001)
echo "Starting Mock Filesystem MCP Server (port 8001)..."
python mock_mcp_server.py filesystem &
FS_PID=$!

# Wait a bit
sleep 1

# Start Mock Trader MCP Server (port 8002)
echo "Starting Mock Trader MCP Server (port 8002)..."
python mock_mcp_server.py trader &
TRADER_PID=$!

# Wait a bit
sleep 1

# Start Mini-AGI Backend (port 8000)
echo "Starting Mini-AGI Backend (port 8000)..."
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo ""
echo "=========================================="
echo "All servers started!"
echo "=========================================="
echo "Mock Ollama:     http://127.0.0.1:11434"
echo "MCP Filesystem:  http://127.0.0.1:8001"
echo "MCP Trader:      http://127.0.0.1:8002"
echo "Backend API:     http://127.0.0.1:8000"
echo "API Docs:        http://127.0.0.1:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "=========================================="

# Wait for all background processes
wait
