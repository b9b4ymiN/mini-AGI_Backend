# 🚀 Deployment Guide - Mini-AGI Backend

Complete guide for deploying the Mini-AGI Backend with Docker.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment Options](#deployment-options)
- [Production Deployment](#production-deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ (included with Docker Desktop)
- **Git** (for cloning the repository)

### System Requirements

**Minimum:**
- 2 CPU cores
- 4 GB RAM
- 10 GB disk space

**Recommended (with Ollama):**
- 4+ CPU cores
- 8+ GB RAM
- 20+ GB disk space (for LLM models)

**For GPU Support (Ollama):**
- NVIDIA GPU with 8+ GB VRAM
- NVIDIA Docker runtime installed

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/b9b4ymiN/mini-AGI_Backend.git
cd mini-AGI_Backend
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (optional)
nano .env
```

### 3. Start Services

```bash
# Start all services (backend + Ollama)
docker-compose up -d

# Or build and start
docker-compose up -d --build
```

### 4. Pull Ollama Model

```bash
# Wait for Ollama to start, then pull a model
docker exec -it ollama ollama pull llama3.1:8b

# Or use the model specified in .env
docker exec -it ollama ollama pull $(grep LLM_MODEL .env | cut -d '=' -f2)
```

### 5. Verify Deployment

```bash
# Check backend health
curl http://localhost:8000/health

# Check Ollama
curl http://localhost:11434/api/tags

# View logs
docker-compose logs -f backend
```

**Expected Response:**
```json
{"status":"ok"}
```

---

## Configuration

### Environment Variables

Edit `.env` file to configure:

#### LLM Provider

```bash
# Use Ollama (local)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_URL=http://ollama:11434

# Use Z.AI (cloud)
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
ZAI_API_KEY=your-api-key-here
```

#### CORS Configuration

```bash
# Allow specific origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Allow all origins (NOT recommended for production)
CORS_ORIGINS=*
```

#### Application Settings

```bash
# Max orchestration steps
MAX_ORCHESTRATION_STEPS=10

# Temperature (0.0 - 1.0)
LLM_TEMPERATURE=0.2
```

---

## Deployment Options

### Option 1: Development (Default)

**File:** `docker-compose.yml`

```bash
docker-compose up -d
```

**Features:**
- Ollama port exposed (11434)
- Hot-reload enabled (optional)
- Suitable for local development

### Option 2: Production

**File:** `docker-compose.prod.yml`

```bash
docker-compose -f docker-compose.prod.yml up -d
```

**Features:**
- Ollama port NOT exposed (internal only)
- Resource limits configured
- Health checks enabled
- Logging configured
- Restart policies set

### Option 3: Backend Only (External Ollama/Z.AI)

```bash
# Edit .env to point to external Ollama
OLLAMA_URL=http://your-ollama-server:11434

# Or use Z.AI
LLM_PROVIDER=zai
ZAI_API_KEY=your-key

# Start only backend
docker-compose up -d backend
```

### Option 4: Standalone Docker (No Compose)

```bash
# Build image
docker build -t mini-agi-backend .

# Run container
docker run -d \
  --name mini-agi-backend \
  -p 8000:8000 \
  -e LLM_PROVIDER=zai \
  -e ZAI_API_KEY=your-key \
  mini-agi-backend
```

---

## Production Deployment

### Step 1: Prepare Environment

```bash
# Create production .env file
cp .env.example .env
nano .env
```

**Production .env example:**
```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
LLM_TEMPERATURE=0.2
OLLAMA_URL=http://ollama:11434
CORS_ORIGINS=https://your-frontend-domain.com
MAX_ORCHESTRATION_STEPS=10
BACKEND_PORT=8000
```

### Step 2: Build Production Image

```bash
docker-compose -f docker-compose.prod.yml build --no-cache
```

### Step 3: Deploy

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Step 4: Load Ollama Models

```bash
# Pull required models
docker exec -it ollama-prod ollama pull llama3.1:8b

# List available models
docker exec -it ollama-prod ollama list
```

### Step 5: Setup Reverse Proxy (Recommended)

#### Nginx Configuration

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

#### Enable SSL (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d api.yourdomain.com
```

### Step 6: Setup Monitoring

#### View Logs

```bash
# Follow all logs
docker-compose -f docker-compose.prod.yml logs -f

# Follow backend only
docker-compose -f docker-compose.prod.yml logs -f backend

# Show last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

#### Monitor Resources

```bash
# Monitor containers
docker stats

# Check specific container
docker stats mini-agi-backend-prod
```

---

## GPU Support (NVIDIA)

### Prerequisites

1. **Install NVIDIA Drivers**
2. **Install NVIDIA Container Toolkit:**

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Enable GPU in Docker Compose

Edit `docker-compose.prod.yml`:

```yaml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

### Verify GPU Access

```bash
docker exec -it ollama-prod nvidia-smi
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# LLM provider info
curl http://localhost:8000/llm/info

# Available personas
curl http://localhost:8000/personas

# Ollama models
curl http://localhost:11434/api/tags
```

### Backup Ollama Models

```bash
# Create backup
docker run --rm \
  -v mini-agi-backend_ollama-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/ollama-models-$(date +%Y%m%d).tar.gz /data

# Restore backup
docker run --rm \
  -v mini-agi-backend_ollama-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/ollama-models-YYYYMMDD.tar.gz -C /
```

### Update Deployment

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Or for zero-downtime (if using orchestrator)
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml up -d --no-deps backend
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (CAUTION: Deletes Ollama models)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Clean up Docker system
docker system prune -a
```

---

## Troubleshooting

### Issue: Backend fails to connect to Ollama

**Symptoms:**
```
Failed to call Ollama at http://ollama:11434
```

**Solutions:**

1. **Check if Ollama is running:**
```bash
docker-compose ps ollama
```

2. **Check Ollama logs:**
```bash
docker-compose logs ollama
```

3. **Verify network connection:**
```bash
docker exec -it mini-agi-backend curl http://ollama:11434/api/tags
```

4. **Check OLLAMA_URL in .env:**
```bash
# For Docker Compose
OLLAMA_URL=http://ollama:11434

# For external Ollama
OLLAMA_URL=http://your-server:11434
```

### Issue: Model not found

**Symptoms:**
```
model 'llama3.1:8b' not found
```

**Solutions:**

```bash
# Pull the model
docker exec -it ollama ollama pull llama3.1:8b

# Or change LLM_MODEL in .env to an existing model
docker exec -it ollama ollama list
```

### Issue: Out of memory

**Symptoms:**
```
OOMKilled
```

**Solutions:**

1. **Increase Docker memory limit** (Docker Desktop → Settings → Resources)

2. **Use smaller model:**
```bash
LLM_MODEL=llama3.1:8b  # Instead of larger models
```

3. **Limit container memory:**
Edit `docker-compose.prod.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 4G
```

### Issue: CORS errors

**Symptoms:**
```
Access to fetch blocked by CORS policy
```

**Solutions:**

1. **Add frontend origin to .env:**
```bash
CORS_ORIGINS=http://localhost:3000,https://your-frontend.com
```

2. **Restart backend:**
```bash
docker-compose restart backend
```

### Issue: Permission denied errors

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied
```

**Solutions:**

The Dockerfile runs as non-root user (`appuser`). If you need write permissions:

```bash
# Fix permissions
docker-compose exec backend chown -R appuser:appuser /app/backend/instruction
```

### Issue: Slow responses

**Possible Causes:**

1. **CPU-only Ollama** - Enable GPU support
2. **Large model** - Use smaller model
3. **High temperature** - Lower LLM_TEMPERATURE
4. **Many orchestration steps** - Reduce MAX_ORCHESTRATION_STEPS

**Monitor performance:**
```bash
docker stats
```

---

## Advanced Configuration

### Custom Personas

Add new persona instruction files:

```bash
# Create instruction file
nano backend/instruction/my-persona.md

# Register in personas.py
# Edit backend/orchestrator/personas.py
PERSONA_REGISTRY = {
    "oi-trader": "AI_System_Instructions_Trading_Analysis.md",
    "my-persona": "my-persona.md",  # Add this line
}

# Rebuild
docker-compose up -d --build backend
```

### Environment-specific Configuration

```bash
# Development
docker-compose -f docker-compose.yml up -d

# Staging
docker-compose -f docker-compose.staging.yml up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### Scaling (Kubernetes/Swarm)

For production scaling, consider:
- Kubernetes deployment
- Docker Swarm
- Load balancers
- Separate Ollama cluster

---

## Security Best Practices

1. **Never commit .env files** - Already in `.gitignore`
2. **Use secrets management** - For production API keys
3. **Enable HTTPS** - Use reverse proxy with SSL
4. **Restrict CORS origins** - Don't use `*` in production
5. **Keep images updated** - Regularly update base images
6. **Use non-root user** - Already configured in Dockerfile
7. **Scan for vulnerabilities:**

```bash
docker scan mini-agi-backend
```

---

## Performance Tuning

### Ollama GPU Settings

```bash
# Set GPU memory fraction
docker-compose exec ollama-prod bash -c 'export OLLAMA_GPU_MEMORY_FRACTION=0.9'
```

### Backend Workers

For high load, use multiple workers:

```dockerfile
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## Support & Resources

- **Documentation:** [README.md](README.md)
- **Specifications:** [SPECS.md](SPECS.md)
- **Issues:** [GitHub Issues](https://github.com/b9b4ymiN/mini-AGI_Backend/issues)
- **Docker Docs:** [https://docs.docker.com](https://docs.docker.com)
- **Ollama Docs:** [https://ollama.ai/docs](https://ollama.ai/docs)

---

**Last Updated:** 2025-11-19
**Version:** 1.0.0
