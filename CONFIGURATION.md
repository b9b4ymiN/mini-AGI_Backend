# Configuration Guide - Mini-AGI Backend

## Overview

The Mini-AGI Backend supports multiple LLM providers and is fully configurable via environment variables. You can easily switch between providers, models, and adjust parameters without changing code.

---

## Supported LLM Providers

| Provider | Description | API Key Required |
|----------|-------------|------------------|
| **Ollama** | Local LLM server (free, self-hosted) | ❌ No |
| **Z.AI** | Cloud API with Thai language support | ✅ Yes |

---

## Quick Configuration

### 1. Create `.env` File

Copy the example configuration:

```bash
cp .env.example .env
```

### 2. Edit `.env` File

Choose your provider and configure it:

**For Ollama (Default - No API Key Required):**
```bash
LLM_PROVIDER=ollama
LLM_MODEL=mistral
LLM_TEMPERATURE=0.2
OLLAMA_URL=http://localhost:11434
```

**For Z.AI (Requires API Key):**
```bash
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
LLM_TEMPERATURE=0.7
ZAI_API_KEY=your-api-key-here
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

### 3. Start the Server

```bash
# Install dependencies (if not already)
pip install -r requirements.txt

# Start the server
uvicorn backend.main:app --reload --port 8000
```

### 4. Verify Configuration

Check your current LLM configuration:

```bash
curl http://127.0.0.1:8000/llm/info
```

Response:
```json
{
  "provider": "zai",
  "model": "glm-4.6",
  "temperature": "0.7",
  "ollama_url": "N/A",
  "zai_url": "https://api.z.ai/api/coding/paas/v4",
  "zai_api_key_set": "Yes"
}
```

---

## Configuration Options

### Core Settings

| Variable | Description | Default | Valid Values |
|----------|-------------|---------|--------------|
| `LLM_PROVIDER` | Which LLM provider to use | `ollama` | `ollama`, `zai` |
| `LLM_MODEL` | Model name | Provider-specific | See below |
| `LLM_TEMPERATURE` | Creativity level (0.0-1.0) | `0.2` | `0.0` to `1.0` |

### Ollama Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_URL` | Ollama base URL | `http://localhost:11434` |

**Popular Ollama Models:**
- `mistral` - Fast, good quality (recommended)
- `llama2` - Meta's LLaMA 2
- `codellama` - Code-specialized model
- `phi` - Small, fast model
- `gemma` - Google's Gemma
- `qwen` - Alibaba's Qwen

### Z.AI Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `ZAI_API_KEY` | Your Z.AI API key | *Required* |
| `ZAI_BASE_URL` | Z.AI endpoint URL | `https://api.z.ai/api/coding/paas/v4` |

**Z.AI Models:**
- `glm-4.6` - Latest GLM model (recommended)
- And more...

**Z.AI Endpoints:**
- `https://api.z.ai/api/coding/paas/v4` - For coding tasks
- `https://api.z.ai/api/paas/v4` - General endpoint

---

## Usage Examples

### Example 1: Local Development with Ollama

Perfect for free, local development without API costs.

**Setup:**

1. Install Ollama from https://ollama.ai
2. Pull a model:
   ```bash
   ollama pull mistral
   ```
3. Configure `.env`:
   ```bash
   LLM_PROVIDER=ollama
   LLM_MODEL=mistral
   LLM_TEMPERATURE=0.2
   ```
4. Start servers:
   ```bash
   # Terminal 1: Ollama (if not auto-started)
   ollama serve

   # Terminal 2: Backend
   uvicorn backend.main:app --reload --port 8000
   ```

**Test:**
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Hello!"}]
      }
    ]
  }'
```

### Example 2: Production with Z.AI

Best for production deployment with Thai language support.

**Setup:**

1. Get API key from https://z.ai
2. Configure `.env`:
   ```bash
   LLM_PROVIDER=zai
   LLM_MODEL=glm-4.6
   LLM_TEMPERATURE=0.7
   ZAI_API_KEY=your-actual-api-key
   ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
   ```
3. Start backend:
   ```bash
   uvicorn backend.main:app --port 8000
   ```

**Test with Thai:**
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "สวัสดี คุณทำอะไรได้บ้าง?"}]
      }
    ]
  }'
```

### Example 3: Testing with Mock Servers

No Ollama or API key needed - perfect for CI/CD.

```bash
# Start all mock servers
./start_all_mock.sh

# Run tests
python test_system.py
```

The mock Ollama server will automatically respond with agent-compatible JSON.

---

## Temperature Guide

Temperature controls randomness in responses:

