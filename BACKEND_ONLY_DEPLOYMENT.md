# 🚀 Backend-Only Deployment (No Ollama Container)

This guide is for deploying **only the backend** without the Ollama container.

---

## 📋 When to Use This

Use backend-only deployment when:

- ✅ Using **Z.AI cloud API** (recommended for simplicity)
- ✅ Using **external Ollama server** (separate machine/cloud)
- ✅ Ollama is **already running on your host machine**
- ✅ You want a **minimal Docker setup**

---

## 🚀 Quick Start

### Option 1: Using Z.AI (Easiest - No Ollama Needed)

```bash
# 1. Create .env file
cp .env.backend-only.example .env

# 2. Edit .env and add your Z.AI API key
# Edit the file and set:
#   ZAI_API_KEY=your-actual-api-key

# 3. Start backend
docker-compose -f docker-compose.backend-only.yml up -d

# 4. Test
curl http://localhost:8000/health
```

### Option 2: Using Ollama on Host Machine

**Prerequisites:** Ollama must be running on your Windows machine.

```bash
# 1. Start Ollama on your host (if not already running)
# Open PowerShell and run:
ollama serve

# 2. Create .env file
cp .env.backend-only.example .env

# 3. Edit .env:
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_URL=http://host.docker.internal:11434

# 4. Start backend
docker-compose -f docker-compose.backend-only.yml up -d

# 5. Test
curl http://localhost:8000/health
```

### Option 3: Using External Ollama Server

```bash
# 1. Create .env file
cp .env.backend-only.example .env

# 2. Edit .env:
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_URL=http://your-ollama-server-ip:11434

# 3. Start backend
docker-compose -f docker-compose.backend-only.yml up -d

# 4. Test
curl http://localhost:8000/health
```

---

## ⚙️ Configuration

### For Z.AI

**.env file:**
```bash
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
LLM_TEMPERATURE=0.2
ZAI_API_KEY=your-api-key-here
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Get Z.AI API Key:**
1. Visit https://z.ai
2. Sign up / Log in
3. Get your API key from the dashboard
4. Add it to `.env` file

### For Ollama on Host (Windows)

**.env file:**
```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
LLM_TEMPERATURE=0.2
OLLAMA_URL=http://host.docker.internal:11434
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Important:** `host.docker.internal` is a special DNS name that Docker uses to connect to the host machine on Windows/Mac.

### For External Ollama Server

**.env file:**
```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
LLM_TEMPERATURE=0.2
OLLAMA_URL=http://192.168.1.100:11434  # Your Ollama server IP
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## 🔍 Management Commands

### Start Backend

```bash
docker-compose -f docker-compose.backend-only.yml up -d
```

### View Logs

```bash
# Follow logs
docker-compose -f docker-compose.backend-only.yml logs -f

# Last 100 lines
docker-compose -f docker-compose.backend-only.yml logs --tail=100
```

### Stop Backend

```bash
docker-compose -f docker-compose.backend-only.yml down
```

### Restart Backend

```bash
docker-compose -f docker-compose.backend-only.yml restart
```

### Rebuild and Restart

```bash
docker-compose -f docker-compose.backend-only.yml up -d --build
```

---

## 🧪 Testing

### Basic Health Check

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"status":"ok"}
```

### Check LLM Configuration

```bash
curl http://localhost:8000/llm/info
```

**Expected (Z.AI):**
```json
{
  "provider": "zai",
  "model": "glm-4.6",
  "temperature": "0.2",
  "zai_url": "https://api.z.ai/api/coding/paas/v4",
  "zai_api_key_set": "Yes"
}
```

### Check Available Personas

```bash
curl http://localhost:8000/personas
```

### Test Chat Endpoint

```bash
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

## 🐛 Troubleshooting

### Issue: Backend can't connect to Z.AI

**Symptoms:**
```
Failed to call Z.AI: 401 Unauthorized
```

**Solution:**
1. Check ZAI_API_KEY in .env
2. Verify API key is valid
3. Restart backend: `docker-compose -f docker-compose.backend-only.yml restart`

### Issue: Backend can't connect to host Ollama

**Symptoms:**
```
Failed to call Ollama at http://host.docker.internal:11434
```

**Solutions:**

1. **Verify Ollama is running on host:**
   ```bash
   # In PowerShell (outside Docker)
   curl http://localhost:11434/api/tags
   ```

2. **Check OLLAMA_URL in .env:**
   ```bash
   # Must use host.docker.internal on Windows/Mac
   OLLAMA_URL=http://host.docker.internal:11434
   ```

3. **Restart backend:**
   ```bash
   docker-compose -f docker-compose.backend-only.yml restart
   ```

### Issue: Connection refused to external Ollama

**Symptoms:**
```
Connection refused
```

**Solutions:**

1. **Verify external Ollama is accessible:**
   ```bash
   curl http://your-server-ip:11434/api/tags
   ```

2. **Check firewall settings** on external server

3. **Verify OLLAMA_URL** in .env is correct

### Issue: CORS errors

**Symptoms:**
```
Access to fetch blocked by CORS policy
```

**Solution:**

Edit .env:
```bash
CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.com
```

Then restart:
```bash
docker-compose -f docker-compose.backend-only.yml restart
```

---

## 📊 Comparison: With vs Without Ollama

| Feature | With Ollama Container | Backend Only |
|---------|----------------------|--------------|
| Container Count | 2 (backend + ollama) | 1 (backend) |
| Disk Space | ~20 GB | ~500 MB |
| Memory Usage | 4-8 GB | 512 MB - 2 GB |
| Startup Time | 1-2 min | 10-20 sec |
| External Dependency | None | Z.AI API or external Ollama |
| Cost | Free (local) | Z.AI costs / self-hosted |
| Best For | Self-contained, offline | Production, cloud |

---

## 💡 Best Practices

### For Z.AI

1. ✅ Use environment variables for API keys
2. ✅ Never commit `.env` to git
3. ✅ Monitor API usage/costs
4. ✅ Set appropriate temperature for your use case
5. ✅ Configure CORS for your frontend domain

### For Host Ollama

1. ✅ Ensure Ollama is running before starting backend
2. ✅ Use `host.docker.internal` on Windows/Mac
3. ✅ Pull required models: `ollama pull llama3.1:8b`
4. ✅ Monitor host resources

### For External Ollama

1. ✅ Secure the connection (VPN, SSH tunnel)
2. ✅ Use HTTPS if possible
3. ✅ Monitor network latency
4. ✅ Have backup LLM provider (Z.AI)

---

## 🔐 Security Notes

1. **API Keys:** Never commit `.env` file to git (already in `.gitignore`)
2. **CORS:** Restrict origins in production (don't use `*`)
3. **Network:** Use HTTPS for external connections
4. **Firewall:** Only expose port 8000 (not Ollama)
5. **Updates:** Keep Docker images updated

---

## 📈 Production Deployment

For production with backend-only:

```bash
# 1. Use production .env
cp .env.backend-only.example .env
# Edit with production values

# 2. Build optimized image
docker-compose -f docker-compose.backend-only.yml build --no-cache

# 3. Start with restart policy
docker-compose -f docker-compose.backend-only.yml up -d

# 4. Setup reverse proxy (Nginx/Caddy)
# 5. Enable SSL/HTTPS
# 6. Setup monitoring
# 7. Configure backups
```

---

## 🆘 Need Help?

- **Full Deployment Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Docker Quick Reference:** [DOCKER_README.md](DOCKER_README.md)
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

**Enjoy your lightweight backend deployment! 🎉**
