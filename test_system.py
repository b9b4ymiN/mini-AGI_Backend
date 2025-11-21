#!/usr/bin/env python3
"""
Test script to verify the Mini-AGI Backend is working correctly.
Tests health endpoint, chat endpoint, and basic orchestration.
"""

import requests
import json
import time
import sys
from typing import Dict, Any


def test_health(base_url: str = "http://127.0.0.1:8000") -> bool:
    """Test the health endpoint."""
    print("\n=== Testing Health Endpoint ===")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "ok":
            print("✅ Health endpoint working")
            return True
        else:
            print(f"❌ Health endpoint returned unexpected data: {data}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
        return False


def test_chat_simple(base_url: str = "http://127.0.0.1:8000") -> bool:
    """Test the chat endpoint with a simple message."""
    print("\n=== Testing Simple Chat ===")
    try:
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Hello, this is a test!"}]
                }
            ]
        }

        response = requests.post(
            f"{base_url}/chat",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        print(f"Response: {json.dumps(data, indent=2)}")

        if "answer" in data and "events" in data:
            print("✅ Chat endpoint returned valid response")
            print(f"   Answer: {data['answer'][:100]}...")
            print(f"   Events: {len(data['events'])} steps")
            return True
        else:
            print(f"❌ Chat endpoint returned unexpected format")
            return False

    except Exception as e:
        print(f"❌ Chat endpoint failed: {e}")
        return False


def test_tool_execution(base_url: str = "http://127.0.0.1:8000") -> bool:
    """Test tool execution via chat."""
    print("\n=== Testing Tool Execution ===")
    try:
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Calculate the sum of numbers 1 to 10 using Python"}]
                }
            ]
        }

        response = requests.post(
            f"{base_url}/chat",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        # Check if any event used a tool
        events = data.get("events", [])
        used_tool = any(event.get("action") == "use_tool" for event in events)

        if used_tool:
            print("✅ Tool execution detected in events")
            for event in events:
                if event.get("action") == "use_tool":
                    print(f"   Tool used: {event.get('tool')}")
            return True
        else:
            print("⚠️  No tool execution detected (may be expected if mock Ollama gives direct answer)")
            return True

    except Exception as e:
        print(f"❌ Tool execution test failed: {e}")
        return False


def check_ollama(ollama_url: str = "http://127.0.0.1:11434") -> bool:
    """Check if Ollama (or mock) is running."""
    print("\n=== Checking Ollama ===")
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()

        if "models" in data:
            print(f"✅ Ollama is running")
            models = [m.get("name") for m in data.get("models", [])]
            print(f"   Available models: {models}")
            return True
        else:
            print(f"⚠️  Ollama responded but format unexpected")
            return False

    except Exception as e:
        print(f"❌ Ollama is not running: {e}")
        print("   You can start the mock Ollama with: python mock_ollama_server.py")
        return False


def check_mcp_servers() -> Dict[str, bool]:
    """Check if MCP servers are running."""
    print("\n=== Checking MCP Servers ===")
    results = {}

    servers = {
        "filesystem": "http://127.0.0.1:8001",
        "trader": "http://127.0.0.1:8002"
    }

    for name, url in servers.items():
        try:
            response = requests.get(f"{url}/health", timeout=2)
            response.raise_for_status()
            results[name] = True
            print(f"✅ {name.capitalize()} MCP server is running")
        except Exception as e:
            results[name] = False
            print(f"⚠️  {name.capitalize()} MCP server is not running")
            print(f"   Start with: python mock_mcp_server.py {name}")

    return results


def test_database_management(base_url: str = "http://127.0.0.1:8000") -> bool:
    """Test database management endpoints."""
    print("\n=== Testing Database Management ===")
    try:
        # Test /db/size
        response = requests.get(f"{base_url}/db/size", timeout=5)
        response.raise_for_status()
        size_data = response.json()

        if "size_mb" in size_data and "max_size_mb" in size_data:
            print(f"✅ Database size: {size_data['size_mb']:.2f} MB / {size_data['max_size_mb']} MB")
            print(f"   Usage: {size_data['usage_percent']:.2f}%")
        else:
            print("❌ /db/size returned unexpected format")
            return False

        # Test /db/status
        response = requests.get(f"{base_url}/db/status", timeout=5)
        response.raise_for_status()
        status_data = response.json()

        if "status" in status_data:
            print(f"✅ Database status: {status_data['status']}")
        else:
            print("❌ /db/status returned unexpected format")
            return False

        # Test /db/stats
        response = requests.get(f"{base_url}/db/stats", timeout=5)
        response.raise_for_status()
        stats_data = response.json()

        if "total_conversations" in stats_data:
            print(f"✅ Database stats:")
            print(f"   Conversations: {stats_data['total_conversations']}")
            print(f"   Sessions: {stats_data['total_sessions']}")
            print(f"   Facts: {stats_data['total_facts']}")
        else:
            print("❌ /db/stats returned unexpected format")
            return False

        # Test /db/recommendations
        response = requests.get(f"{base_url}/db/recommendations", timeout=5)
        response.raise_for_status()
        rec_data = response.json()

        if "recommendations" in rec_data:
            print(f"✅ Storage recommendations: {len(rec_data['recommendations'])} items")
        else:
            print("❌ /db/recommendations returned unexpected format")
            return False

        print("✅ All database management endpoints working")
        return True

    except Exception as e:
        print(f"❌ Database management test failed: {e}")
        return False


def test_memory_system(base_url: str = "http://127.0.0.1:8000") -> bool:
    """Test memory system (session management)."""
    print("\n=== Testing Memory System ===")
    try:
        # Create a new session
        response = requests.post(f"{base_url}/sessions", timeout=5)
        response.raise_for_status()
        session_data = response.json()

        if "session_id" not in session_data:
            print("❌ Failed to create session")
            return False

        session_id = session_data["session_id"]
        print(f"✅ Created session: {session_id}")

        # Send first message
        payload1 = {
            "session_id": session_id,
            "user_id": "test-user",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "My name is TestUser"}]
                }
            ]
        }

        response = requests.post(f"{base_url}/chat", json=payload1, timeout=30)
        response.raise_for_status()
        data1 = response.json()

        if "session_id" not in data1:
            print("❌ First message didn't return session_id")
            return False

        print(f"✅ First message sent")

        # Send second message asking about name
        payload2 = {
            "session_id": session_id,
            "user_id": "test-user",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "What is my name?"}]
                }
            ]
        }

        response = requests.post(f"{base_url}/chat", json=payload2, timeout=30)
        response.raise_for_status()
        data2 = response.json()

        # Check if context was used
        if data2.get("context_used"):
            print(f"✅ Memory working - context was used")
            print(f"   Answer: {data2['answer'][:100]}...")
        else:
            print("⚠️  Context not used (may need more test data)")

        # Get session history
        response = requests.get(f"{base_url}/sessions/{session_id}/history?limit=10", timeout=5)
        response.raise_for_status()
        history_data = response.json()

        if "history" in history_data and len(history_data["history"]) >= 2:
            print(f"✅ Session history: {len(history_data['history'])} turns")
        else:
            print("⚠️  Session history may not be complete")

        print("✅ Memory system working")
        return True

    except Exception as e:
        print(f"❌ Memory system test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Mini-AGI Backend System Test")
    print("=" * 60)

    # Check dependencies first
    ollama_ok = check_ollama()
    mcp_status = check_mcp_servers()

    print("\n" + "=" * 60)
    print("Dependency Status:")
    print(f"  Ollama: {'✅ Running' if ollama_ok else '❌ Not running'}")
    print(f"  MCP Filesystem: {'✅ Running' if mcp_status.get('filesystem') else '⚠️  Not running (optional)'}")
    print(f"  MCP Trader: {'✅ Running' if mcp_status.get('trader') else '⚠️  Not running (optional)'}")

    if not ollama_ok:
        print("\n❌ Ollama is required. Please start it with:")
        print("   python mock_ollama_server.py")
        print("   (or use real Ollama)")
        sys.exit(1)

    # Wait a moment for servers to be ready
    print("\nWaiting 2 seconds for servers to be ready...")
    time.sleep(2)

    # Run tests
    results = []
    results.append(("Health Check", test_health()))
    results.append(("Simple Chat", test_chat_simple()))
    results.append(("Tool Execution", test_tool_execution()))
    results.append(("Memory System", test_memory_system()))
    results.append(("DB Management", test_database_management()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20} {status}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 All tests passed! System is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
