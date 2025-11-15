# Mini-AGI Backend - Project Instructions

## Project Overview
Python backend orchestrator that coordinates AI agents using Ollama + MCP tools. Exposes a simple FastAPI endpoint for chat interactions.

## Core Architecture

**Agent System:**
- `orchestrator` - Main coordinator (always starts here)
- `coder` - Python/Node.js/trading code specialist  
- `researcher` - Information analysis and structuring

**Protocol:**
- Agents communicate via JSON-only responses
- Actions: `use_tool` | `delegate` | `final`
- Max 10 orchestration steps per request

## Technology Stack

**Runtime:**
- Python 3.10+ with full type hints
- FastAPI + uvicorn (port 8000)
- Pydantic for models and validation

**LLM:**
- Ollama @ `http://localhost:11434`
- Model: `"gpt-oss-20b"`
- Temperature: 0.2 (low for consistency)

**Tools:**
- Local: `read_file`, `write_file`, `run_python`
- MCP servers: filesystem (8001), trader (8002)

## Key Principles

1. **Type Safety First** - All functions must have type hints
2. **JSON Protocol Strict** - Agents MUST respond in JSON format only
3. **Graceful Degradation** - Parse failures fall back to safe defaults
4. **Context Accumulation** - Log each step for agent awareness
5. **No Streaming** - Simple request → response pattern

## Code Organization

```
backend/
  main.py              # FastAPI app, /chat endpoint
  orchestrator/
    __init__.py
    llm.py            # Ollama integration (call_ollama)
    agents.py         # AGENTS config + run_agent()
    tools.py          # TOOLS registry + implementations
    core.py           # orchestrate() main loop
    models.py         # Pydantic: Event, Request, Response
```

## Important Constraints

**Security:**
- `run_python` is dev-only (unsafe for production)
- No authentication on local tools
- CORS allows `localhost:3000` only

**Error Handling:**
- Tool failures return error strings (not exceptions)
- LLM parsing failures use fallback JSON
- Invalid actions reset to orchestrator

**Agent Response Schema:**
```json
{
  "thought": "reasoning in English",
  "action": "use_tool | delegate | final",
  "tool": "tool_name or null",
  "target_agent": "agent_name or null", 
  "args": {},
  "answer": "final answer or empty"
}
```

## Development Workflow

**Start server:**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Test endpoint:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role":"user", "content":[{"type":"text","text":"Hello"}]}]}'
```

## Coding Preferences

**Style:**
- Use `typing` module extensively
- Prefer explicit over implicit
- Document complex logic with inline comments
- Keep functions focused and testable

**Patterns:**
- Registry pattern for agents and tools
- Immutable data where possible
- Early returns for validation
- Descriptive variable names

## When Making Changes

✅ **Do:**
- Maintain backwards compatibility with frontend
- Add tools to TOOLS registry properly
- Test JSON parsing edge cases
- Keep orchestration loop readable

❌ **Don't:**
- Break the JSON protocol
- Add streaming (out of scope)
- Modify Ollama request format without testing
- Skip type hints

## Quick Reference

**Add new tool:**
1. Implement function in `tools.py`
2. Add to `TOOLS` dict
3. Update orchestrator system prompt

**Add new agent:**
1. Add to `AGENTS` dict in `agents.py`
2. Define clear system prompt
3. Specify JSON response format

**Debug tips:**
- Check `context_log` in orchestrate loop
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Enable FastAPI debug: `--reload --log-level debug`

---

For detailed implementation specs, see `SPECS.md`
