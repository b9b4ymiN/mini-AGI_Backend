"""
Tool implementations and registry for local and MCP tools.
"""

from typing import Dict, Any, Callable
import requests


# ============================================================================
# Local Tool Implementations
# ============================================================================

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


# ============================================================================
# MCP Bridge Function
# ============================================================================

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


# ============================================================================
# Tool Registry
# ============================================================================

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
