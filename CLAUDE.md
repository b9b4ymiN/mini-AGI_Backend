# CLAUDE.md - AI Assistant Guide for Mini-AGI Backend

## Project Overview

**Project Name:** Mini-AGI Backend
**Repository:** b9b4ymiN/mini-AGI_Backend
**Current State:** Specification Phase (No Implementation Yet)
**Purpose:** Python backend orchestrator that coordinates AI agents using Ollama LLM and MCP (Model Context Protocol) tools, exposing a FastAPI endpoint for chat interactions.

### Project Status

- ✅ Project specifications complete (SPECS.md)
- ✅ Setup instructions complete (README.md)
- ✅ Claude Code instructions complete (.claude/claude-instructions.md)
- ⏳ **Backend implementation pending** - Ready for development
- ⏳ Dependencies not installed yet
- ⏳ No code files exist yet

---

## Architecture Overview

### Core Concept

This is an **agent orchestration system** that:
1. Receives user queries via REST API
2. Routes them through an orchestrator agent
3. Delegates to specialist agents (coder, researcher) as needed
4. Executes tools (file operations, code execution, MCP integrations)
5. Returns structured responses with execution traces

### Tech Stack

| Component | Technology | Details |
|-----------|-----------|---------|
| **Language** | Python 3.10+ | Full type hints required |
| **Web Framework** | FastAPI | REST API on port 8000 |
| **ASGI Server** | Uvicorn | Development server with hot reload |
| **Validation** | Pydantic | Request/response models |
| **HTTP Client** | requests | For Ollama and MCP calls |
| **LLM** | Ollama | Local model: `gpt-oss-20b` @ localhost:11434 |
| **Tools** | MCP Servers | Filesystem (8001), Trader (8002) |

### Agent System

**Three Agents:**

1. **Orchestrator** (entry point)
   - Main coordinator for all requests
   - Routes to specialist agents
   - Manages tool execution
   - Always starts here

2. **Coder** (specialist)
   - Python/Node.js/Next.js expert
   - Trading automation specialist
   - Code refactoring and debugging

3. **Researcher** (specialist)
   - Information analysis
   - Document summarization
   - Data structuring

**Agent Protocol:**
- All agents respond in strict JSON format
- Actions: `use_tool` | `delegate` | `final`
- Max 10 orchestration steps per request
- Context accumulates across steps

---

## Repository Structure

### Current Structure

```
mini-AGI_Backend/
├── .claude/
│   └── claude-instructions.md    # Claude Code configuration
├── .git/                          # Git repository
├── README.md                      # Setup and usage guide
├── SPECS.md                       # Detailed implementation spec
└── CLAUDE.md                      # This file
```

### Target Structure (To Be Implemented)

```
mini-AGI_Backend/
├── .claude/
│   └── claude-instructions.md
├── backend/                       # ← TO CREATE
│   ├── main.py                    # FastAPI app with /chat endpoint
│   └── orchestrator/
│       ├── __init__.py           # Package marker
│       ├── llm.py                # Ollama client (call_ollama)
│       ├── agents.py             # AGENTS dict + run_agent()
│       ├── tools.py              # TOOLS registry + implementations
│       ├── core.py               # orchestrate() main loop
│       └── models.py             # Pydantic models
├── requirements.txt               # ← TO CREATE: Python dependencies
├── README.md
├── SPECS.md
└── CLAUDE.md
```

---

## Development Workflow for AI Assistants

### Phase 1: Initial Setup

**When to do this:** First time implementing the backend

**Steps:**

1. **Create directory structure:**
   ```bash
   mkdir -p backend/orchestrator
   touch backend/__init__.py
   touch backend/orchestrator/__init__.py
   ```

2. **Create requirements.txt:**
   ```
   fastapi
   uvicorn
   requests
   pydantic
   ```

3. **Verify Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

### Phase 2: Implementation Order

**Recommended order for creating files:**

1. **backend/orchestrator/models.py** - Define data models first
   - `OrchestratorEvent`
   - `ChatRequest`
   - `ChatResponse`

