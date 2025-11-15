"""
Simple mock MCP server for testing purposes.
This server simulates filesystem and trader MCP operations.
"""

from fastapi import FastAPI, Request
from typing import Dict, Any
import os
import json

# Filesystem mock server (port 8001)
fs_app = FastAPI(title="Mock Filesystem MCP Server")

@fs_app.get("/health")
def fs_health():
    return {"status": "ok", "server": "mock-filesystem"}

@fs_app.post("/invoke")
async def fs_invoke(request: Request):
    """Mock filesystem operations."""
    body = await request.json()
    tool = body.get("tool", "")
    args = body.get("args", {})

    if tool == "list_files":
        path = args.get("path", ".")
        try:
            files = os.listdir(path)[:10]  # Limit to 10 files
            return json.dumps({"files": files, "path": path})
        except Exception as e:
            return json.dumps({"error": str(e)})

    elif tool == "read_file":
        path = args.get("path", "")
        try:
            with open(path, "r") as f:
                content = f.read()[:1000]  # Limit to 1000 chars
            return json.dumps({"content": content, "path": path})
        except Exception as e:
            return json.dumps({"error": str(e)})

    elif tool == "write_file":
        path = args.get("path", "")
        content = args.get("content", "")
        try:
            with open(path, "w") as f:
                f.write(content)
            return json.dumps({"success": True, "path": path})
        except Exception as e:
            return json.dumps({"error": str(e)})

    else:
        return json.dumps({"error": f"Unknown tool: {tool}"})


# Trader mock server (port 8002)
trader_app = FastAPI(title="Mock Trader MCP Server")

@trader_app.get("/health")
def trader_health():
    return {"status": "ok", "server": "mock-trader"}

@trader_app.post("/invoke")
async def trader_invoke(request: Request):
    """Mock trading operations."""
    body = await request.json()
    tool = body.get("tool", "")
    args = body.get("args", {})

    if tool == "backtest":
        strategy = args.get("strategy", "unknown")
        return json.dumps({
            "strategy": strategy,
            "result": {
                "total_return": "15.3%",
                "sharpe_ratio": 1.42,
                "max_drawdown": "-8.5%",
                "trades": 47
            }
        })

    elif tool == "get_price":
        symbol = args.get("symbol", "BTC")
        return json.dumps({
            "symbol": symbol,
            "price": 45123.50,
            "timestamp": "2024-01-15T10:30:00Z"
        })

    elif tool == "place_order":
        return json.dumps({
            "order_id": "mock-12345",
            "status": "filled",
            "message": "Mock order placed successfully"
        })

    else:
        return json.dumps({"error": f"Unknown tool: {tool}"})


if __name__ == "__main__":
    import sys
    import uvicorn

    if len(sys.argv) > 1 and sys.argv[1] == "filesystem":
        print("Starting Mock Filesystem MCP Server on port 8001...")
        uvicorn.run(fs_app, host="127.0.0.1", port=8001)
    elif len(sys.argv) > 1 and sys.argv[1] == "trader":
        print("Starting Mock Trader MCP Server on port 8002...")
        uvicorn.run(trader_app, host="127.0.0.1", port=8002)
    else:
        print("Usage: python mock_mcp_server.py [filesystem|trader]")
        print("  filesystem - Start filesystem mock on port 8001")
        print("  trader     - Start trader mock on port 8002")
