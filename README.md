# MCP Multi-Agent CLI

A feature-rich command line interface that connects local AI models (via Ollama) to a suite of powerful tools using the Model Context Protocol (MCP). Built with LangGraph, it enables your local LLM to leverage external intelligence gracefully and deterministically.

## 🚀 Current Architecture

The core script, `client.py`, operates an AI agent powered by locally running models (like `qwen2.5:3b` or `phi3`). This agent communicates with **six intelligent MCP Servers** that provide specialized tools through the Model Context Protocol (MCP).

### Available Servers & Capabilities

#### **Python MCP Servers** (Local & Deterministic)

- **🔢 Math (`servers/math_server.py`)**: 
  - Basic arithmetic: `add()`, `subtract()`, `multiply()`, `divide()`
  - Powers & roots: `power()`, `square_root()`, `factorial()`
  - Logarithms: `log()` (natural, base-10, or custom)
  - Trigonometry: `sin()`, `cos()`, `tan()` (in degrees)
  - Number theory: `gcd()`, `lcm()`

- **📐 Units (`servers/unit_server.py`)**: 
  - Length: mm, cm, m, km, inch, foot, mile, nautical mile, light-year
  - Weight: mg, g, kg, oz, lb, stone, ton
  - Volume: ml, l, gallon, quart, pint, cup, fl oz, m³
  - Speed: m/s, km/h, mph, knots, ft/s
  - Area: m², km², cm², acres, hectares, sq miles
  - Time: seconds, minutes, hours, days, weeks, months, years
  - Temperature: Celsius ↔ Fahrenheit ↔ Kelvin

- **🌤️ Weather (`servers/weather_server.py`)**: 
  - Real-time weather: `get_current_weather(location)` — temperature, humidity, wind, precipitation, visibility
  - Multi-day forecast: `get_weather_forecast(location, days)` — up to 14 days
  - Smart geocoding to resolve city/location names worldwide
  - Wind direction & speed, pressure, cloud cover

- **📈 Stocks (`servers/stock_server.py`)**: 
  - Symbol lookup: `search_stock_symbol(company_name)` — find tickers (NSE/BSE & global)
  - Live prices: `get_stock_price(ticker)` — current price, change, 52-week range, volume
  - Fundamentals: `get_stock_info(ticker)` — P/E ratio, EPS, market cap, dividend yield, analyst ratings
  - Historical data: `get_stock_history(ticker, period)` — 1d to max history with open/high/low/close
  - Comparisons: `compare_stocks([tickers])` — side-by-side analysis
  - Supports international markets (NSE/BSE for India, NASDAQ/NYSE for US, etc.)

- **🌐 Translation (`servers/translate_server.py`)**: 
  - Translate text to **50+ languages** via Google Translate
  - Language detection: `detect_language(text)` — identify source language
  - List all supported languages: `list_supported_languages()`
  - Supported: Hindi, Gujarati, Spanish, French, German, Japanese, Korean, Chinese, Arabic, and more
  - Auto-detect source language or specify manually

#### **Node.js MCP Server**

- **📂 Filesystem (`@modelcontextprotocol/server-filesystem`)**: 
  - Read files across permitted directories (home, documents, downloads, current workspace, etc.)
  - Search & analyze local codebases, config files, and documentation
  - Supports Windows, macOS, and Linux paths

## 🛠️ Installation & Setup

### 1. Prerequisites

- **Python 3.10+**
- **Ollama** installed with at least one model pulled (e.g., `ollama pull qwen2.5:3b`)
- **Node.js (v18+)** & **npm** (optional, only for Filesystem/Tavily servers)

The Math, Units, Weather, Stocks, and Translation servers work **completely offline** with no additional dependencies beyond what's in `requirements.txt`.

### 2. Environment Setup

Clone the repository, create a virtual environment, and install dependencies.

```bash
# Create and activate a Virtual Environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the necessary python packages
pip install -r requirements.txt
```

### 3. Optional: API Keys

Create a `.env` file in the root directory (alongside `client.py`):