2. **backend/orchestrator/llm.py** - LLM integration
   - `call_ollama(messages, model)` function
   - Ollama URL: `http://localhost:11434/api/chat`
   - Model: `gpt-oss-20b`
   - Temperature: 0.2

3. **backend/orchestrator/tools.py** - Tool implementations
   - Local tools: `read_file`, `write_file`, `run_python`
   - MCP bridges: `mcp_filesystem`, `mcp_trader`
   - `TOOLS` registry dictionary

4. **backend/orchestrator/agents.py** - Agent definitions
   - `AGENTS` registry with system prompts
   - `run_agent(agent_name, user_content, extra_context)` function
   - JSON parsing with fallbacks

5. **backend/orchestrator/core.py** - Main orchestration loop
   - `orchestrate(user_input, max_steps=10)` function
   - Step-by-step execution
   - Context accumulation

6. **backend/main.py** - FastAPI application
   - `/chat` POST endpoint
   - `/health` GET endpoint
   - CORS configuration

### Phase 3: Testing

**Steps after implementation:**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start server:**
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

3. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

4. **Test chat endpoint:**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{
       "messages": [
         {
           "role": "user",
           "content": [{"type": "text", "text": "Hello"}]
         }
       ]
     }'
   ```

---

## Key Conventions and Patterns

### Code Style

**Type Hints (Required):**
```python
# GOOD
def call_ollama(messages: List[Dict[str, str]], model: str = MODEL_NAME) -> str:
    pass

# BAD - no type hints
def call_ollama(messages, model=MODEL_NAME):
    pass
```

**Registry Pattern:**
```python
# Agents and tools use dict registries for easy extension
AGENTS: Dict[str, Dict[str, str]] = {
    "orchestrator": {"system": "..."},
    "coder": {"system": "..."},
}

TOOLS: Dict[str, Callable[..., str]] = {
    "read_file": lambda **kw: tool_read_file(kw.get("path", "")),
}
```

**Error Handling:**
```python
# Tools return error strings, not exceptions
def tool_read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR(read_file): {e}"
```

### Agent Response Schema

**Strict JSON format required:**

```json
{
  "thought": "Brief reasoning in English",
  "action": "use_tool | delegate | final",
  "tool": "tool_name or null",
  "target_agent": "agent_name or null",
  "args": {},
  "answer": "Final answer for user (only if action=final)"
}
```

### System Prompts

**Must be explicit about JSON:**
```python
"You ALWAYS respond ONLY in JSON with this schema: {...}"
```

**Must list available tools and agents:**
```python
"""
Available tools:
- read_file(path: str) - Read file contents
- write_file(path: str, content: str) - Write to file
...

Available agents:
- coder: Python/Node.js/trading expert
- researcher: Analysis specialist
"""
```

---

## Critical Implementation Details

### 1. LLM Integration (llm.py)

**Ollama Request Format:**
```python
payload = {
    "model": "gpt-oss-20b",
    "messages": messages,  # List[Dict[str, str]]
    "stream": False,
    "options": {
        "temperature": 0.2,
    },
}
```

**Response Parsing:**
```python
# Ollama returns: {"message": {"role": "assistant", "content": "..."}}
data = response.json()
return data["message"]["content"]
```

### 2. JSON Parsing with Fallbacks (agents.py)

**Robust parsing strategy:**
```python
try:
    data = json.loads(raw_response)
except json.JSONDecodeError:
    # Try to extract JSON from markdown code blocks
    start = raw_response.find("{")
    end = raw_response.rfind("}") + 1
    if start != -1 and end > start:
        data = json.loads(raw_response[start:end])
    else:
        # Ultimate fallback
        data = {
            "thought": "JSON parsing failed",
            "action": "final",
            "answer": raw_response,
        }
```

### 3. Orchestration Loop (core.py)

**State tracking:**
```python
context_log: List[str] = []        # Accumulates step history
events: List[OrchestratorEvent] = [] # Records each step
current_agent: str = "orchestrator" # Currently active agent
current_query: str = user_input    # Current prompt
```

**Action handling:**
- `action="final"` → Return answer immediately
- `action="use_tool"` → Execute tool, stay with current agent
- `action="delegate"` → Switch to target_agent
- Invalid action → Reset to orchestrator with error message

### 4. Tool System (tools.py)

**Local tools are simple functions:**
```python
def tool_read_file(path: str) -> str:
    # Returns content or error string

