# API Examples

Practical examples for calling the Mini-AGI Backend API.

## Base URL

```
http://localhost:8000
```

## Authentication

All requests (except `/health`, `/health/live`, `/health/ready`) require an API key:

```bash
curl -H "X-API-Key: dev-key-123456789" http://localhost:8000/endpoint
```

Default API key from `.env`:
- `API_KEYS=dev-key-123456789`

---

## 1. Simple Chat

### Basic Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-123456789" \
  -d '{
    "messages": [
      {"role": "user", "content": [{"type": "text", "text": "Hello!"}]}
    ]
  }'
```

**Response:**
```json
{
  "answer": "Hello! How can I help you today?",
  "events": [],
  "session_id": "abc123def456",
  "context_used": false
}
```

---

## 2. Chat with Memory

The AI remembers previous conversations when you provide a `session_id`.

### First Message (creates session)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-123456789" \
  -d '{
    "user_id": "john",
    "messages": [
      {"role": "user", "content": [{"type": "text", "text": "My name is John"}]}
    ]
  }'
```

**Response:**
```json
{
  "answer": "Nice to meet you, John!",
  "events": [],
  "session_id": "sess_abc123",
  "context_used": false
}
```

### Second Message (uses memory)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-123456789" \
  -d '{
    "session_id": "sess_abc123",
    "user_id": "john",
    "messages": [
      {"role": "user", "content": [{"type": "text", "text": "What is my name?"}]}
    ]
  }'
```

**Response:**
```json
{
  "answer": "Your name is John, as you mentioned earlier.",
  "events": [],
  "session_id": "sess_abc123",
  "context_used": true
}
```

---

## 3. Using Personas

### Get available personas

```bash
curl -H "X-API-Key: dev-key-123456789" \
  http://localhost:8000/personas
```

**Response:**
```json
{
  "personas": [
    {
      "id": "oi-trader",
      "name": "OI Trader",
      "file": "backend/instruction/oi_trader.md",
      "exists": true
    },
    {
      "id": "coder",
      "name": "Coder",
      "file": "backend/instruction/coder.md",
      "exists": true
    },
    {
      "id": "deep-thinking",
      "name": "Deep Thinking",
      "file": "backend/instruction/Ultimate_thinking.md",
      "exists": true
    }
  ]
}
```

### Use a persona in chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-123456789" \
  -d '{
    "persona": "oi-trader",
    "messages": [
      {"role": "user", "content": [{"type": "text", "text": "Analyze BTC trend"}]}
    ]
  }'
```

**Response:**
```json
{
  "answer": "Analyzing BTC price action... [trading analysis response]",
  "events": [],
  "session_id": "sess_trader_123",
  "context_used": false
}
```

---

## 4. Session Management

### Create a new session

```bash
curl -X POST http://localhost:8000/sessions?user_id=alice \
  -H "X-API-Key: dev-key-123456789"
```

**Response:**
```json
{
  "session_id": "sess_xyz789"
}
```

### Get session info

```bash
curl -H "X-API-Key: dev-key-123456789" \
  http://localhost:8000/sessions/sess_xyz789
```

**Response:**
```json
{
  "session_id": "sess_xyz789",
  "user_id": "alice",
  "created_at": "2025-01-14T10:30:00Z",
  "message_count": 5,
  "last_activity": "2025-01-14T10:35:00Z"
}
```

### Get conversation history

```bash
curl -H "X-API-Key: dev-key-123456789" \
  "http://localhost:8000/sessions/sess_xyz789/history?limit=10"
```

**Response:**
```json
{
  "session_id": "sess_xyz789",
  "history": [
    {
      "id": 1,
      "role": "user",
      "content": "Hello, how are you?",
      "timestamp": "2025-01-14T10:30:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "I'm doing well, thank you!",
      "timestamp": "2025-01-14T10:30:05Z"
    },
    {
      "id": 3,
      "role": "user",
      "content": "What can you help me with?",
      "timestamp": "2025-01-14T10:31:00Z"
    },
    {
      "id": 4,
      "role": "assistant",
      "content": "I can help with coding, trading analysis, research, and more...",
      "timestamp": "2025-01-14T10:31:05Z"
    }
  ],
  "count": 4
}
```

