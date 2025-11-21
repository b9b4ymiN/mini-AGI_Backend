# 🚀 Mini-AGI Backend - Complete API Guide

**Version:** 2.0
**Last Updated:** 2025-11-21

Complete guide for using the Mini-AGI Backend API with conversation memory, personas, and multi-provider LLM support.

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Features](#features)
- [Deployment](#deployment)
- [Examples](#examples)
- [Best Practices](#best-practices)

---

## 🎯 Quick Start

### Prerequisites

- **Docker Desktop** (running)
- **Z.AI API Key** OR **Ollama** (local/remote)

### 1. Configure Environment

```bash
# Copy environment template
cp .env.backend-only.example .env

# Edit .env - Add your Z.AI API key
nano .env
```

**For Z.AI (Recommended - No Ollama needed):**
```bash
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
ZAI_API_KEY=your-api-key-here
```

### 2. Start Backend

**Windows:**
```bash
start-backend.bat
```

**Linux/Mac:**
```bash
docker-compose -f docker-compose.backend-only.yml up -d
```

### 3. Test API

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

**API Documentation:** http://localhost:8000/docs

---

## 📡 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/llm/info` | GET | LLM configuration info |
| `/personas` | GET | Available personas |
| `/chat` | POST | Main chat endpoint with memory |

### Memory Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions` | POST | Create new session |
| `/sessions/{id}` | GET | Get session info |
| `/sessions/{id}/history` | GET | Get conversation history |
| `/conversations/search` | GET | Search conversations |
| `/memory/facts` | POST | Save user fact |
| `/memory/facts` | GET | Get user facts |
| `/sessions/cleanup` | DELETE | Cleanup old sessions |

### Database Management Endpoints (Oracle Cloud Free Tier)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/db/size` | GET | Get database size and usage |
| `/db/stats` | GET | Detailed database statistics |
| `/db/status` | GET | Check size limits status |
| `/db/cleanup/auto` | POST | Auto cleanup if needed |
| `/db/archive` | POST | Archive old conversations |
| `/db/vacuum` | POST | Reclaim unused space |
| `/db/optimize` | POST | Optimize database |
| `/db/recommendations` | GET | Get storage recommendations |

---

## 🎯 Features

### 1. Conversation Memory

The AI remembers previous conversations using session IDs.

**How it works:**
- Each conversation gets a unique `session_id`
- AI automatically retrieves last 5 turns
- Context is injected into agent prompts
- All messages saved to SQLite database

### 2. Personas

Pre-configured AI personalities with specialized instructions.

**Available personas:**
- `oi-trader` - Professional trading analysis (Thai language)

### 3. Multi-Provider LLM

Switch between different LLM providers:
- **Z.AI** - Cloud API (recommended)
- **Ollama** - Local or remote server

### 4. Agent System

- **Orchestrator** - Main coordinator
- **Coder** - Programming specialist
- **Researcher** - Information analyst

---

## 💬 Chat Endpoint

### Basic Usage

```http
POST /chat
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ]
}
```

**Response:**
```json
{
  "answer": "Hi! How can I help you?",
  "session_id": "abc123",
  "context_used": false,
  "events": [...]
}
```

### With Memory (Multi-turn Conversation)

**Turn 1:**
```json
{
  "user_id": "john",
  "messages": [
    {
      "role": "user",
      "content": "My name is John"
    }
  ]
}
```

**Response:**
```json
{
  "answer": "Nice to meet you, John!",
  "session_id": "abc123",  ← Save this!
  "context_used": false
}
```

**Turn 2 (AI remembers):**
```json
{
  "session_id": "abc123",
  "user_id": "john",
  "messages": [
    {
      "role": "user",
      "content": "What's my name?"
    }
  ]
}
```

**Response:**
```json
{
  "answer": "Your name is John, as you mentioned earlier.",
  "session_id": "abc123",
  "context_used": true  ← Memory was used!
}
```

### With Persona

```json
{
  "persona": "oi-trader",
  "user_id": "trader001",
  "messages": [
    {
      "role": "user",
      "content": "Analyze SPY: price $450, POC $448, Call OI 50k, Put OI 30k"
    }
  ]
}
```

**Response:** Professional Thai trading analysis using 5-Pillar framework.

### With Custom System Instruction

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant. Be concise."
    },
    {
      "role": "user",
      "content": "Explain APIs"
    }
  ]
}
```

### Complete Example (All Features)

```json
{
  "session_id": "abc123",
  "user_id": "john",
  "persona": "oi-trader",
  "messages": [
    {
      "role": "system",
      "content": "Additional instructions..."
    },
    {
      "role": "user",
      "content": "Your question here"
    }
  ]
}
```

**Priority:** persona > system message > default

---

## 🧠 Memory System

### Session Management

#### Create Session
```bash
curl -X POST "http://localhost:8000/sessions?user_id=john"
```

**Response:**
```json
{
  "session_id": "abc123"
}
```

#### Get Session Info
```bash
curl "http://localhost:8000/sessions/abc123"
```

**Response:**
```json
{
  "session_id": "abc123",
  "created_at": "2025-11-21T10:00:00",
  "last_activity": "2025-11-21T10:15:00",
  "message_count": 5
}
```

#### Get History
```bash
curl "http://localhost:8000/sessions/abc123/history?limit=10"
```

**Response:**
```json
{
  "session_id": "abc123",
  "history": [
    {
      "id": 1,
      "timestamp": "2025-11-21T10:00:00",
      "user_message": "My name is John",
      "ai_response": "Nice to meet you, John!",
      "persona": null
    }
  ],
  "count": 1
}
```

### Search Conversations

```bash
curl "http://localhost:8000/conversations/search?query=trading&user_id=john&limit=5"
```

### Memory Facts (Long-term Learning)

#### Save Fact
```bash
curl -X POST "http://localhost:8000/memory/facts" \
  -H "Content-Type: application/json" \
  -d '{
    "fact_key": "preferred_language",
    "fact_value": "Thai",
    "fact_type": "preference",
    "user_id": "john",
    "confidence": 1.0
  }'
