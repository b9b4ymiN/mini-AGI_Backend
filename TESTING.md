# Testing Guide - Mini-AGI Backend

## Quick Start Testing (No Ollama Required!)

The easiest way to test the system is using the provided mock servers.

### Option 1: One-Command Start (Recommended)

```bash
# Start all mock servers at once
./start_all_mock.sh
```

This starts:
- Mock Ollama Server (port 11434)
- Mock Filesystem MCP Server (port 8001)
- Mock Trader MCP Server (port 8002)
- Mini-AGI Backend (port 8000)

Then in another terminal:

```bash
# Run the test suite
python test_system.py
```

### Option 2: Manual Server Start

**Terminal 1 - Mock Ollama:**
```bash
python mock_ollama_server.py
```

**Terminal 2 - Mock Filesystem MCP:**
```bash
python mock_mcp_server.py filesystem
```

**Terminal 3 - Mock Trader MCP:**
```bash
python mock_mcp_server.py trader
```

**Terminal 4 - Backend:**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 5 - Run Tests:**
```bash
python test_system.py
```

---

## Manual Testing

### 1. Health Check

```bash
curl http://127.0.0.1:8000/health
```

Expected output:
```json
{"status":"ok"}
```

### 2. Simple Chat Test

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Hello!"}]
      }
    ]
  }'
```

Expected output:
```json
{
  "answer": "Mock response: I received your message...",
  "events": [
    {
      "step": 1,
      "agent": "orchestrator",
      "action": "final",
      "tool": null,
      "target_agent": null,
      "thought": "This is a simple query, I can answer directly"
    }
  ]
}
```

### 3. Test Tool Execution

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Calculate the sum of 1 to 10"}]
      }
    ]
  }'
```

This should trigger the `run_python` tool.

### 4. Test Agent Delegation

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Write a Python function to calculate fibonacci"}]
      }
    ]
  }'
```

This should delegate to the `coder` agent.

### 5. Test MCP Filesystem Tool

```bash
curl -X POST http://127.0.0.1:8001/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "list_files",
    "args": {"path": "."}
  }'
```

### 6. Test MCP Trader Tool

```bash
curl -X POST http://127.0.0.1:8002/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_price",
    "args": {"symbol": "BTC"}
  }'
```

---

## Testing with Real Ollama

If you have Ollama installed and want to test with real LLM:

### 1. Install Ollama

Visit: https://ollama.ai

### 2. Pull the Model

```bash
ollama pull mistral  # or any other model
```

### 3. Update LLM Configuration

Edit `backend/orchestrator/llm.py`:

```python
MODEL_NAME = "mistral"  # Change from "gpt-oss-20b"
```

### 4. Start Ollama

```bash
ollama serve
```

### 5. Start Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

### 6. Test

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Explain quantum computing in simple terms"}]
      }
    ]
  }'
```

---

## Understanding Mock Servers

### Mock Ollama Server

The mock Ollama server (`mock_ollama_server.py`) simulates LLM responses by:

- Parsing user messages for keywords
- Returning appropriate JSON responses that follow the agent protocol
- Supporting actions: `use_tool`, `delegate`, `final`

**Example behaviors:**
- "calculate" → uses `run_python` tool
- "write code" → delegates to `coder` agent
- "read file" → uses `read_file` tool
- default → provides direct `final` answer

### Mock MCP Servers

**Filesystem Mock (`mock_mcp_server.py filesystem`):**
- `list_files`: Lists files in a directory
- `read_file`: Reads file contents (limited to 1000 chars)
- `write_file`: Writes content to a file

**Trader Mock (`mock_mcp_server.py trader`):**
- `backtest`: Returns mock backtest results
- `get_price`: Returns mock cryptocurrency prices
- `place_order`: Simulates order placement

---

## Troubleshooting

### Port Already in Use

If you get "Address already in use" errors:

```bash
# Kill all Python processes
pkill -f python

# Or kill specific ports
lsof -ti:8000 | xargs kill
lsof -ti:11434 | xargs kill
lsof -ti:8001 | xargs kill
lsof -ti:8002 | xargs kill
```

### Import Errors

Make sure you're in the project root directory:

```bash
cd /path/to/mini-AGI_Backend
python test_system.py
```

### Dependencies Missing

```bash
pip install -r requirements.txt
```

### Mock Server Not Responding

Check if the server is actually running:

```bash
# Check Ollama
curl http://127.0.0.1:11434/api/tags

# Check Filesystem MCP
curl http://127.0.0.1:8001/health

# Check Trader MCP
curl http://127.0.0.1:8002/health

# Check Backend
curl http://127.0.0.1:8000/health
```

---

## Interactive Testing with Swagger UI

1. Start the backend server
2. Open your browser to: http://127.0.0.1:8000/docs
3. Try the `/chat` endpoint interactively

---

## Expected Test Results

When running `python test_system.py`, you should see:

```
============================================================
Mini-AGI Backend System Test
============================================================

=== Checking Ollama ===
✅ Ollama is running
   Available models: ['gpt-oss-20b']

=== Checking MCP Servers ===
✅ Filesystem MCP server is running
✅ Trader MCP server is running

============================================================
Dependency Status:
  Ollama: ✅ Running
  MCP Filesystem: ✅ Running
  MCP Trader: ✅ Running

=== Testing Health Endpoint ===
✅ Health endpoint working

=== Testing Simple Chat ===
✅ Chat endpoint returned valid response
   Answer: Mock response: I received your message...
   Events: 1 steps

=== Testing Tool Execution ===
✅ Tool execution detected in events
   Tool used: run_python

============================================================
Test Summary:
============================================================
Health Check         ✅ PASSED
Simple Chat          ✅ PASSED
Tool Execution       ✅ PASSED

Total: 3/3 tests passed

🎉 All tests passed! System is working correctly.
```

---

## Next Steps

Once basic testing is complete:

1. **Frontend Integration**: Connect a frontend using the assistant-ui format
2. **Custom Tools**: Add your own tools to `backend/orchestrator/tools.py`
3. **Custom Agents**: Add specialized agents to `backend/orchestrator/agents.py`
4. **Real MCP Servers**: Replace mocks with actual MCP server implementations
5. **Production Setup**: Add authentication, rate limiting, and proper error handling

---

## Production Checklist

Before deploying to production:

- [ ] Replace mock Ollama with real Ollama or OpenAI/Anthropic API
- [ ] Replace mock MCP servers with real implementations
- [ ] Add authentication (JWT, API keys, etc.)
- [ ] Add rate limiting
- [ ] Add proper logging
- [ ] Add monitoring and alerting
- [ ] Review and secure the `run_python` tool
- [ ] Set up HTTPS/TLS
- [ ] Configure proper CORS for your frontend domain
- [ ] Add database for conversation history
- [ ] Implement proper error handling and retries
- [ ] Add input validation and sanitization
- [ ] Set up CI/CD pipeline
- [ ] Write comprehensive tests
- [ ] Document API endpoints

---

**Happy Testing! 🚀**