---

## 5. Search Conversations

```bash
curl -H "X-API-Key: dev-key-123456789" \
  "http://localhost:8000/conversations/search?query=bitcoin&user_id=john&limit=5"
```

**Response:**
```json
{
  "query": "bitcoin",
  "results": [
    {
      "id": 42,
      "session_id": "sess_john_001",
      "user_id": "john",
      "role": "user",
      "content": "What do you think about bitcoin investing?",
      "timestamp": "2025-01-14T09:15:00Z"
    },
    {
      "id": 43,
      "session_id": "sess_john_001",
      "user_id": "john",
      "role": "assistant",
      "content": "Bitcoin investing requires careful consideration of risk tolerance...",
      "timestamp": "2025-01-14T09:15:10Z"
    }
  ],
  "count": 2
}
```

---

## 6. User Facts (Long-term Memory)

### Save a fact about the user

```bash
curl -X POST "http://localhost:8000/memory/facts?fact_key=preference&fact_value=likes_coffee&user_id=john" \
  -H "X-API-Key: dev-key-123456789"
```

**Response:**
```json
{
  "status": "success",
  "message": "Fact saved"
}
```

### Get user facts

```bash
curl -H "X-API-Key: dev-key-123456789" \
  "http://localhost:8000/memory/facts?user_id=john"
```

**Response:**
```json
{
  "facts": [
    {
      "id": 1,
      "fact_key": "preference",
      "fact_value": "likes_coffee",
      "fact_type": "general",
      "user_id": "john",
      "confidence": 1.0,
      "created_at": "2025-01-14T10:00:00Z"
    },
    {
      "id": 2,
      "fact_key": "skill_level",
      "fact_value": "intermediate_programmer",
      "fact_type": "skill",
      "user_id": "john",
      "confidence": 0.9,
      "created_at": "2025-01-14T10:05:00Z"
    }
  ],
  "count": 2
}
```

---

## 7. Health Checks

### Full health check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "api_version": "v1",
  "components": {
    "llm": {
      "status": "ok",
      "provider": "zai",
      "model": "glm-4.6"
    },
    "cache": {
      "status": "ok",
      "enabled": true,
      "type": "memory"
    },
    "database": {
      "status": "ok",
      "size_mb": 2.5,
      "usage_percent": 12.5
    }
  }
}
```

### Liveness probe

```bash
curl http://localhost:8000/health/live
```

**Response:**
```json
{
  "status": "alive"
}
```

### Readiness probe

```bash
curl http://localhost:8000/health/ready
```

**Response:**
```json
{
  "status": "ready",
  "llm_provider": "zai"
}
```

---

## 8. LLM Info

```bash
curl -H "X-API-Key: dev-key-123456789" \
  http://localhost:8000/llm/info
```

**Response:**
```json
{
  "provider": "zai",
  "model": "glm-4.6",
  "temperature": 0.2,
  "max_tokens": 8000
}
```

---

## 9. Python Example

```python
import requests

API_KEY = "dev-key-123456789"
BASE_URL = "http://localhost:8000"
headers = {"X-API-Key": API_KEY}

# Simple chat
response = requests.post(
    f"{BASE_URL}/chat",
    headers=headers,
    json={
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "Hello!"}]}
        ]
    }
)

print(response.json())
```

---

## 10. JavaScript/Node.js Example

```javascript
const API_KEY = "dev-key-123456789";
const BASE_URL = "http://localhost:8000";

async function chat(message) {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({
      messages: [
        { role: "user", content: [{ type: "text", text: message }] }
      ],
    }),
  });

  return await response.json();
}

// Usage
chat("Hello!").then(console.log);
```

---

## 11. JavaScript/TypeScript with Frontend Framework

### React Example

```tsx
import { useState } from 'react';