def tool_write_file(path: str, content: str) -> str:
    # Returns success message or error string
```

**MCP tools use HTTP bridge:**
```python
def call_mcp_tool(server_url: str, tool_name: str, args: Dict[str, Any]) -> str:
    resp = requests.post(
        server_url.rstrip("/") + "/invoke",
        json={"tool": tool_name, "args": args},
        timeout=30,
    )
    return resp.text
```

### 5. FastAPI Endpoint (main.py)

**Message extraction:**
```python
# Extract latest user message from assistant-ui format
for msg in reversed(req.messages):
    if msg.get("role") == "user":
        content = msg.get("content", [])
        if content and isinstance(content, list):
            first_item = content[0]
            if isinstance(first_item, dict) and first_item.get("type") == "text":
                last_user_msg = first_item.get("text", "")
                break
```

---

## Common Tasks for AI Assistants

### Task: Implement the complete backend from scratch

**Instructions:**
1. Read SPECS.md for detailed implementation requirements
2. Follow the implementation order in Phase 2
3. Create each file with proper type hints
4. Test each component before moving to next
5. Verify Ollama connection works
6. Test final integration with curl

**Time estimate:** ~30-45 minutes for AI assistant

### Task: Add a new tool

**Steps:**
1. Implement function in `backend/orchestrator/tools.py`:
   ```python
   def tool_my_new_tool(arg1: str, arg2: int) -> str:
       try:
           # Implementation
           return "SUCCESS: ..."
       except Exception as e:
           return f"ERROR(my_new_tool): {e}"
   ```

2. Add to TOOLS registry:
   ```python
   TOOLS["my_new_tool"] = lambda **kw: tool_my_new_tool(
       kw.get("arg1", ""),
       kw.get("arg2", 0)
   )
   ```

3. Update orchestrator system prompt in `agents.py`:
   ```python
   """
   Available tools:
   - my_new_tool(arg1: str, arg2: int) - Description
   """
   ```

### Task: Add a new agent

**Steps:**
1. Add to AGENTS dict in `backend/orchestrator/agents.py`:
   ```python
   AGENTS["my_agent"] = {
       "system": """You are MyAgent, an expert in X.

       You help with Y and Z.
       Always respond in JSON: {thought, action, tool, target_agent, args, answer}.

       Available tools:
       - tool1, tool2, ...
       """
   }
   ```

2. Update orchestrator system prompt to include new agent in delegation list

3. Test with a query that requires the new agent

### Task: Debug a failing request

**Diagnostic steps:**

1. **Check Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Check MCP servers (if using):**
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   ```

3. **Enable debug logging:**
   ```bash
   uvicorn backend.main:app --reload --port 8000 --log-level debug
   ```

4. **Examine orchestration events:**
   - Look at the `events` array in response
   - Check which agent/tool failed
   - Review `thought` field for agent reasoning

5. **Test Ollama directly:**
   ```bash
   curl -X POST http://localhost:11434/api/chat \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-oss-20b",
       "messages": [{"role": "user", "content": "test"}],
       "stream": false
     }'
   ```

---

## Important Constraints and Gotchas

### Security Warnings

⚠️ **run_python tool is UNSAFE:**
- Uses Python `exec()` without sandboxing
- Only for local development
- NEVER use in production with untrusted input
- Consider removing or securing before deployment

⚠️ **No authentication:**
- API is completely open
- CORS allows localhost:3000 only
- Add auth for production use

### Performance Considerations

- **Max 10 orchestration steps** - prevents infinite loops
- **Temperature 0.2** - low for consistency, may be too deterministic
- **No streaming** - entire response waits for completion
- **Synchronous tools** - blocking I/O, consider async for production

### LLM Limitations

- **JSON compliance** - Model may not always follow JSON format strictly
  - Solution: Fallback parsing implemented in run_agent()