```

#### Get Facts
```bash
curl "http://localhost:8000/memory/facts?user_id=john"
```

**Response:**
```json
{
  "facts": [
    {
      "fact_key": "preferred_language",
      "fact_value": "Thai",
      "fact_type": "preference",
      "confidence": 1.0
    }
  ],
  "count": 1
}
```

### Cleanup Old Sessions

```bash
curl -X DELETE "http://localhost:8000/sessions/cleanup?days=30"
```

---

## 🎭 Personas

### List Available Personas

```bash
curl "http://localhost:8000/personas"
```

**Response:**
```json
{
  "personas": [
    {
      "id": "oi-trader",
      "name": "Oi Trader",
      "file": "AI_System_Instructions_Trading_Analysis.md",
      "exists": true
    }
  ]
}
```

### Using Personas

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "persona": "oi-trader",
    "messages": [{
      "role": "user",
      "content": "Analyze BTC price action"
    }]
  }'
```

### Adding New Personas

1. **Create instruction file:**
   ```
   backend/instruction/my-persona.md
   ```

2. **Register in personas.py:**
   ```python
   PERSONA_REGISTRY = {
       "oi-trader": "AI_System_Instructions_Trading_Analysis.md",
       "my-persona": "my-persona.md"  # Add this
   }
   ```

3. **Restart backend**

---

## 🔧 Configuration

### Environment Variables

**LLM Provider:**
```bash
LLM_PROVIDER=zai              # or "ollama"
LLM_MODEL=glm-4.6             # Model name
LLM_TEMPERATURE=0.2           # 0.0-1.0
```

**Z.AI:**
```bash
ZAI_API_KEY=your-key
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

**Ollama:**
```bash
OLLAMA_URL=http://localhost:11434
# For Docker: http://host.docker.internal:11434
# For remote: http://your-server:11434
```

**Application:**
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
MAX_ORCHESTRATION_STEPS=10
```

### Get Current Configuration

```bash
curl "http://localhost:8000/llm/info"
```

**Response:**
```json
{
  "provider": "zai",
  "model": "glm-4.6",
  "temperature": "0.2",
  "zai_api_key_set": "Yes"
}
```

---

## 📝 Complete Examples

### Example 1: Simple Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": "What is FastAPI?"
    }]
  }'
