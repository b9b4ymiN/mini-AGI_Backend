"""
Agent system with registry and execution logic.
"""

from typing import Dict, Any
import json
from .llm import call_llm


# ============================================================================
# Agent Registry
# ============================================================================

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


# ============================================================================
# Agent Execution Function
# ============================================================================

def run_agent(
    agent_name: str,
    user_content: str,
    extra_context: str = "",
    custom_system_instruction: str = ""
) -> Dict[str, Any]:
    """
    Execute an agent and parse its JSON response.

    Args:
        agent_name: Name of agent from AGENTS registry
        user_content: Main user query or instruction
        extra_context: Optional context from previous steps
        custom_system_instruction: Optional custom system instruction to prepend

    Returns:
        Dict with keys: thought, action, tool, target_agent, args, answer
    """
    # 1. Get agent config
    if agent_name not in AGENTS:
        raise ValueError(f"Unknown agent: {agent_name}")

    agent_cfg = AGENTS[agent_name]

    # 2. Build messages
    # Merge all system content into one message (some LLMs don't support multiple system messages)
    system_parts = []

    # Add custom system instruction first if provided
    if custom_system_instruction:
        system_parts.append(f"CUSTOM USER INSTRUCTIONS:\n{custom_system_instruction}\n")

    # Add agent's base system prompt
    system_parts.append(agent_cfg["system"])

    # Add context from previous steps if any
    if extra_context:
        system_parts.append(f"\nContext from previous steps:\n{extra_context}")

    # Combine all system parts into one message
    combined_system = "\n---\n".join(system_parts)

    messages = [
        {"role": "system", "content": combined_system},
        {"role": "user", "content": user_content}
    ]

    # 3. Call LLM
    raw_response = call_llm(messages)

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
