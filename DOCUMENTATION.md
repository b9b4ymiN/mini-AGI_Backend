# 📚 Documentation Overview

Complete guide to Mini-AGI Backend documentation.

---

## 📋 Available Documentation

### 1. **README.md** (Start Here!)
**Quick overview and getting started**

- Project overview
- Quick start guide
- Basic examples
- Architecture diagram
- Links to detailed docs

**Use when:** You're new to the project

---

### 2. **API_GUIDE.md** (Main Reference)
**Complete API documentation and examples**

- All API endpoints
- Request/response formats
- Complete usage examples
- Best practices
- Troubleshooting
- JavaScript/PowerShell examples

**Use when:** You need to integrate with the API

**Covers:**
- Chat endpoint (with memory, personas, system instructions)
- Memory management endpoints
- Session management
- Conversation search
- User facts (long-term learning)
- Configuration
- Error handling

---

### 3. **MEMORY_SYSTEM.md** (Deep Dive)
**Detailed memory system architecture**

- Memory architecture
- Database schema
- Short-term vs long-term memory
- Context retrieval algorithms
- Performance optimization
- Advanced configuration

**Use when:** You want to understand or customize the memory system

---

### 4. **DEPLOYMENT.md** (Full Setup)
**Complete deployment guide with Ollama**

- Prerequisites
- Full deployment options
- With Ollama container
- Production configuration
- GPU support
- Monitoring
- Backup strategies

**Use when:** You want to deploy with Ollama or need production setup

---

## 🎯 Quick Navigation

### I want to...

**Get started quickly**
→ Start with **README.md** then **API_GUIDE.md**

**Integrate the API**
→ Read **API_GUIDE.md** (has all examples)

**Understand memory system**
→ Read **MEMORY_SYSTEM.md**

**Deploy with Ollama**
→ Read **DEPLOYMENT.md**

**Deploy with Z.AI only**
→ Read **API_GUIDE.md** (Deployment section)

**Add custom personas**
→ See **API_GUIDE.md** (Personas section)

**Debug issues**
→ Check **API_GUIDE.md** (Troubleshooting section)

---

## 📡 Live Documentation

When backend is running:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health:** http://localhost:8000/health

---

## 🔍 Documentation Map

```
README.md (Overview)
    ├─► API_GUIDE.md (Main Reference)
    │       ├─► Quick Start
    │       ├─► All Endpoints
    │       ├─► Examples
    │       ├─► Best Practices
    │       └─► Troubleshooting
    │
    ├─► MEMORY_SYSTEM.md (Memory Details)
    │       ├─► Architecture
    │       ├─► Database Schema
    │       └─► Advanced Config
    │
    └─► DEPLOYMENT.md (Full Deployment)
            ├─► With Ollama
            ├─► Production Setup
            └─► Monitoring
```

---

## 📝 File Sizes

| File | Size | Purpose |
|------|------|---------|
| README.md | 3.7 KB | Quick overview |
| API_GUIDE.md | 18 KB | Complete API reference |
| MEMORY_SYSTEM.md | 12 KB | Memory system guide |
| DEPLOYMENT.md | 12 KB | Full deployment guide |

---

## ✅ What Each Document Contains

### README.md
- ✅ Features list
- ✅ Quick start (3 steps)
- ✅ Basic examples
- ✅ Architecture diagram
- ✅ Documentation links

### API_GUIDE.md
- ✅ All API endpoints
- ✅ Request/response formats
- ✅ Complete examples (curl, PowerShell, JavaScript)
- ✅ Chat with memory
- ✅ Personas
- ✅ Session management
- ✅ Search
- ✅ Configuration
- ✅ Best practices
- ✅ Troubleshooting
- ✅ Performance metrics

### MEMORY_SYSTEM.md
- ✅ Memory architecture
- ✅ Database schema (3 tables)
- ✅ Memory flow diagram
- ✅ Short-term vs long-term memory
- ✅ Context retrieval
- ✅ Fact storage
- ✅ Search capabilities
- ✅ Performance tuning

### DEPLOYMENT.md
- ✅ Full deployment options
- ✅ With Ollama container
- ✅ Production setup
- ✅ GPU support
- ✅ Reverse proxy (Nginx)
- ✅ SSL/HTTPS
- ✅ Monitoring
- ✅ Backup strategies

---

## 🎓 Learning Path

**Beginner:**
1. Read README.md
2. Follow Quick Start
3. Test simple chat example

**Intermediate:**
1. Read API_GUIDE.md sections:
   - Chat endpoint
   - Memory management
   - Personas
2. Try multi-turn conversation
3. Test session management

**Advanced:**
1. Read MEMORY_SYSTEM.md
2. Understand database schema
3. Customize memory parameters
4. Read DEPLOYMENT.md for production

---

## 🔗 External Resources

- **Swagger UI:** Interactive API testing
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Z.AI:** https://z.ai
- **Ollama:** https://ollama.ai

---

## 💡 Tips

1. **Start small** - Test simple chat first
2. **Use Swagger UI** - Best for exploring API
3. **Check examples** - API_GUIDE.md has many
4. **Read troubleshooting** - Common issues covered
5. **Check version** - Docs are versioned

---

## 🆘 Getting Help

1. **Check API_GUIDE.md** first (most comprehensive)
2. **Use Swagger UI** for endpoint details
3. **Read error messages** - Usually self-explanatory
4. **Check logs** - `docker-compose logs`
5. **Verify config** - `/llm/info` endpoint

---

**Quick Start:** [README.md](README.md)
**Complete Reference:** [API_GUIDE.md](API_GUIDE.md)
**Interactive Docs:** http://localhost:8000/docs

---

**All documentation is up to date as of v2.0 (2025-11-21)**