const API_KEY = "dev-key-123456789";
const BASE_URL = "http://localhost:8000";

function ChatComponent() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);

  const sendMessage = async () => {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify({
        messages: [
          { role: "user", content: [{ type: "text", text: input }] }
        ],
      }),
    });

    const data = await response.json();
    setMessages([...messages, { role: "user", content: input }, { role: "assistant", content: data.answer }]);
    setInput("");
  };

  return (
    <div>
      <div>
        {messages.map((msg, i) => (
          <p key={i}><strong>{msg.role}:</strong> {msg.content}</p>
        ))}
      </div>
      <input value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}
```

### Vue Example

```vue
<template>
  <div>
    <div v-for="(msg, i) in messages" :key="i">
      <strong>{{ msg.role }}:</strong> {{ msg.content }}
    </div>
    <input v-model="input" @keyup.enter="sendMessage" />
    <button @click="sendMessage">Send</button>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const API_KEY = "dev-key-123456789";
const BASE_URL = "http://localhost:8000";

const input = ref("");
const messages = ref([]);

async function sendMessage() {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({
      messages: [
        { role: "user", content: [{ type: "text", text: input.value }] }
      ],
    }),
  });

  const data = await response.json();
  messages.value.push(
    { role: "user", content: input.value },
    { role: "assistant", content: data.answer }
  );
  input.value = "";
}
</script>
```

---

## Streaming Response (WebSocket)

For real-time streaming, use WebSocket:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: "chat",
    messages: [
      { role: "user", content: [{ type: "text", text: "Hello!" }] }
    ]
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Stream:", data);
};
```

---

## Error Handling

All errors return JSON:

```json
{
  "detail": "Invalid API key"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized (invalid/missing API key)
- `404` - Not Found
- `500` - Server Error

---

## Interactive API Docs

For a complete interactive documentation:

```
http://localhost:8000/docs
```

This Swagger UI allows you to test all endpoints directly from your browser.

---

## Response Format Reference

### ChatResponse

```typescript
{
  answer: string;              // AI response text
  events: Event[];             // Agent orchestration events
  session_id: string;          // Session identifier
  context_used: boolean;       // Whether memory context was used
}
```

### SessionInfo

```typescript
{
  session_id: string;
  user_id: string | null;
  created_at: string;          // ISO 8601 timestamp
  message_count: number;
  last_activity: string;       // ISO 8601 timestamp
}
```

### ConversationHistory

```typescript
{
  session_id: string;
  history: ConversationTurn[];
  count: number;
}
```

### ConversationTurn

```typescript
{
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;           // ISO 8601 timestamp
}
```

### SearchResult

```typescript
{
  query: string;
  results: ConversationTurn[];
  count: number;
}
```

### MemoryFact

```typescript
{
  id: number;
  fact_key: string;            // Unique identifier for the fact
  fact_value: string;          // The fact content
  fact_type: string;           // Type: general, preference, skill, etc.
  user_id: string | null;
  confidence: number;          // 0.0 - 1.0
  created_at: string;          // ISO 8601 timestamp
}
```

### Persona

```typescript
{
  id: string;                  // Persona identifier
  name: string;                // Display name
  file: string;                // Instruction file path
  exists: boolean;             // Whether file exists
}
```

### HealthCheck

```typescript
{
  status: "ok" | "degraded";
  version: string;
  api_version: string;
  components: {
    llm: {
      status: "ok" | "error";
      provider: string;
      model: string;
    };
    cache: {
      status: "ok" | "error";
      enabled: boolean;
      type: string;
    };
    database: {
      status: "ok" | "error";
      size_mb: number;
      usage_percent: number;
    };
  };
}
```

### LlmInfo

```typescript
{
  provider: "zai" | "ollama";
  model: string;
  temperature: number;
  max_tokens: number;
}
```

### ErrorResponse

```typescript
{
  detail: string;              // Error message
}
```