- **Context limits** - Long conversations may exceed model context
  - Solution: Only send user message + context log (not full history)
- **Ollama dependency** - Requires local Ollama server
  - Alternative: Could swap to OpenAI/Anthropic API

---

## Git Workflow

### Branch Strategy

**Active branch:** `claude/claude-md-mi0ayxvf17n52854-015FZkkYHb2ZPF3GUmbSVvHg`

All development should happen on this branch.

### Commit Guidelines

**When implementing backend:**
```bash
# After creating file structure
git add backend/ requirements.txt
git commit -m "feat: implement backend file structure and dependencies"

# After implementing models
git add backend/orchestrator/models.py
git commit -m "feat: implement Pydantic models for API and events"

# After implementing LLM integration
git add backend/orchestrator/llm.py
git commit -m "feat: implement Ollama LLM integration"

# After implementing tools
git add backend/orchestrator/tools.py
git commit -m "feat: implement local and MCP tool integrations"

# After implementing agents
git add backend/orchestrator/agents.py
git commit -m "feat: implement agent system with orchestrator, coder, and researcher"

# After implementing core orchestration
git add backend/orchestrator/core.py
git commit -m "feat: implement main orchestration loop"

# After implementing API
git add backend/main.py
git commit -m "feat: implement FastAPI endpoints for chat and health"

# Final commit after testing
git add .
git commit -m "feat: complete backend implementation with tests"
```

### Push Strategy

```bash
# Push to feature branch
git push -u origin claude/claude-md-mi0ayxvf17n52854-015FZkkYHb2ZPF3GUmbSVvHg
```

**Retry logic for network issues:**
- Retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s)
- Only retry on network errors, not on authentication failures

---

## Documentation References

### Primary Documentation

1. **SPECS.md** - Detailed technical specification
   - Complete implementation requirements
   - Code examples for each component
   - API request/response formats
   - Deployment instructions

2. **README.md** - Setup and usage guide
   - Quick start instructions
   - Testing procedures
   - Troubleshooting common issues
   - Frontend integration examples

3. **.claude/claude-instructions.md** - Claude Code specific guidance
   - Project overview
   - Core architecture
   - Key principles
   - Coding preferences
   - Quick reference

4. **CLAUDE.md** (this file) - AI assistant comprehensive guide
   - Project status and overview
   - Development workflows
   - Implementation patterns
   - Common tasks
   - Troubleshooting

### External Documentation

- **FastAPI:** https://fastapi.tiangolo.com/
- **Pydantic:** https://docs.pydantic.dev/
- **Ollama API:** https://github.com/ollama/ollama/blob/main/docs/api.md
- **MCP Spec:** (Assumed available from MCP server providers)

---

## Testing Checklist

### Pre-Implementation Tests

- [ ] Ollama is running and accessible
- [ ] Model `gpt-oss-20b` is available
- [ ] MCP servers are running (if required)
- [ ] Python 3.10+ is installed

### Post-Implementation Tests

**Basic functionality:**
- [ ] Health endpoint returns `{"status": "ok"}`
- [ ] Chat endpoint accepts requests
- [ ] Orchestrator agent executes successfully
- [ ] Tool execution works (read_file, write_file, run_python)
- [ ] Agent delegation works (orchestrator → coder/researcher)
- [ ] Final answers are returned correctly

**Edge cases:**
- [ ] Invalid tool name handled gracefully
- [ ] Invalid agent name handled gracefully
- [ ] Max steps (10) prevents infinite loops
- [ ] JSON parsing failures fall back correctly
- [ ] MCP timeouts handled (if using MCP servers)
- [ ] Empty user message handled

**Integration:**
- [ ] CORS allows requests from localhost:3000
- [ ] Request/response format matches assistant-ui expectations
- [ ] Events array contains all orchestration steps
- [ ] Server auto-reloads on file changes (--reload flag)

---

## Troubleshooting Guide

### Issue: "Connection refused" to Ollama

**Symptoms:**
```
requests.exceptions.ConnectionError: ('Connection aborted.', ConnectionRefusedError(111, 'Connection refused'))
```