```

### Example 2: Multi-turn Conversation

```bash
# Turn 1
RESPONSE=$(curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","messages":[{"role":"user","content":"I like Python"}]}')

# Extract session_id
SESSION_ID=$(echo $RESPONSE | jq -r '.session_id')

# Turn 2
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"user_id\":\"alice\",\"messages\":[{\"role\":\"user\",\"content\":\"What do I like?\"}]}"

# Response: "You mentioned that you like Python."
```

### Example 3: Trading Analysis with Persona

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "persona": "oi-trader",
    "user_id": "trader001",
    "messages": [{
      "role": "user",
      "content": "Analyze: SPY $450, POC $448, Call OI 50000, Put OI 30000"
    }]
  }'
```

### Example 4: Personalized Conversation

```bash
# Save preference
curl -X POST http://localhost:8000/memory/facts \
  -H "Content-Type: application/json" \
  -d '{
    "fact_key": "expertise",
    "fact_value": "machine learning",
    "fact_type": "skill",
    "user_id": "bob"
  }'

# Chat (AI knows about expertise)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "bob",
    "messages": [{
      "role": "user",
      "content": "Suggest a project for me"
    }]
  }'

# Response will be tailored to ML expertise
```

### Example 5: PowerShell (Windows)

```powershell
# First message
$response1 = Invoke-RestMethod -Uri "http://localhost:8000/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"user_id":"test","messages":[{"role":"user","content":"My name is John"}]}'

Write-Host "Session ID: $($response1.session_id)"

# Second message
$response2 = Invoke-RestMethod -Uri "http://localhost:8000/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body "{`"session_id`":`"$($response1.session_id)`",`"user_id`":`"test`",`"messages`":[{`"role`":`"user`",`"content`":`"What's my name?`"}]}"

Write-Host "Answer: $($response2.answer)"
Write-Host "Context used: $($response2.context_used)"
```

---

## 🚀 Deployment

### Development

```bash
# Using batch script (Windows)
start-backend.bat

# Using Docker Compose
docker-compose -f docker-compose.backend-only.yml up -d

# View logs
docker-compose -f docker-compose.backend-only.yml logs -f
```

### Production

```bash
# Build and start
docker-compose -f docker-compose.backend-only.yml up -d --build

# Check status
docker-compose -f docker-compose.backend-only.yml ps

# View logs
docker-compose -f docker-compose.backend-only.yml logs --tail=100
```

### Stop

```bash
docker-compose -f docker-compose.backend-only.yml down
```

---

## ✅ Best Practices

### For API Consumers

1. **Always save session_id** - Required for conversation continuity
2. **Use user_id consistently** - Enables personalization across sessions
3. **Handle errors gracefully** - Check response status codes
4. **Respect rate limits** - Don't spam requests
5. **Clean up old sessions** - Periodically call `/sessions/cleanup`

### Session Management

```javascript
// Frontend example (JavaScript)
class MiniAGIClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.sessionId = null;
    this.userId = 'user_' + Math.random().toString(36).substr(2, 9);
  }

  async chat(message, persona = null) {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: this.sessionId,
        user_id: this.userId,
        persona: persona,
        messages: [{
          role: 'user',
          content: message
        }]
      })
    });

    const data = await response.json();

    // Save session ID for next request
    this.sessionId = data.session_id;

    return data;
  }

  newSession() {
    this.sessionId = null;
  }
}

// Usage
const client = new MiniAGIClient();

// First message
const response1 = await client.chat('My name is Alice');
console.log(response1.answer);

