# ⚡ Quick Start - Backend Only (No Ollama)

**Get your backend running in 3 steps!**

---

## 🎯 For Z.AI Users (Recommended)

### Step 1: Configure

```bash
# Copy environment template
cp .env.backend-only.example .env
```

Edit `.env` and add your Z.AI API key:
```bash
ZAI_API_KEY=your-actual-api-key-here
```

### Step 2: Start

**Windows:**
```bash
start-backend.bat
```

**Linux/Mac:**
```bash
docker-compose -f docker-compose.backend-only.yml up -d
```

### Step 3: Test

```bash
curl http://localhost:8000/health
```

**Done! ✅** Your backend is running at http://localhost:8000

---

## 🎯 For Ollama Users (Host Machine)

### Step 1: Start Ollama

```bash
# In a separate terminal
ollama serve
```

### Step 2: Configure

```bash
# Copy environment template
cp .env.backend-only.example .env
```

Edit `.env`:
```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_URL=http://host.docker.internal:11434
```

### Step 3: Start Backend

**Windows:**
```bash
start-backend.bat
```

**Linux/Mac:**
```bash
docker-compose -f docker-compose.backend-only.yml up -d
```

### Step 4: Test

```bash
curl http://localhost:8000/health
```

**Done! ✅**

---

## 📝 Available Commands

### Windows Users

```bash
start-backend.bat          # Start
start-backend.bat stop     # Stop
start-backend.bat logs     # View logs
start-backend.bat test     # Test endpoints
start-backend.bat restart  # Restart
```

### Linux/Mac Users

```bash
# Start
docker-compose -f docker-compose.backend-only.yml up -d

# Stop
docker-compose -f docker-compose.backend-only.yml down

# Logs
docker-compose -f docker-compose.backend-only.yml logs -f

# Restart
docker-compose -f docker-compose.backend-only.yml restart

# Rebuild
docker-compose -f docker-compose.backend-only.yml up -d --build
```

---

## 🧪 Test Your Backend

### Quick Test

```bash
# Health
curl http://localhost:8000/health

# LLM Info
curl http://localhost:8000/llm/info

# Personas
curl http://localhost:8000/personas
```

### Full Test (Windows)

```bash
start-backend.bat test
```

### Test Chat with Persona

```bash
curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"persona\":\"oi-trader\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}"
```

---

## 📚 API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **LLM Info:** http://localhost:8000/llm/info
- **Personas:** http://localhost:8000/personas

---

## 🐛 Common Issues

### Docker not running

**Error:** `Cannot connect to Docker daemon`

**Fix:** Start Docker Desktop

---

### Can't connect to Z.AI

**Error:** `401 Unauthorized`

**Fix:** Check `ZAI_API_KEY` in `.env` file

---

### Can't connect to host Ollama

**Error:** `Connection refused`

**Fix:**
1. Make sure Ollama is running: `ollama serve`
2. Check `.env`: `OLLAMA_URL=http://host.docker.internal:11434`

---

## 📖 More Documentation

- **Full Guide:** [BACKEND_ONLY_DEPLOYMENT.md](BACKEND_ONLY_DEPLOYMENT.md)
- **Troubleshooting:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Docs:** http://localhost:8000/docs

---

**Need help?** Check [BACKEND_ONLY_DEPLOYMENT.md](BACKEND_ONLY_DEPLOYMENT.md) for detailed instructions.
