<div align="center">

# 🤖 Mini-AGI Backend

**Enterprise-grade AI Agent Orchestration Platform**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*A powerful, production-ready backend system for orchestrating AI agents with multi-provider LLM support, tool integration, and extensible architecture.*

[Features](#-features) •
[Quick Start](#-quick-start) •
[Documentation](#-documentation) •
[API Reference](#-api-reference) •
[Configuration](#-configuration)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

Mini-AGI Backend is a sophisticated agent orchestration system that enables AI-powered applications to intelligently coordinate multiple specialist agents, execute tools, and deliver structured responses. Built with FastAPI and designed for production use, it provides a robust foundation for building autonomous AI systems.

### Key Capabilities

- **Multi-Agent Orchestration**: Coordinate specialist agents (orchestrator, coder, researcher) with intelligent task delegation
- **Multi-Provider LLM Support**: Seamlessly switch between Ollama (local) and Z.AI (cloud) providers
- **Extensible Tool System**: Built-in local tools and MCP (Model Context Protocol) server integration
- **Production-Ready**: Type-safe, fully documented, with comprehensive testing infrastructure
- **Zero-Setup Testing**: Mock servers for instant testing without external dependencies

---

## ✨ Features

### 🧠 Intelligent Agent System
- **Orchestrator Agent**: Main coordinator for routing and delegation
- **Coder Agent**: Specialized in Python, Node.js, Next.js, and trading algorithms
- **Researcher Agent**: Expert in information analysis and data structuring
- **JSON Protocol**: Strict agent communication protocol with fallback parsing

### 🔌 Multi-Provider LLM Support
- **Ollama**: Local, free, self-hosted LLM server
- **Z.AI**: Cloud API with Thai language support and GLM-4.6 model
- **Configurable Models**: Easy model switching via environment variables
- **Temperature Control**: Adjustable creativity/determinism

### 🛠️ Comprehensive Tool System
- **Local Tools**: File I/O (`read_file`, `write_file`), Python execution (`run_python`)
- **MCP Integration**: Filesystem and trader MCP server bridges
- **Extensible Registry**: Simple tool addition via registry pattern
- **Error Handling**: Graceful error responses with context

### 🚀 Developer Experience
- **FastAPI Framework**: Auto-generated API docs at `/docs`
- **Type Safety**: Full Python type hints for IDE support
- **Hot Reload**: Development server with auto-reload
- **Mock Servers**: Test without Ollama or MCP servers
- **Automated Testing**: Comprehensive test suite with validation

### 🔒 Production Features
- **CORS Support**: Configurable cross-origin access
- **Health Checks**: `/health` endpoint for monitoring
- **Event Tracking**: Full execution trace in responses
- **Environment Config**: Secure `.env` file management
- **API Versioning**: Version 1.0.0 with stable interface

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│                     (backend/main.py)                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Core                         │
│                  (orchestrator/core.py)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Orchestrator │  │    Coder     │  │  Researcher  │      │
│  │    Agent     │  │    Agent     │  │    Agent     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │               │
│         └─────────────────┴──────────────────┘               │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
      ┌─────────────────┐    ┌─────────────────┐
      │   LLM Provider  │    │   Tool System   │
      │  (Ollama/Z.AI)  │    │  (Local + MCP)  │
      └─────────────────┘    └─────────────────┘
```

### Request Flow

1. **Client** sends POST request to `/chat` endpoint
2. **FastAPI** extracts user message from assistant-ui format
3. **Orchestrator** initiates agent with context
4. **Agent** decides action: `use_tool`, `delegate`, or `final`
5. **Tool Execution** (if needed) returns results
6. **Agent Delegation** (if needed) switches to specialist
7. **Response** returns final answer with event trace

---

## ⚡ Quick Start

Get up and running in **3 simple steps**:

### Option 1: Quick Test (No Ollama Required)

Perfect for immediate testing without any setup:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start all mock servers (one command!)
./start_all_mock.sh

# 3. In another terminal, run tests
python test_system.py
```

**Result:** ✅ All tests pass! System ready to use.

### Option 2: Production Setup

For real LLM integration:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your LLM provider
cp .env.example .env
# Edit .env with your settings (see Configuration section)

# 3. Start the server
uvicorn backend.main:app --reload --port 8000

# 4. Test the API
curl http://localhost:8000/health
```

**Access API Docs:** http://localhost:8000/docs

---

## 📦 Installation

### Prerequisites

- **Python**: 3.10 or higher
- **pip**: Latest version recommended
- **LLM Provider** (choose one):
  - Ollama (local, free) - [Install Ollama](https://ollama.ai)
  - Z.AI API key - [Get API key](https://z.ai)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/mini-AGI_Backend.git
cd mini-AGI_Backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from backend.orchestrator.llm import get_provider_info; print('✅ Installation successful!')"
```

### Docker Installation (Optional)

```bash
# Coming soon
docker-compose up
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Copy example configuration
cp .env.example .env
```

### Provider Configuration

#### Ollama (Local, Free)

```bash
LLM_PROVIDER=ollama
LLM_MODEL=mistral          # or llama2, codellama, phi, gemma
LLM_TEMPERATURE=0.2
OLLAMA_URL=http://localhost:11434
```

**Setup Ollama:**
```bash
# Install from https://ollama.ai
ollama pull mistral
ollama serve
```

#### Z.AI (Cloud API)

```bash
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
LLM_TEMPERATURE=0.7
ZAI_API_KEY=your-api-key-here
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

**Get API Key:** Visit [https://z.ai](https://z.ai)

### Configuration Options

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `LLM_PROVIDER` | LLM provider to use | `ollama` | `ollama`, `zai` |
| `LLM_MODEL` | Model name | Provider-specific | See provider docs |
| `LLM_TEMPERATURE` | Response creativity (0.0-1.0) | `0.2` | `0.0` - `1.0` |
| `OLLAMA_URL` | Ollama base URL | `http://localhost:11434` | Any valid URL |
| `ZAI_API_KEY` | Z.AI API key | None | Required for Z.AI |
| `ZAI_BASE_URL` | Z.AI endpoint | `https://api.z.ai/api/coding/paas/v4` | Any valid URL |

📖 **Complete Guide:** See [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration instructions, examples, and troubleshooting.

---

## 🔌 API Reference

### Endpoints

#### POST `/chat`

Main chat endpoint for agent orchestration.

**Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": [{"type": "text", "text": "Your message here"}]
    }
  ]
}
```

**Response:**
```json
{
  "answer": "Agent's final response",
  "events": [
    {
      "step": 1,
      "agent": "orchestrator",
      "action": "final",
      "tool": null,
      "target_agent": null,
      "thought": "Agent's reasoning"
    }
  ]
}
```

#### GET `/health`

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "ok"
}
```

#### GET `/llm/info`

Get current LLM provider configuration.

**Response:**
```json
{
  "provider": "ollama",
  "model": "mistral",
  "temperature": "0.2",
  "ollama_url": "http://localhost:11434",
  "zai_url": "N/A",
  "zai_api_key_set": "No"
}
```

### Interactive API Documentation

FastAPI automatically generates interactive API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Testing

### Automated Testing

Run the comprehensive test suite:

```bash
# Start mock servers
./start_all_mock.sh

# Run tests (in another terminal)
python test_system.py
```

**Expected Output:**
```
============================================================
Mini-AGI Backend System Test
============================================================

=== Checking Ollama ===
✅ Ollama is running

=== Testing Health Endpoint ===
✅ Health endpoint working

=== Testing Simple Chat ===
✅ Chat endpoint returned valid response

Total: 3/3 tests passed
🎉 All tests passed! System is working correctly.
```

### Manual Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "Hello!"}]
      }
    ]
  }'