// Second message (remembers context)
const response2 = await client.chat('What is my name?');
console.log(response2.answer); // "Your name is Alice"
```

### Memory Management

1. **Limit context** - Default is 5 turns, 2000 chars (configurable)
2. **Cleanup regularly** - Run cleanup monthly
3. **Monitor database** - Check size of `backend/data/conversations.db`
4. **Backup important sessions** - Export before cleanup

### Database Size Management (Oracle Cloud Free Tier)

**Important for Oracle Cloud deployments** - The free tier has storage limits. Use these endpoints to monitor and manage database size.

#### Check Database Size

```bash
curl http://localhost:8000/db/size
```

**Response:**
```json
{
  "size_mb": 2.45,
  "max_size_mb": 100,
  "usage_percent": 2.45,
  "status": "ok"
}
```

#### Check Database Status

```bash
curl http://localhost:8000/db/status
```

**Response:**
```json
{
  "status": "ok",
  "size_mb": 2.45,
  "max_size_mb": 100,
  "usage_percent": 2.45,
  "message": "Database size is healthy"
}
```

**Statuses:**
- `ok` - Under 80% capacity
- `warning` - 80-100% capacity (action recommended)
- `critical` - Over 100% capacity (immediate action required)

#### Get Detailed Statistics

```bash
curl http://localhost:8000/db/stats
```

**Response:**
```json
{
  "size_mb": 2.45,
  "total_conversations": 1250,
  "total_sessions": 85,
  "total_facts": 42,
  "oldest_conversation": "2025-01-15T10:30:00",
  "newest_conversation": "2025-11-21T14:22:00",
  "avg_conversations_per_session": 14.7
}
```

#### Auto Cleanup (Recommended)

Automatically cleans up based on current database status:

```bash
curl -X POST http://localhost:8000/db/cleanup/auto
```

**Response:**
```json
{
  "action_taken": "normal_cleanup",
  "deleted_conversations": 180,
  "deleted_sessions": 12,
  "size_before_mb": 85.3,
  "size_after_mb": 72.1,
  "space_freed_mb": 13.2,
  "status": "ok"
}
```

**Cleanup Levels:**
- **Normal (warning)** - Deletes data older than 30 days
- **Aggressive (critical)** - Deletes data older than 7 days
- **None (ok)** - No action taken

#### Archive Old Conversations

Archive conversations to compressed file before deletion:

```bash
# Archive conversations older than 90 days
curl -X POST "http://localhost:8000/db/archive?days=90&compress=true"
```

**Response:**
```json
{
  "status": "success",
  "archive_file": "backend/data/archive_2025-11-21_142230.json.gz",
  "conversations_archived": 450,
  "sessions_archived": 28,
  "compression_ratio": "87%",
  "original_size_mb": 3.2,
  "compressed_size_mb": 0.4,
  "conversations_deleted": 450
}
```

#### Vacuum Database (Reclaim Space)

After deleting data, run VACUUM to reclaim disk space:

```bash
curl -X POST http://localhost:8000/db/vacuum
```

**Response:**
```json
{
  "status": "success",
  "size_before_mb": 45.8,
  "size_after_mb": 32.1,
  "space_freed_mb": 13.7,
  "freed_percent": 29.9
}
```

#### Optimize Database

Run full optimization (VACUUM, ANALYZE, REINDEX):

```bash
curl -X POST http://localhost:8000/db/optimize
```

**Response:**
```json
{
  "status": "success",
  "vacuum": {
    "size_before_mb": 45.8,
    "size_after_mb": 32.1,
    "space_freed_mb": 13.7
  },
  "analyze_complete": true,
  "reindex_complete": true,
  "optimization_time_seconds": 2.3
}
```

#### Get Storage Recommendations

Get actionable recommendations based on current database state:

```bash
curl http://localhost:8000/db/recommendations
```

**Response:**
```json
{
  "status": "warning",
  "recommendations": [
    {
      "priority": "high",
      "action": "Run auto cleanup",
      "reason": "Database is at 85% capacity",
      "command": "POST /db/cleanup/auto"
    },
    {
      "priority": "medium",
      "action": "Archive old conversations",
      "reason": "450 conversations older than 90 days",
      "command": "POST /db/archive?days=90"
    },
    {
      "priority": "low",
      "action": "Vacuum database",
      "reason": "Can reclaim ~13MB of space",
      "command": "POST /db/vacuum"
    }
  ]
}
```

#### Best Practices for Oracle Cloud Free Tier

1. **Monitor regularly** - Check `/db/size` weekly
2. **Enable auto cleanup** - Run `/db/cleanup/auto` in cron job
3. **Archive before cleanup** - Use `/db/archive` to save old data
4. **Vacuum after cleanup** - Reclaim disk space with `/db/vacuum`
5. **Set up alerts** - Monitor when usage exceeds 80%

**Example Maintenance Script (PowerShell):**
```powershell
# Weekly maintenance script
$apiUrl = "http://localhost:8000"

# Check status
$status = Invoke-RestMethod -Uri "$apiUrl/db/status"
Write-Host "Database Status: $($status.status)"

# Auto cleanup if needed
if ($status.status -ne "ok") {
    $result = Invoke-RestMethod -Uri "$apiUrl/db/cleanup/auto" -Method POST
    Write-Host "Cleanup: Freed $($result.space_freed_mb) MB"
}

# Vacuum to reclaim space
$vacuum = Invoke-RestMethod -Uri "$apiUrl/db/vacuum" -Method POST
Write-Host "Vacuum: Freed $($vacuum.space_freed_mb) MB"
```

**Example Maintenance Script (Bash):**
```bash
#!/bin/bash
# Weekly maintenance script
API_URL="http://localhost:8000"

# Check status
status=$(curl -s "$API_URL/db/status")
echo "Database Status: $(echo $status | jq -r '.status')"

