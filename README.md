# MCP Multi-Agent CLI

A feature-rich command line interface that connects local AI models (via Ollama) to a suite of powerful tools using the Model Context Protocol (MCP). Built with LangGraph, it enables your local LLM to leverage external intelligence gracefully and deterministically.

## 🚀 Current Architecture

The core script, `client.py`, operates an AI agent powered by locally running models (like `qwen2.5:3b` or `phi3`). This agent communicates with four custom local **Python MCP Servers** and one remote-ready **Node MCP Server** (`tavily-mcp`).

### Available Servers & Capabilities

- **🔢 Math (`servers/math_server.py`)**: Arithmetic, algebra, statistics, compound interest, logging, and trigonometry.
- **📐 Units (`servers/unit_server.py`)**: Dynamic conversions for length, weight, temperature, volume, area, time, pressure, and energy.
- **🌤️ Weather (`servers/weather_server.py`)**: Live weather, multi-day forecasting, and city comparison via Open-Meteo.
- **📈 Stocks (`servers/stock_server.py`)**: Live ticker prices, valuations, dividend histories, and index tracking via yfinance.
- **🌐 Web Search (`tavily-mcp`)**: Web scraping, real-time facts, and live news lookup via Tavily's search API.

## 🛠️ Installation & Setup

### 1. Prerequisites

- **Python 3.10+**
- **Node.js (v18+)** & **npm** (for the Tavily MCP adapter)
- **Ollama** installed with at least one model pulled (e.g., `ollama pull qwen2.5:3b`)
- A **Tavily API Key** (Get one for free at [tavily.com](https://app.tavily.com))

### 2. Environment Setup

Clone the repository, create a virtual environment, and install dependencies.

```bash
# Create and activate a Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Install the necessary python packages
pip install -r requirements.txt
```

### 3. API Keys

Create a `.env` file in the root directory (alongside `client.py`) and add your Tavily API key:

```ini
TAVILY_API_KEY="tvly-your-api-key-here"
```

## 💻 Usage

Ensure Ollama is running in the background (`ollama serve`), then start the multi-agent CLI:

```bash
python client.py
```

Type `/help` inside the CLI to see all available commands, including switching models on the fly (`/models` & `/model [NAME]`).

## 🔮 What's Next? (Future Roadmap)

- [ ] **Filesystem / Workspace Server**: Adding an MCP server that allows the LLM to read local system files, search directories, and analyze local codebases contextually.
- [ ] **Advanced Database Querying**: Equipping the agent with a local SQLite/PostgreSQL server to fetch, create, and analyze structured data.
- [ ] **Memory / Persistence**: Implementing Long-Term Memory (via Mem0 or LangGraph checkpointing) so the agent remembers preferences between sessions.
- [ ] **Dockerization**: Wrapping the client and servers into docker containers for one-click cross-platform deployment.