# Test LLM info endpoint
curl http://localhost:8000/llm/info
```

📖 **Complete Testing Guide:** See [TESTING.md](TESTING.md) for detailed testing instructions.

---

## 💻 Development

### Project Structure

```
mini-AGI_Backend/
├── backend/                    # Main backend implementation
│   ├── main.py                # FastAPI application entry point
│   └── orchestrator/          # Core orchestration system
│       ├── agents.py          # Agent definitions and execution
│       ├── core.py            # Main orchestration loop
│       ├── llm.py             # Multi-provider LLM integration
│       ├── models.py          # Pydantic data models
│       └── tools.py           # Tool implementations
├── .env.example               # Configuration template
├── .gitignore                 # Git ignore rules
├── mock_ollama_server.py      # Mock Ollama for testing
├── mock_mcp_server.py         # Mock MCP servers
├── test_system.py             # Automated test suite
├── start_all_mock.sh          # Start all mock servers
├── requirements.txt           # Python dependencies
├── CONFIGURATION.md           # Configuration guide
├── TESTING.md                 # Testing guide
├── SPECS.md                   # Technical specification
└── README.md                  # This file
```

### Adding New Agents

1. **Define agent** in `backend/orchestrator/agents.py`:

```python
AGENTS["my_agent"] = {
    "system": """You are MyAgent, specialized in X.

    Always respond in JSON: {thought, action, tool, target_agent, args, answer}.

    Available tools: ...
    """
}
```

2. **Update orchestrator** to include new agent in delegation options

3. **Test** with queries requiring the new agent

### Adding New Tools

1. **Implement function** in `backend/orchestrator/tools.py`:

```python
def tool_my_tool(arg: str) -> str:
    try:
        # Implementation
        return "SUCCESS: ..."
    except Exception as e:
        return f"ERROR(my_tool): {e}"