| Temperature | Behavior | Best For |
|-------------|----------|----------|
| `0.0 - 0.2` | Deterministic, focused | Code generation, JSON output, agents |
| `0.3 - 0.5` | Balanced | General tasks |
| `0.6 - 0.8` | Creative | Content writing, brainstorming |
| `0.9 - 1.0` | Very creative | Story writing, poetry |

**Recommendation for agents:** Keep `0.2` or lower to ensure JSON compliance.

---

## Switching Providers

You can switch providers by simply changing environment variables:

### Switch from Ollama to Z.AI:

**Before (Ollama):**
```bash
LLM_PROVIDER=ollama
LLM_MODEL=mistral
```

**After (Z.AI):**
```bash
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
ZAI_API_KEY=your-key-here
```

**Restart the server:**
```bash
# The server will automatically pick up the new configuration
uvicorn backend.main:app --reload --port 8000
```

**Verify:**
```bash
curl http://127.0.0.1:8000/llm/info
```

---

## Environment Variable Precedence

1. **Actual environment variables** (set in shell)
2. **.env file** (in project root)
3. **Default values** (hardcoded in code)

Example:
```bash
# .env file has:
LLM_PROVIDER=ollama

# But you can override it:
LLM_PROVIDER=zai uvicorn backend.main:app --port 8000
```

---

## Troubleshooting

### Issue: "ZAI_API_KEY environment variable is required"

**Solution:** Set your Z.AI API key in `.env`:
```bash
ZAI_API_KEY=your-actual-api-key
```

### Issue: "Failed to call Ollama"

**Solutions:**
1. Check if Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```
2. Start Ollama:
   ```bash
   ollama serve
   ```
3. Check `OLLAMA_URL` in `.env`

### Issue: "Unknown LLM provider"

**Solution:** Check `LLM_PROVIDER` is either `ollama` or `zai`:
```bash
# Valid values:
LLM_PROVIDER=ollama
# or
LLM_PROVIDER=zai
```

### Issue: Agent returns non-JSON

**Solutions:**
1. Lower temperature:
   ```bash
   LLM_TEMPERATURE=0.1
   ```
2. Check agent system prompts enforce JSON-only output
3. The system has fallback JSON parsing built-in

### Issue: .env file not loading

**Solutions:**
1. Make sure `.env` is in project root (same level as `backend/`)
2. Reinstall python-dotenv:
   ```bash
   pip install python-dotenv
   ```
3. Restart the server completely

---

## Advanced Configuration

### Using Multiple Models

You can have different configurations for different environments:

**.env.development:**
```bash
LLM_PROVIDER=ollama
LLM_MODEL=mistral
LLM_TEMPERATURE=0.2
```

**.env.production:**
```bash
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
LLM_TEMPERATURE=0.7
ZAI_API_KEY=prod-api-key
```

**Load specific env file:**
```bash
# Development
ln -sf .env.development .env
uvicorn backend.main:app --reload --port 8000

# Production
ln -sf .env.production .env
uvicorn backend.main:app --port 8000
```

### Docker Environment Variables

If using Docker, pass env vars:

```bash
docker run -e LLM_PROVIDER=zai \
           -e ZAI_API_KEY=your-key \
           -e LLM_MODEL=glm-4.6 \
           -p 8000:8000 \
           mini-agi-backend
```

Or use `--env-file`:
```bash
docker run --env-file .env -p 8000:8000 mini-agi-backend
```

---

## Security Best Practices

1. **Never commit `.env` to git:**
   ```bash
   # .gitignore already includes:
   .env
   ```

2. **Use different API keys for dev/prod:**
   ```bash
   # Development
   ZAI_API_KEY=dev-key-with-limits

   # Production
   ZAI_API_KEY=prod-key-monitored
   ```

3. **Rotate API keys regularly**

4. **Use environment variables in production:**
   ```bash
   # Don't use .env in production
   # Set via system environment or secrets manager
   export ZAI_API_KEY=your-key
   ```

5. **Monitor API usage and costs**

---

## Testing Configuration

Test your configuration is working:

```bash
# 1. Check health
curl http://127.0.0.1:8000/health

# 2. Check LLM info
curl http://127.0.0.1:8000/llm/info

# 3. Test chat
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":[{"type":"text","text":"Test"}]}]}'
```

---

## Summary

- ✅ **Multiple providers:** Ollama (local) and Z.AI (cloud)
- ✅ **Easy switching:** Just change `.env` file
- ✅ **No code changes:** Everything via environment variables
- ✅ **Configurable:** Models, temperature, URLs
- ✅ **Secure:** API keys in `.env` (not in code)
- ✅ **Verifiable:** `/llm/info` endpoint shows current config

For more help, see:
- **TESTING.md** - Testing guide
- **README.md** - Quick start
- **.env.example** - All configuration options
