# Claude Code – Backend Implementation Specification

**Full technical specification for Mini-AGI Backend**

---

## Table of Contents

1. [Overview & Objectives](#overview)
2. [Tech Stack & Dependencies](#dependencies)
3. [Project Structure](#structure)
4. [LLM Integration (Ollama)](#llm)
5. [Agent System](#agents)
6. [Tool System (Local + MCP)](#tools)
7. [Orchestrator Core Logic](#orchestrator)
8. [API & Data Models](#api)
9. [Deployment & Testing](#deployment)

---

## <a id="overview"></a>1. Overview & Objectives

### Purpose
Build a Python backend that orchestrates AI agents using:
- **Ollama** LLM (model: `gpt-oss-20b`)
- **Agent-based architecture** (orchestrator, coder, researcher)
- **Tool integration** (local Python tools + MCP servers)
- **Simple HTTP API** (FastAPI)

### High-Level Behavior

1. Receive user query via `POST /chat`
2. Start with `orchestrator` agent
3. Execute orchestration loop (max 10 steps):
   - Agent returns JSON action
   - Execute tool calls or delegate to specialist agents
   - Accumulate context for next step
4. Return final answer + event log

### Explicit Non-Goals
- ❌ No streaming (SSE/WebSocket)
- ❌ No authentication/authorization
- ❌ No production-grade security for `run_python`

---

## <a id="dependencies"></a>2. Tech Stack & Dependencies

### Core Stack
- **Language:** Python 3.10+
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **HTTP Client:** requests
- **Validation:** Pydantic

### Installation

```bash
pip install fastapi uvicorn requests pydantic
```

### External Services

**Ollama:**
- Base URL: `http://localhost:11434`
- Endpoint: `/api/chat`
- Model: `"gpt-oss-20b"`

**MCP Servers** (assumed running):
- Filesystem MCP: `http://localhost:8001`
- Trader MCP: `http://localhost:8002`

---

## <a id="structure"></a>3. Project Structure

```
backend/
├── main.py                    # FastAPI application
└── orchestrator/
    ├── __init__.py           # Package init
    ├── llm.py                # Ollama client
    ├── agents.py             # Agent configs + run_agent()
    ├── tools.py              # Tool implementations + registry
    ├── core.py               # Main orchestrate() loop
    └── models.py             # Pydantic models
```

---

## <a id="llm"></a>4. LLM Integration (Ollama)

**File:** `backend/orchestrator/llm.py`

### Function Signature

```python
from typing import List, Dict

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gpt-oss-20b"

def call_ollama(messages: List[Dict[str, str]], model: str = MODEL_NAME) -> str:
    """
    Call Ollama chat API and return the assistant's response content.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (default: gpt-oss-20b)
        
    Returns:
        String content from assistant's response
        
    Raises:
        Exception: If HTTP request fails
    """
    pass
```

### Implementation Requirements

**Request Payload:**
```python
payload = {
    "model": model,
    "messages": messages,
    "stream": False,
    "options": {
        "temperature": 0.2,
    },
}
```

**HTTP Call:**
```python
import requests

response = requests.post(OLLAMA_URL, json=payload, timeout=60)
response.raise_for_status()
data = response.json()
```

**Response Parsing:**
```python
# Expected structure:
# {
#   "message": {
#     "role": "assistant",
#     "content": "..."
#   }
# }
return data["message"]["content"]
```

**Error Handling:**
- Raise clear exception if status != 200
- Include model name and endpoint in error message

---

## <a id="agents"></a>5. Agent System

**File:** `backend/orchestrator/agents.py`

### 5.1 Agent Registry

```python
from typing import Dict

AGENTS: Dict[str, Dict[str, str]] = {
    "orchestrator": {
        "system": """You are the Orchestrator AI.
You coordinate tools (local + MCP) and specialist agents.
You ALWAYS respond ONLY in JSON with this schema:

{
  "thought": "short reasoning in English",
  "action": "use_tool | delegate | final",
  "tool": "tool_name or null",
  "target_agent": "agent_name or null",
  "args": {},
  "answer": "final user-facing answer or empty if not final"
}

Available tools:
- read_file(path: str) - Read file contents
- write_file(path: str, content: str) - Write to file
- run_python(code: str) - Execute Python code
- mcp_filesystem(tool: str, args: dict) - MCP filesystem operations
- mcp_trader(tool: str, args: dict) - MCP trading operations

Available agents:
- coder: Python/Node.js/Next.js/trading code expert
- researcher: Information analysis and structuring

Actions:
- use_tool: Call a tool and await result
- delegate: Hand off subtask to specialist agent
- final: Provide final answer to user
"""
    },
    
    "coder": {
        "system": """You are CoderAgent, an expert in:
- Python, Node.js, Next.js
- Trading automation and algorithms
- Code refactoring and debugging

You help write, refactor, and debug code.
Always respond in JSON: {thought, action, tool, target_agent, args, answer}.

When you need to:
- Read/write files: use read_file or write_file tools
- Test code: use run_python tool
- Complete task: action="final" with answer
"""
    },
    
    "researcher": {
        "system": """You are ResearchAgent.
You analyze, summarize, and structure information for the user.

Always respond in JSON: {thought, action, tool, target_agent, args, answer}.

When you need to:
- Read documents: use read_file tool
- Analyze data: use run_python tool
- Complete task: action="final" with answer
"""
    },
}
```

### 5.2 Agent Execution Function

```python
from typing import Dict, Any
import json
from .llm import call_ollama

def run_agent(
    agent_name: str, 
    user_content: str, 
    extra_context: str = ""
) -> Dict[str, Any]:
    """
    Execute an agent and parse its JSON response.
    
    Args:
        agent_name: Name of agent from AGENTS registry
        user_content: Main user query or instruction
        extra_context: Optional context from previous steps
        
    Returns:
        Dict with keys: thought, action, tool, target_agent, args, answer
    """
    # 1. Get agent config
    if agent_name not in AGENTS:
        raise ValueError(f"Unknown agent: {agent_name}")
    
    agent_cfg = AGENTS[agent_name]
    
    # 2. Build messages
    messages = [
        {"role": "system", "content": agent_cfg["system"]},
    ]
    
    if extra_context:
        messages.append({
            "role": "system", 
            "content": f"Context from previous steps:\n{extra_context}"
        })
    
    messages.append({
        "role": "user", 
        "content": user_content
    })
    
    # 3. Call LLM
    raw_response = call_ollama(messages)
    
    # 4. Parse JSON with fallbacks
    data = None
    
    # Try direct parse
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks or text
        try:
            # Find first { and last }
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(raw_response[start:end])
        except:
            pass
    
    # Ultimate fallback
    if data is None:
        data = {
            "thought": "JSON parsing failed",
            "action": "final",
            "tool": None,
            "target_agent": None,
            "args": {},
            "answer": raw_response,
        }
    
    # 5. Ensure required keys exist
    data.setdefault("thought", "")
    data.setdefault("action", "final")
    data.setdefault("tool", None)
    data.setdefault("target_agent", None)
    data.setdefault("args", {})
    data.setdefault("answer", "")
    
    return data
```

---

## <a id="tools"></a>6. Tool System (Local + MCP)

**File:** `backend/orchestrator/tools.py`

### 6.1 Local Tool Implementations

```python
from typing import Dict, Any, Callable
import requests

def tool_read_file(path: str) -> str:
    """Read file contents."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR(read_file): {e}"

def tool_write_file(path: str, content: str) -> str:
    """Write content to file."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"OK: Wrote {len(content)} chars to {path}"
    except Exception as e:
        return f"ERROR(write_file): {e}"

def tool_run_python(code: str) -> str:
    """
    Execute Python code in isolated scope.
    WARNING: Dev/local only - not safe for untrusted code.
    """
    local_vars: Dict[str, Any] = {}
    try:
        exec(code, {"__builtins__": __builtins__}, local_vars)
        return f"EXEC_OK: {local_vars}"
    except Exception as e:
        return f"EXEC_ERROR: {e}"
```

### 6.2 MCP Bridge Function

```python
def call_mcp_tool(server_url: str, tool_name: str, args: Dict[str, Any]) -> str:
    """
    Generic bridge to call MCP server via HTTP.
    
    Args:
        server_url: Base URL of MCP server
        tool_name: Name of tool to invoke
        args: Tool arguments as dict
        
    Returns:
        String response from MCP server
    """
    try:
        resp = requests.post(
            server_url.rstrip("/") + "/invoke",
            json={"tool": tool_name, "args": args},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"ERROR(mcp:{server_url},{tool_name}): {e}"
```

### 6.3 Tool Registry

```python
TOOLS: Dict[str, Callable[..., str]] = {
    # Local tools
    "read_file": lambda **kw: tool_read_file(kw.get("path", "")),
    
    "write_file": lambda **kw: tool_write_file(
        kw.get("path", ""), 
        kw.get("content", "")
    ),
    
    "run_python": lambda **kw: tool_run_python(kw.get("code", "")),
    
    # MCP tools
    "mcp_filesystem": lambda **kw: call_mcp_tool(
        server_url="http://localhost:8001",
        tool_name=kw.get("tool", "list_files"),
        args=kw.get("args", {}),
    ),
    
    "mcp_trader": lambda **kw: call_mcp_tool(
        server_url="http://localhost:8002",
        tool_name=kw.get("tool", "backtest"),
        args=kw.get("args", {}),
    ),
}
```

---

## <a id="orchestrator"></a>7. Orchestrator Core Logic

**File:** `backend/orchestrator/core.py`

### Function Signature

```python
from typing import Tuple, List
from .models import OrchestratorEvent

def orchestrate(user_input: str, max_steps: int = 10) -> Tuple[str, List[OrchestratorEvent]]:
    """
    Main orchestration loop.
    
    Args:
        user_input: User's query or instruction
        max_steps: Maximum orchestration steps (default: 10)
        
    Returns:
        Tuple of (final_answer, event_list)
    """
    pass
```

### Implementation Logic

```python
from .agents import run_agent, AGENTS
from .tools import TOOLS
import json

def orchestrate(user_input: str, max_steps: int = 10) -> Tuple[str, List[OrchestratorEvent]]:
    # Initialize state
    context_log: List[str] = []
    events: List[OrchestratorEvent] = []
    current_agent: str = "orchestrator"
    current_query: str = user_input
    
    # Main loop
    for step in range(max_steps):
        # 1. Execute current agent
        result = run_agent(
            current_agent, 
            current_query, 
            extra_context="\n".join(context_log)
        )
        
        # 2. Extract fields
        thought = result.get("thought", "")
        action = result.get("action", "final")
        tool_name = result.get("tool")
        target_agent = result.get("target_agent")
        args = result.get("args", {}) or {}
        answer = result.get("answer", "")
        
        # 3. Record event
        events.append(
            OrchestratorEvent(
                step=step + 1,
                agent=current_agent,
                action=action,
                tool=tool_name,
                target_agent=target_agent,
                thought=thought,
            )
        )
        
        # 4. Update context log
        context_log.append(
            f"[{current_agent} step {step+1}] {json.dumps(result, ensure_ascii=False)}"
        )
        
        # 5. Handle action
        if action == "final":
            # Done - return answer
            return (answer or "[NO ANSWER]", events)
        
        elif action == "use_tool":
            # Execute tool
            if tool_name and tool_name in TOOLS:
                tool_fn = TOOLS[tool_name]
                tool_output = tool_fn(**args)
                
                # Prepare next query with tool result
                current_query = (
                    f"Tool `{tool_name}` output:\n{tool_output}\n\n"
                    "Now continue your reasoning and decide next action."
                )
                # Stay with same agent
            else:
                # Unknown tool - ask agent to provide final answer
                current_agent = "orchestrator"
                current_query = (
                    f"Unknown tool '{tool_name}'. "
                    "Please provide a final answer with available information."
                )
        
        elif action == "delegate":
            # Switch to target agent
            if target_agent and target_agent in AGENTS:
                current_agent = target_agent
                current_query = args.get("task", answer) or f"User goal: {user_input}"
            else:
                # Unknown agent - reset to orchestrator
                current_agent = "orchestrator"
                current_query = (
                    f"Unknown agent '{target_agent}'. "
                    "Please handle the task yourself or use available tools."
                )
        
        else:
            # Invalid action - ask for final
            current_agent = "orchestrator"
            current_query = (
                f"Invalid action '{action}'. "
                f"Previous JSON: {json.dumps(result)}\n"
                "Please provide a 'final' answer."
            )
    
    # Max steps reached without final
    return (
        "[MAX STEPS REACHED - No final answer provided]",
        events
    )
```

---

## <a id="api"></a>8. API & Data Models

### 8.1 Data Models

**File:** `backend/orchestrator/models.py`

```python
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class OrchestratorEvent(BaseModel):
    """Record of a single orchestration step."""
    step: int
    agent: str
    action: str
    tool: Optional[str] = None
    target_agent: Optional[str] = None
    thought: str

class ChatRequest(BaseModel):
    """Request format matching assistant-ui."""
    messages: List[Dict[str, Any]]

class ChatResponse(BaseModel):
    """Response with final answer and execution trace."""
    answer: str
    events: List[OrchestratorEvent]
```

### 8.2 FastAPI Application

**File:** `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from orchestrator.models import ChatRequest, ChatResponse
from orchestrator.core import orchestrate

app = FastAPI(
    title="Mini-AGI Backend",
    description="Agent orchestration with Ollama + MCP",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.
    
    Expects assistant-ui message format:
    {
      "messages": [
        {
          "role": "user",
          "content": [{"type": "text", "text": "..."}]
        }
      ]
    }
    """
    # Extract latest user message
    last_user_msg = ""
    
    for msg in reversed(req.messages):
        if msg.get("role") == "user":
            content = msg.get("content", [])
            
            if content and isinstance(content, list):
                first_item = content[0]
                
                if isinstance(first_item, dict) and first_item.get("type") == "text":
                    last_user_msg = first_item.get("text", "")
                    break
    
    if not last_user_msg:
        last_user_msg = "No text content provided."
    
    # Run orchestration
    answer, events = orchestrate(last_user_msg)
    
    return ChatResponse(answer=answer, events=events)

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

---

## <a id="deployment"></a>9. Deployment & Testing

### 9.1 Start Development Server

```bash
# From project root
uvicorn backend.main:app --reload --port 8000

# With custom log level
uvicorn backend.main:app --reload --port 8000 --log-level debug
```

### 9.2 Test Endpoints

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Chat Request:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Write a Python function to calculate fibonacci"
          }
        ]
      }
    ]
  }'
```

### 9.3 Verify Ollama

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Test model
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-20b",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### 9.4 Common Issues

**Problem:** Ollama connection refused
```
Solution: Start Ollama service or check URL/port
```

**Problem:** JSON parsing fails for agent responses
```
Solution: Check agent system prompts enforce JSON-only output
Add more explicit examples in prompts
```

**Problem:** MCP tools timeout
```
Solution: Verify MCP servers are running
Check server URLs in tools.py
Increase timeout in call_mcp_tool()
```

---

## Appendix: Complete File Checklist

- [ ] `backend/main.py` - FastAPI app with /chat endpoint
- [ ] `backend/orchestrator/__init__.py` - Package marker
- [ ] `backend/orchestrator/llm.py` - Ollama client
- [ ] `backend/orchestrator/agents.py` - AGENTS dict + run_agent()
- [ ] `backend/orchestrator/tools.py` - TOOLS registry + implementations
- [ ] `backend/orchestrator/core.py` - orchestrate() loop
- [ ] `backend/orchestrator/models.py` - Pydantic models

---

**End of Specification**
