# 🐳 Docker Deployment - Quick Reference

This section provides quick Docker deployment commands. For complete documentation, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 🚀 Quick Start with Docker

### Option 1: Docker Compose (Recommended)

**Development:**
```bash
# Start all services (backend + Ollama)
docker-compose up -d

# Pull Ollama model
docker exec -it ollama ollama pull llama3.1:8b

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Production:**
```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Pull model
docker exec -it ollama-prod ollama pull llama3.1:8b

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Option 2: Makefile Commands

```bash
# Development
make dev            # Start dev environment
make pull-model     # Pull Ollama model
make test           # Test API endpoints
make logs           # View logs
make stop           # Stop services

# Production
make prod           # Start prod environment
make health         # Check health
make status         # Show status
make clean          # Clean up
```

### Option 3: Deployment Script

```bash
# Make script executable (Linux/Mac)
chmod +x deploy.sh

# Deploy
./deploy.sh dev      # Development
./deploy.sh prod     # Production
./deploy.sh logs     # View logs
./deploy.sh status   # Check status
```

---

## 📝 Configuration

### 1. Create .env file

```bash
cp .env.example .env
```

### 2. Edit .env

**For Ollama (local):**
```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_URL=http://ollama:11434
```

**For Z.AI (cloud):**
```bash
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
ZAI_API_KEY=your-api-key-here
```

---

## 🔍 Available Services

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| Backend | 8000 | http://localhost:8000 | FastAPI application |
| Backend Docs | 8000 | http://localhost:8000/docs | Swagger UI |
| Ollama | 11434 | http://localhost:11434 | LLM server |

---

## 📊 Service Management

### Check Status

```bash
# Using Docker Compose
docker-compose ps

# Using Makefile
make status

# Manual
docker ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Ollama only
docker-compose logs -f ollama

# Using Makefile
make logs-f
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart backend only
docker-compose restart backend

# Rebuild and restart
make rebuild
```

---

## 🧪 Testing

### Health Check

```bash
# Using curl
curl http://localhost:8000/health

# Using Makefile
make health
```

### Test All Endpoints

```bash
make test
```

### Manual Tests

```bash
# Health
curl http://localhost:8000/health

# LLM Info
curl http://localhost:8000/llm/info

# Personas
curl http://localhost:8000/personas

# Chat (with persona)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "persona": "oi-trader",
    "messages": [{
      "role": "user",
      "content": "Hello"
    }]
  }'
```

---

## 🛠️ Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Port 8000 already in use
# - .env file missing
# - Ollama not accessible
```

### Ollama not responding

```bash
# Check if running
docker-compose ps ollama

# Check logs
docker-compose logs ollama

# Restart
docker-compose restart ollama
```

### Model not found

```bash
# List models
docker exec -it ollama ollama list

# Pull model
docker exec -it ollama ollama pull llama3.1:8b
```

---

## 🧹 Cleanup

### Stop Services

```bash
# Stop
docker-compose down

# Stop and remove volumes (⚠️ deletes Ollama models)
docker-compose down -v

# Using Makefile
make clean
```

### Remove Images

```bash
# Remove all project images
docker-compose down --rmi all

# Prune system (⚠️ removes all unused Docker resources)
make prune
```

---

## 🔐 Security

### Production Checklist

- [ ] Use `docker-compose.prod.yml`
- [ ] Configure CORS properly (no `*`)
- [ ] Use HTTPS via reverse proxy
- [ ] Keep Ollama internal (don't expose port)
- [ ] Regularly update images
- [ ] Use secrets for API keys
- [ ] Enable resource limits

---

## 📚 Additional Resources

- **Full Deployment Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Documentation:** http://localhost:8000/docs
- **Project Specs:** [SPECS.md](SPECS.md)
- **Docker Hub - Ollama:** https://hub.docker.com/r/ollama/ollama

---

## 💡 Tips

1. **Use `make` commands** for convenience
2. **Check logs first** when troubleshooting
3. **Pull models** after first deployment
4. **Backup Ollama data** before cleanup: `make backup`
5. **Monitor resources** with: `docker stats`

---

**Need Help?** See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive documentation.
