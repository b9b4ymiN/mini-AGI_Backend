# Mini-AGI Backend - Setup Guide

## ⚡ Quick Test (No Ollama Required!)

Want to test immediately without installing Ollama? Use our mock servers:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start all mock servers (one command!)
./start_all_mock.sh

# 3. In another terminal, run tests
python test_system.py
```

✅ **System is ready to use!** See [TESTING.md](TESTING.md) for detailed testing guide.

---

## 📁 Project Structure

```
mini-AGI_Backend/
├── .claude/
│   └── claude-instructions.md  ← Claude Code configuration
├── backend/                    ← Main backend implementation
│   ├── main.py                ← FastAPI app
│   └── orchestrator/
│       ├── __init__.py
│       ├── llm.py             ← Ollama integration
│       ├── agents.py          ← Agent system
│       ├── tools.py           ← Tool implementations
│       ├── core.py            ← Orchestration loop
│       └── models.py          ← Pydantic models
├── mock_ollama_server.py      ← Mock Ollama for testing
├── mock_mcp_server.py         ← Mock MCP servers for testing
├── test_system.py             ← Automated test suite
├── start_all_mock.sh          ← Start all mock servers at once
├── requirements.txt           ← Python dependencies
├── TESTING.md                 ← Comprehensive testing guide
├── SPECS.md                   ← Full implementation specification
├── CLAUDE.md                  ← AI assistant guide
└── README.md                  ← This file
```

## 🚀 Quick Start

### 1. Setup Project Structure

```bash
# Create directories
mkdir -p .claude backend/orchestrator

# Move files to correct locations
mv .claude-instructions.md .claude/instructions.md
# Keep SPECS.md at root level
```

### 2. Install Dependencies

```bash
pip install fastapi uvicorn requests pydantic
```

### 3. Start Ollama

Make sure Ollama is running with the correct model:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If needed, pull the model
ollama pull gpt-oss-20b
```

### 4. (Optional) Start MCP Servers

If you have MCP servers for filesystem and trader tools:

```bash
# Terminal 1: Filesystem MCP
# (start on port 8001)

# Terminal 2: Trader MCP  
# (start on port 8002)
```

### 5. Implement Backend

You can either:

**Option A: Use Claude Code (Recommended)**
```bash
# Claude will read .claude/instructions.md automatically
claude code "implement all backend files according to specs"
```

**Option B: Manual Implementation**
Follow the detailed specification in `SPECS.md` to create each file.

### 6. Run the Server

```bash
# From project root
uvicorn backend.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

## 🧪 Testing

### Test Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

### Test Chat Endpoint

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Hello, test message"}]
      }
    ]
  }'
```

Expected response:
```json
{
  "answer": "...",
  "events": [
    {
      "step": 1,
      "agent": "orchestrator",
      "action": "final",
      "tool": null,
      "target_agent": null,
      "thought": "..."
    }
  ]
}
```

## 🔧 Configuration

### Modify Agent Behavior

Edit `backend/orchestrator/agents.py`:
- Update system prompts
- Add new agents
- Modify agent capabilities

### Add New Tools

1. Implement function in `backend/orchestrator/tools.py`
2. Add to `TOOLS` registry
3. Update orchestrator system prompt to include new tool

### Change LLM Settings

Edit `backend/orchestrator/llm.py`:
- Model name: Change `MODEL_NAME`
- Temperature: Modify `options.temperature`
- Timeout: Add timeout parameter to request

### CORS Configuration

Edit `backend/main.py`:
```python
allow_origins=["http://localhost:3000", "http://localhost:5173"]
```

## 📝 Usage with Frontend

Your frontend should POST to `/chat` with this format:

```javascript
const response = await fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    messages: [
      {
        role: 'user',
        content: [{ type: 'text', text: userMessage }]
      }
    ]
  })
});

const { answer, events } = await response.json();
```

## 🐛 Troubleshooting

### "Connection refused" to Ollama

**Problem:** Backend can't connect to Ollama
**Solution:**
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

### "Unknown model: gpt-oss-20b"

**Problem:** Model not available
**Solution:**
```bash
# Pull the model
ollama pull gpt-oss-20b

# Or use a different model by editing llm.py
```

### Agent returns non-JSON response

**Problem:** LLM not following JSON format
**Solution:**
- Check agent system prompts are clear
- Lower temperature (currently 0.2)
- Add more explicit JSON examples in prompts
- Check fallback parsing in `run_agent()`

### MCP tools timing out

**Problem:** MCP server not responding
**Solution:**
```bash
# Verify MCP servers are running
curl http://localhost:8001/health
curl http://localhost:8002/health

# Increase timeout in tools.py
timeout=60  # instead of 30
```

### CORS errors from frontend

**Problem:** Frontend can't reach backend
**Solution:**
- Add frontend origin to `allow_origins` in main.py
- Check frontend is using correct backend URL
- Verify both servers are running

## 📚 Documentation

- **Testing Guide:** `TESTING.md` - Complete testing instructions with mock servers
- **Quick Reference:** `.claude/claude-instructions.md` - For Claude Code
- **AI Assistant Guide:** `CLAUDE.md` - Comprehensive guide for AI assistants
- **Full Specification:** `SPECS.md` - Detailed technical specification
- **API Docs:** http://localhost:8000/docs (when server running)

## 🔄 Development Workflow

1. **Make changes** to backend files
2. **Server auto-reloads** (if using `--reload`)
3. **Test** with curl or frontend
4. **Check logs** for errors
5. **Iterate**

## 🎯 Next Steps

After backend is working:

1. ✅ Test all agents (orchestrator, coder, researcher)
2. ✅ Test all tools (local + MCP)
3. ✅ Integrate with frontend
4. ✅ Add error monitoring
5. ✅ Add request logging
6. ✅ Implement rate limiting (production)
7. ✅ Add authentication (production)

---

**Happy Coding! 🚀**