```

2. **Register tool**:

```python
TOOLS["my_tool"] = lambda **kw: tool_my_tool(kw.get("arg", ""))
```

3. **Update agent prompts** to include the new tool

### Code Style

- **Type Hints**: All functions must have type hints
- **Error Handling**: Tools return error strings, not exceptions
- **Documentation**: Docstrings for all public functions
- **Testing**: Add tests for new features

---

## 🚀 Deployment

### Production Checklist

Before deploying to production:

- [ ] Use real LLM provider (Ollama or Z.AI)
- [ ] Set strong API keys and rotate regularly
- [ ] Configure CORS for your domain
- [ ] Add authentication middleware
- [ ] Implement rate limiting
- [ ] Set up monitoring and logging
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS/TLS
- [ ] Review and secure `run_python` tool
- [ ] Set up CI/CD pipeline

### Environment Setup

**Production environment variables:**

```bash
# Use production LLM provider
LLM_PROVIDER=zai
LLM_MODEL=glm-4.6
ZAI_API_KEY=prod-api-key-here

# Security
CORS_ORIGINS=https://yourdomain.com

# Monitoring
LOG_LEVEL=INFO
```

### Running in Production

```bash
# Use production ASGI server
pip install gunicorn

# Run with multiple workers
gunicorn backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## 📚 Documentation

Comprehensive documentation is available:

| Document | Description |
|----------|-------------|
| **[CONFIGURATION.md](CONFIGURATION.md)** | Complete configuration guide with examples |
| **[TESTING.md](TESTING.md)** | Testing guide with mock servers and examples |
| **[SPECS.md](SPECS.md)** | Detailed technical specification |
| **[CLAUDE.md](CLAUDE.md)** | AI assistant development guide |
| **[API Docs](http://localhost:8000/docs)** | Interactive API documentation (when server running) |

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Guidelines

- Follow existing code style and conventions
- Add type hints to all functions
- Write tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern web framework for building APIs
- **Ollama** - Local LLM serving platform
- **Z.AI** - Cloud LLM API with Thai support
- **Pydantic** - Data validation using Python type hints

---

## 📞 Support

- **Documentation**: Check the `/docs` folder
- **Issues**: [GitHub Issues](https://github.com/yourusername/mini-AGI_Backend/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/mini-AGI_Backend/discussions)

---

<div align="center">

**Built with ❤️ using FastAPI and Python**

[⬆ Back to Top](#-mini-agi-backend)

</div>