```ini
# For SerpAPI web search (optional alternative)
SERPAPI_API_KEY="your-serpapi-key-here"

# For memory persistence (optional)
MEM0_USER_ID="your_user_id"  # Default: "local_user"
```

**Note**: The **Math, Units, Weather, Stocks, Translation, and Filesystem servers require NO API keys** — they're fully local or use free public APIs.

## 💻 Usage

Ensure Ollama is running in the background (`ollama serve`), then start the multi-agent CLI:

```bash
python client.py
```

### CLI Commands

- `/help` — Show all available CLI commands
- `/tools` — List all loaded MCP tools (from all servers)
- `/models` — List all locally available Ollama models
- `/model [NAME]` — Switch to a different model on-the-fly (clears conversation history)
- `/memories` — View everything stored in long-term memory
- `/forget` — Wipe ALL stored memories and start fresh
- `/clear` — Clear current conversation history (keeps memory)
- `/exit` — Quit the CLI

### Smart Tool Selection

The AI agent uses **explicit tool selection rules** to avoid hallucinations:

- **Weather queries** → Always use `get_current_weather()` or `get_weather_forecast()` (not web search)
- **Stock queries** → Always search symbol first via `search_stock_symbol()`, then get price/info
- **Math & calculations** → Always use math tools, never calculate in your head
- **Unit conversions** → Always use conversion tools, never convert manually
- **Translations** → When a user requests output in a specific language, the agent:
  - Completes all tool calls to get English results
  - Calls `translate_text()` as the final step
  - Shows ONLY the translated output
- **Web search** → Only for recent news, general lookups, or topics without dedicated tools

## 🧠 Long-Term Memory (mem0)

The agent includes **persistent memory** via `mem0` + ChromaDB:
- Automatically extracts key facts from conversations (e.g., "User prefers Indian stocks")
- Semantic search over past memories to inject context into the system prompt
- **No network required** — ChromaDB stores memories locally in `./memory_db/`
- Uses Ollama's embedding model for semantic search
- Each conversation automatically updates and refines the memory store
- Use `/memories` to view stored facts or `/forget` to wipe all memories

**Example flow**:
1. User: *"Show me Reliance Industries stock history"*
2. Agent remembers: "User is interested in Indian stocks"
3. Next session: User mentions "show my stock" → Agent automatically considers Indian tickers first

---

## 🔧 Architecture Details

### Tech Stack
- **LLM**: Ollama (local models: qwen, llama, phi, mistral, deepseek, etc.)
- **Agent Framework**: LangGraph (deterministic, tool-using agent loop)
- **MCP Implementation**: `langchain-mcp-adapters` (multi-server client)
- **Memory**: mem0 + ChromaDB (local semantic storage)
- **CLI**: Rich (beautiful terminal output)
- **Python**: 3.10+

### Server Configuration
- **Python servers**: FastMCP framework (stdio transport)
- **Node.js servers**: npx-based execution (stdio transport)
- **Communication**: MCP over stdio (no network required)

### Data Sources
- **Weather**: Open-Meteo (free, no API key)
- **Stocks**: yfinance (free, Yahoo Finance data)
- **Translation**: Google Translate (free, via deep-translator)
- **Filesystem**: Local read-only access (permission-based)


## 🔮 What's Next? (Future Roadmap)

- [x] **Long-Term Memory**: mem0 integration for persistent fact storage ✅
- [x] **Translation Server**: Multi-language support with auto-detect
- [x] **Filesystem Server**: Local file & codebase access (via MCP)
- [ ] **Smart Tool Caching**: Cache frequent queries (weather, stock prices) with TTL
- [ ] **Advanced Database Querying**: MCP server for SQLite/PostgreSQL operations
- [ ] **Web Scraping Server**: Dedicated crawler for structured data extraction
- [ ] **Image Analysis**: Vision capabilities for charts, screenshots, and diagrams
- [ ] **Dockerization**: One-click deployment with all servers in containers
- [ ] **Web Dashboard**: UI to view memories, execution logs, and tool statistics
- [ ] **Multi-Turn Planning**: Agent decomposes complex tasks into smaller steps
- [ ] **Function Calling (Parallel)**: Run multiple tools concurrently when safe
