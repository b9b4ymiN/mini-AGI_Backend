# Getting Started

A simple guide to get the Mini-AGI Backend running on your machine.

## Prerequisites

- Docker installed (or Python 3.10+ for local development)
- API key for Z.AI or access to Ollama

---

## Quick Start (5 minutes)

### Option 1: Using Z.AI Cloud API (Recommended)

1. **Copy the example environment file**

   ```bash
   cp .env.backend-only.example .env
   ```

2. **Edit `.env` and add your API key**

   ```env
   LLM_PROVIDER=zai
   LLM_MODEL=glm-4.6
   ZAI_API_KEY=your-actual-api-key-here
   ```

3. **Start the backend**

   **Windows:**
   ```bash
   start-backend.bat
   ```

   **Linux/Mac:**
   ```bash
   docker-compose -f docker-compose.backend-only.yml up -d
   ```

4. **Test the API**

   ```bash
   curl http://localhost:8000/health
   ```

   You should see:
   ```json
   {"status":"ok","version":"1.0.0"}
   ```

---

### Option 2: Using Local Ollama

1. **Copy the example environment file**

   ```bash
   cp .env.backend-only.example .env
   ```

2. **Edit `.env` to use Ollama**

   ```env
   LLM_PROVIDER=ollama
   LLM_MODEL=llama3.1:8b
   OLLAMA_URL=http://host.docker.internal:11434
   ```

3. **Start with Docker Compose (includes Ollama)**

   ```bash
   docker-compose up -d
   ```

4. **Pull the model (first time only)**

   ```bash
   docker exec -it ollama ollama pull llama3.1:8b
   ```

---

## Verify Installation

Once the backend is running:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "api_version": "v1",
  "components": {
    "llm": { "status": "ok", "provider": "zai", "model": "glm-4.6" },
    "cache": { "status": "ok" },
    "database": { "status": "ok" }
  }
}
```

---

## View API Documentation

Open your browser:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Common Issues

### Port 8000 already in use
Change the port in `.env`:
```env
BACKEND_PORT=8001
```

### Docker permission error (Linux)
```bash
sudo usermod -aG docker $USER
# Then log out and back in
```

### Ollama connection error
Make sure OLLAMA_URL is correct:
- Docker Compose: `http://ollama:11434`
- Host Ollama: `http://host.docker.internal:11434`

---

## Next Steps

- Read [API_EXAMPLES.md](API_EXAMPLES.md) for usage examples
- Read [MEMORY_USAGE_GUIDE.md](MEMORY_USAGE_GUIDE.md) for memory system
- Read [API_GUIDE.md](API_GUIDE.md) for complete API reference
