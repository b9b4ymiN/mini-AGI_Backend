# 🧠 Memory System Usage Guide

**Complete guide to using conversation memory in Mini-AGI Backend**

---

## 🎯 How Memory Works

The AI remembers conversations using **session IDs**. Each conversation has a unique session, and the AI can recall previous messages within that session.

### Memory Layers

1. **Short-term Memory** - Last 5 conversation turns (automatically retrieved)
2. **Long-term Memory** - User facts and preferences (stored permanently)
3. **Search** - Full-text search across all conversations

---

## ⚠️ Common Mistake: Session ID Usage

### ❌ WRONG - Reusing Your Own Session ID

```bash
# First request with custom session_id
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123",
    "user_id": "john",
    "messages": [{"role": "user", "content": "My name is Both"}]
  }'

# Response returns: "session_id": "d87c64f378f935e1"

# ❌ WRONG - Using the original session_id again
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123",
    "user_id": "john",
    "messages": [{"role": "user", "content": "What is my name?"}]
  }'
# This creates a NEW session, AI won't remember!
```

### ✅ CORRECT - Use the Returned Session ID

```bash
# First request (with or without session_id)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "john",
    "messages": [{"role": "user", "content": "My name is Both"}]
  }'

# Response: {"session_id": "d87c64f378f935e1", ...}
# ⚠️ SAVE THIS SESSION ID!

# ✅ CORRECT - Use the returned session_id
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "d87c64f378f935e1",
    "user_id": "john",
    "messages": [{"role": "user", "content": "What is my name?"}]
  }'

# Response: "Your name is Both, as you mentioned earlier."
```

---

## 📝 Step-by-Step Examples

### Example 1: Simple Memory Conversation

**Step 1: First Message (No session_id needed)**

```bash
curl -X POST http://myzai.duckdns.org/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "john",
    "messages": [{"role": "user", "content": "My name is Both"}]
  }'
```

**Response:**
```json
{
  "answer": "Hello Both! Nice to meet you...",
  "session_id": "d87c64f378f935e1",
  "context_used": false
}
```

**⚠️ IMPORTANT: Save the `session_id` value!**

---

**Step 2: Continue Conversation (Use returned session_id)**

```bash
curl -X POST http://myzai.duckdns.org/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "d87c64f378f935e1",
    "user_id": "john",
    "messages": [{"role": "user", "content": "What is my name?"}]
  }'
```

**Response:**
```json
{
  "answer": "Your name is Both, as you mentioned earlier.",
  "session_id": "d87c64f378f935e1",
  "context_used": true
}
```

**✅ Notice: `context_used: true` - Memory was used!**

---

### Example 2: Multi-Turn Conversation

```bash
# Message 1
curl -X POST http://myzai.duckdns.org/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "messages": [{"role": "user", "content": "I love Python programming"}]
  }'
# Save session_id: "abc-123-xyz"

# Message 2
curl -X POST http://myzai.duckdns.org/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123-xyz",
    "user_id": "alice",
    "messages": [{"role": "user", "content": "My favorite framework is FastAPI"}]
  }'

# Message 3
curl -X POST http://myzai.duckdns.org/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123-xyz",
    "user_id": "alice",
    "messages": [{"role": "user", "content": "What did I tell you about my preferences?"}]
  }'
# Response: "You told me that you love Python programming and your favorite framework is FastAPI."
```

---

## 🔍 Checking Memory Status

### Verify Context Was Used

Look for `"context_used": true` in the response:

```json
{
  "answer": "Your name is Both",
  "session_id": "d87c64f378f935e1",
  "context_used": true  // ✅ Memory was retrieved and used!
}
```

If `"context_used": false`, the AI is **NOT** using previous conversation context.

---

### Get Conversation History

```bash
curl http://localhost:8000/sessions/d87c64f378f935e1/history?limit=10
```

**Response:**
```json
{
  "session_id": "d87c64f378f935e1",
  "history": [
    {
      "user_message": "My name is Both",
      "ai_response": "Hello Both! Nice to meet you...",
      "timestamp": "2025-11-21T14:22:00"
    },
    {
      "user_message": "What is my name?",
      "ai_response": "Your name is Both, as you mentioned earlier.",
      "timestamp": "2025-11-21T14:23:00"
    }
  ],
  "count": 2
}
```

---

## 💡 Best Practices

### 1. Always Use the Returned Session ID

```javascript
// JavaScript example
let sessionId = null;

async function chat(message) {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,  // Use saved session_id
      user_id: 'john',
      messages: [{ role: 'user', content: message }]
    })
  });

  const data = await response.json();
  sessionId = data.session_id;  // ✅ Update session_id for next request
  return data.answer;
}

// Usage
await chat("My name is Both");     // Creates new session
await chat("What is my name?");    // Uses same session
```

### 2. Store Session ID Persistently

```powershell
# PowerShell example with persistent session
$sessionFile = "session_id.txt"

# First message - create or load session
if (Test-Path $sessionFile) {
    $sessionId = Get-Content $sessionFile
} else {
    $sessionId = $null
}

$response = Invoke-RestMethod -Uri "http://localhost:8000/chat" `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{
        session_id = $sessionId
        user_id = "john"
        messages = @(@{role = "user"; content = "My name is Both"})
    } | ConvertTo-Json)

# Save session_id for next time
$response.session_id | Out-File $sessionFile

Write-Host "AI: $($response.answer)"
Write-Host "Session: $($response.session_id)"
Write-Host "Memory used: $($response.context_used)"
```

### 3. Verify Memory is Working

```bash
# Quick test script
#!/bin/bash