# Auto cleanup if needed
if [ "$(echo $status | jq -r '.status')" != "ok" ]; then
    result=$(curl -s -X POST "$API_URL/db/cleanup/auto")
    echo "Cleanup: Freed $(echo $result | jq -r '.space_freed_mb') MB"
fi

# Vacuum to reclaim space
vacuum=$(curl -s -X POST "$API_URL/db/vacuum")
echo "Vacuum: Freed $(echo $vacuum | jq -r '.space_freed_mb') MB"
```

### Error Handling

```python
import requests

def chat_with_retry(message, session_id=None, max_retries=3):
    """Chat with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                'http://localhost:8000/chat',
                json={
                    'session_id': session_id,
                    'messages': [{'role': 'user', 'content': message}]
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            print(f"Retry {attempt + 1}/{max_retries}")
            time.sleep(2 ** attempt)  # Exponential backoff
```

---

## 🐛 Troubleshooting

### Issue: Can't connect to backend

**Error:** `Connection refused`

**Solutions:**
1. Check if Docker is running: `docker ps`
2. Check if backend is running: `curl http://localhost:8000/health`
3. Check logs: `docker-compose logs backend`

### Issue: AI doesn't remember previous messages

**Problem:** `context_used: false`

**Solutions:**
1. **Check you're using session_id** in subsequent requests
2. View session history: `curl http://localhost:8000/sessions/{session_id}/history`
3. Check database exists: `ls backend/data/conversations.db`

### Issue: LLM provider errors

**Error:** `Failed to call Z.AI: 401 Unauthorized`

**Solutions:**
1. Check API key in .env: `grep ZAI_API_KEY .env`
2. Restart backend: `docker-compose restart`
3. Verify provider: `curl http://localhost:8000/llm/info`

### Issue: Persona not found

**Error:** `Unknown persona: 'my-persona'`

**Solutions:**
1. Check personas: `curl http://localhost:8000/personas`
2. Verify file exists: `ls backend/instruction/`
3. Check registry in `backend/orchestrator/personas.py`
4. Restart backend

---

## 📊 Performance

### Response Times

| Operation | Average Time |
|-----------|-------------|
| Health check | ~5ms |
| Simple chat | ~1-3s |
| Chat with memory | ~1-4s |
| Session history | ~10ms |
| Search conversations | ~50ms |

### Database

- **Storage:** ~500 bytes per message turn
- **1000 turns:** ~500 KB
- **10,000 turns:** ~5 MB
- **Performance:** Indexed, <50ms queries

### Resource Usage

**Backend Only:**
- CPU: 0.5-1 core
- RAM: 512 MB - 2 GB
- Disk: ~500 MB + conversations DB

---

## 🔐 Security

### API Security

1. **No authentication** - Add authentication for production
2. **CORS configured** - Only specified origins allowed
3. **Input validation** - Pydantic models validate requests
4. **SQL injection safe** - Parameterized queries

### Data Privacy

1. **User data stored** - Conversations saved in database
2. **No encryption** - Database is plain SQLite
3. **User consent** - Inform users about data storage
4. **GDPR compliance** - Provide export/delete endpoints

### Production Recommendations

1. Add authentication (JWT, API keys)
2. Enable HTTPS (reverse proxy)
3. Encrypt database at rest
4. Implement rate limiting
5. Add request logging
6. Monitor for abuse

---

## 📚 Additional Resources

### Documentation Files

- **API_GUIDE.md** - This file (complete reference)
- **MEMORY_SYSTEM.md** - Detailed memory system docs
- **README.md** - Project overview

### API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Support

- **Issues:** Report bugs on GitHub
- **Questions:** Check documentation first
- **Examples:** See `/examples` in repository

---

## 🎉 Summary

**Your Mini-AGI Backend provides:**

✅ **Conversation Memory** - AI remembers previous chats
✅ **Personas** - Specialized AI personalities
✅ **Multi-Provider LLM** - Switch between Z.AI/Ollama
✅ **Agent System** - Orchestrator, Coder, Researcher
✅ **Session Management** - Track conversations
✅ **Long-term Learning** - Store user facts
✅ **Search** - Find past conversations
✅ **RESTful API** - Easy integration
✅ **Docker Ready** - Easy deployment

**Get started:** http://localhost:8000/docs

---

**Version:** 2.0
**Updated:** 2025-11-21
**License:** MIT
