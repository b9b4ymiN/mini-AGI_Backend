# 🤖 Mini-AGI Backend

**Enterprise-grade AI Agent Orchestration Platform with Conversation Memory**

> A powerful backend system for orchestrating AI agents with multi-provider LLM support, conversation memory, persona system, and tool integration.

---

## ✨ Key Features

- 🧠 **Conversation Memory** - AI remembers previous chats across sessions
- 🎭 **Persona System** - Specialized AI personalities (trading, coding, research)
- 🔌 **Multi-Provider LLM** - Switch between Z.AI and Ollama
- 🤝 **Agent Orchestration** - Intelligent task delegation to specialists
- 🛠️ **Tool Integration** - File I/O, code execution, MCP servers
- 🔍 **Memory Search** - Find past conversations
- 💾 **Database Management** - Auto cleanup and monitoring for Oracle Cloud
- 🐳 **Docker Ready** - One-command deployment

---

## 🚀 Quick Start

### 1. Configure

```bash
cp .env.backend-only.example .env
# Edit .env and add: ZAI_API_KEY=your-key
```

### 2. Start

**Windows:**
```bash
start-backend.bat
```

**Linux/Mac:**
```bash
docker-compose -f docker-compose.backend-only.yml up -d
```

### 3. Test

```bash
curl http://localhost:8000/health
```

**API Docs:** http://localhost:8000/docs

---

## 💬 Quick Examples

### Simple Chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

### With Memory (AI Remembers!)
```bash
# Message 1
curl -X POST http://localhost:8000/chat \
  -d '{"user_id":"john","messages":[{"role":"user","content":"My name is John"}]}'

# Message 2 (use session_id from response)
curl -X POST http://localhost:8000/chat \
  -d '{"session_id":"<session-id>","user_id":"john","messages":[{"role":"user","content":"What is my name?"}]}'

# Response: "Your name is John, as you mentioned earlier."
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[API_GUIDE.md](API_GUIDE.md)** | Complete API reference & all examples |
| **[MEMORY_SYSTEM.md](MEMORY_SYSTEM.md)** | Memory system detailed guide |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Deployment options |

**Interactive Docs:** http://localhost:8000/docs

---

## 📡 API Endpoints

### Core
- `GET /health` - Health check
- `POST /chat` - Main chat with memory
- `GET /personas` - Available personas
- `GET /llm/info` - LLM configuration

### Memory
- `POST /sessions` - Create session
- `GET /sessions/{id}/history` - Get history
- `GET /conversations/search` - Search conversations
- `POST /memory/facts` - Save user facts
- `DELETE /sessions/cleanup` - Cleanup old data

### Database Management (Oracle Cloud)
- `GET /db/size` - Check database size
- `GET /db/status` - Check size limits
- `POST /db/cleanup/auto` - Auto cleanup
- `POST /db/archive` - Archive old data
- `POST /db/optimize` - Optimize database

**Full API Reference:** [API_GUIDE.md](API_GUIDE.md)

---

## 🎯 What Makes It Smart?

1. **Remembers Context** - Keeps last 5 conversation turns
2. **Learns About Users** - Stores preferences and facts
3. **Searches History** - Find past discussions
4. **Specialized Personas** - Domain-specific experts
5. **Agent Coordination** - Delegates to best specialist
6. **Tool Execution** - File ops, code running

---

## 🔧 Configuration

```bash
# .env file
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
ZAI_API_KEY=your-key
CORS_ORIGINS=http://localhost:3000
```

---

## 🐳 Deployment

```bash
# Backend only (recommended)
docker-compose -f docker-compose.backend-only.yml up -d

# With Ollama
docker-compose up -d
docker exec -it ollama ollama pull llama3.1:8b
```

---

## 📊 Architecture

```
FastAPI Backend
├── Memory System (SQLite)
├── Persona System
├── Agent Orchestrator
│   ├── Coder
│   └── Researcher
└── LLM Provider (Z.AI/Ollama)
```

---

## 🎉 What's New in v2.0

✅ Conversation memory system
✅ Persona support
✅ Long-term user facts
✅ Session management
✅ Conversation search
✅ Multi-provider LLM
✅ Database size management (Oracle Cloud Free Tier)

---

**Get Started:** See [API_GUIDE.md](API_GUIDE.md) for complete documentation! 🚀