echo "Test 1: Introduce name"
response1=$(curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","messages":[{"role":"user","content":"My name is TestUser"}]}')

session_id=$(echo $response1 | jq -r '.session_id')
echo "Session ID: $session_id"
echo "Response: $(echo $response1 | jq -r '.answer')"

echo ""
echo "Test 2: Ask for name (should remember)"
response2=$(curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$session_id\",\"user_id\":\"test\",\"messages\":[{\"role\":\"user\",\"content\":\"What is my name?\"}]}")

echo "Context used: $(echo $response2 | jq -r '.context_used')"
echo "Response: $(echo $response2 | jq -r '.answer')"

if [ "$(echo $response2 | jq -r '.context_used')" == "true" ]; then
    echo "✅ Memory is working!"
else
    echo "❌ Memory not working - check session_id"
fi
```

---

## 🐛 Troubleshooting

### Problem 1: AI Doesn't Remember Previous Messages

**Symptoms:**
- `"context_used": false` in response
- AI says "I don't know your name"

**Causes:**
1. ❌ Using your own session_id instead of returned one
2. ❌ Not including session_id in subsequent requests
3. ❌ Creating new session each time

**Solution:**
```bash
# ✅ Always use the session_id from the response
# First request
response1=$(curl -s -X POST http://localhost:8000/chat -d '...')
session_id=$(echo $response1 | jq -r '.session_id')

# Second request - USE the saved session_id
curl -X POST http://localhost:8000/chat \
  -d "{\"session_id\":\"$session_id\", ...}"
```

---

### Problem 2: Different Session ID Each Time

**Symptom:**
```json
// Request 1
{"session_id": "abc123"} → Returns: {"session_id": "d87c64f378f935e1"}

// Request 2
{"session_id": "abc123"} → Returns: {"session_id": "f22a886f792fa976"}
// Different session ID!
```

**Cause:** System creates a NEW session if provided session_id doesn't exist

**Solution:**
- Don't provide session_id in first request
- Always use the returned session_id for subsequent requests

```bash
# ✅ CORRECT Pattern
# 1. First request - let system create session
response=$(curl -s -X POST http://localhost:8000/chat -d '{"messages":[...]}')

# 2. Extract session_id
session_id=$(echo $response | jq -r '.session_id')

# 3. Use this session_id for all future requests
curl -X POST http://localhost:8000/chat \
  -d "{\"session_id\":\"$session_id\", \"messages\":[...]}"
```

---

### Problem 3: Memory Not Used (context_used: false)

**Possible Reasons:**

1. **First message in session** - No previous context yet
   - ✅ Normal behavior

2. **Database not created** - Check database exists
   ```bash
   ls backend/data/conversations.db
   ```

3. **Session too old** - Memory only keeps last 5 turns
   - Solution: Check conversation history
   ```bash
   curl http://localhost:8000/sessions/{session_id}/history
   ```

4. **New session created accidentally** - Check session_id matches
   - Compare request session_id with response session_id

---

## 📊 Memory Limits

### Short-Term Memory
- **Turns:** Last 5 conversation turns
- **Size:** Up to 2000 characters
- **Automatic:** Retrieved on every request

### Long-Term Memory (User Facts)
- **Storage:** Unlimited (until cleanup)
- **Persistence:** Stored permanently
- **Manual:** Must be saved explicitly

### Cleanup
- **Auto Cleanup:** Deletes sessions older than 30 days
- **Manual:** Use `/sessions/cleanup?days=30` endpoint

---

## 🚀 Advanced Usage

### Create Session Explicitly

```bash
# Create session first
curl -X POST http://localhost:8000/sessions?user_id=john

# Response: {"session_id": "abc-xyz-123"}

# Use this session_id
curl -X POST http://localhost:8000/chat \
  -d '{"session_id":"abc-xyz-123","messages":[...]}'
```

### Search Past Conversations

```bash
curl "http://localhost:8000/conversations/search?query=Python&user_id=john&limit=5"
```

### Save User Facts (Long-Term Memory)

```bash
curl -X POST http://localhost:8000/memory/facts \
  -d '{
    "fact_key": "favorite_language",
    "fact_value": "Python",
    "fact_type": "preference",
    "user_id": "john",
    "confidence": 1.0
  }'
```

### Get User Facts

```bash
curl "http://localhost:8000/memory/facts?user_id=john"
```

---

## ✅ Quick Reference

### Memory Working Correctly

```json
{
  "answer": "Your name is Both",
  "session_id": "d87c64f378f935e1",  // Same as previous request
  "context_used": true                // ✅ Memory used!
}
```

### Memory NOT Working

```json
{
  "answer": "I don't know your name",
  "session_id": "f22a886f792fa976",  // ⚠️ Different from previous!
  "context_used": false               // ❌ No memory used
}
```

---

## 📝 Summary

### The Golden Rule

**Always use the `session_id` returned by the API, never provide your own!**

```bash
# Step 1: First request (no session_id)
curl -X POST .../chat -d '{"messages":[...]}'
# Returns: {"session_id": "xyz123", ...}

# Step 2: Save this session_id!
export SESSION_ID="xyz123"

# Step 3: Use it in ALL subsequent requests
curl -X POST .../chat -d "{\"session_id\":\"$SESSION_ID\",\"messages\":[...]}"
```

### Verification Checklist

- [ ] Not providing custom session_id in first request
- [ ] Saving session_id from response
- [ ] Using saved session_id in next request
- [ ] Checking `context_used: true` in response
- [ ] Verifying same session_id in request and response

---

**Need help?** Check the full API documentation: [API_GUIDE.md](API_GUIDE.md)