**Solutions:**
1. Check Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```
2. Start Ollama if not running:
   ```bash
   ollama serve
   ```
3. Verify model is available:
   ```bash
   ollama pull gpt-oss-20b
   ```

### Issue: Agent returns non-JSON response

**Symptoms:**
```
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Solutions:**
1. Check agent system prompt enforces JSON-only
2. Lower temperature (try 0.1 instead of 0.2)
3. Add more explicit JSON examples in prompts
4. Verify fallback parsing in `run_agent()` is working
5. Check raw LLM response in debug logs

### Issue: MCP tools timing out

**Symptoms:**
```
ERROR(mcp:http://localhost:8001,list_files): HTTPConnectionPool(host='localhost', port=8001): Max retries exceeded
```

**Solutions:**
1. Verify MCP server is running:
   ```bash
   curl http://localhost:8001/health
   ```
2. Increase timeout in `call_mcp_tool()`:
   ```python
   timeout=60  # instead of 30
   ```
3. Check MCP server logs for errors
4. Verify request format matches MCP server expectations

### Issue: CORS errors from frontend

**Symptoms:**
```
Access to fetch at 'http://localhost:8000/chat' from origin 'http://localhost:5173' has been blocked by CORS policy
```

**Solutions:**
1. Add frontend origin to allowed origins in `backend/main.py`:
   ```python
   allow_origins=["http://localhost:3000", "http://localhost:5173"]
   ```
2. Restart FastAPI server
3. Clear browser cache

### Issue: Import errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solutions:**
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Verify virtual environment is activated
3. Check Python version (3.10+ required)

---

## Future Enhancements (Out of Scope)

The following features are intentionally **not** included in the current spec:

- ❌ Streaming responses (SSE/WebSocket)
- ❌ Authentication/authorization
- ❌ Database persistence
- ❌ Rate limiting
- ❌ Request logging to files
- ❌ Production-grade error monitoring
- ❌ Containerization (Docker)
- ❌ API versioning
- ❌ Async tool execution
- ❌ Multi-user support
- ❌ Conversation history storage

These may be added in future iterations but are not required for initial implementation.

---

## Quick Reference Commands

### Development

```bash
# Create directory structure
mkdir -p backend/orchestrator

# Install dependencies
pip install fastapi uvicorn requests pydantic

# Start server
uvicorn backend.main:app --reload --port 8000

# Start server with debug logging
uvicorn backend.main:app --reload --port 8000 --log-level debug
```

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Chat test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":[{"type":"text","text":"Hello"}]}]}'

# Ollama test
curl http://localhost:11434/api/tags

# MCP filesystem test
curl http://localhost:8001/health

# MCP trader test
curl http://localhost:8002/health
```

### Git

```bash
# Status
git status

# Commit
git add .
git commit -m "feat: description"

# Push
git push -u origin claude/claude-md-mi0ayxvf17n52854-015FZkkYHb2ZPF3GUmbSVvHg
```

---

## Summary for AI Assistants

### What This Project Is

A Python backend that orchestrates AI agents using Ollama LLM to handle user queries through a FastAPI endpoint. Agents can use local tools (file I/O, code execution) and MCP server integrations (filesystem, trading) to accomplish tasks.

### Current State

**Specification complete, implementation pending.** All documentation exists, no code files exist yet. Ready for implementation.

### What to Do Next

1. Read SPECS.md for detailed implementation requirements
2. Create directory structure and requirements.txt
3. Implement files in recommended order (models → llm → tools → agents → core → main)
4. Test each component as you build
5. Verify end-to-end functionality
6. Commit and push to feature branch

### Key Success Criteria

- ✅ All functions have type hints
- ✅ Agents respond in strict JSON format
- ✅ Tool failures return error strings (not exceptions)
- ✅ Orchestration loop has max 10 steps
- ✅ `/chat` and `/health` endpoints work
- ✅ Integration with Ollama successful
- ✅ Tests pass with curl commands

---

**Last Updated:** 2025-11-15
**For Questions:** Refer to SPECS.md, README.md, or .claude/claude-instructions.md
