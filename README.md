# MCP Multi-Agent CLI

A feature-rich command line interface that connects local AI models (via Ollama) to a suite of powerful tools using the Model Context Protocol (MCP). Built with LangGraph, it enables your local LLM to leverage external intelligence gracefully and deterministically.

## 🚀 Current Architecture

The core script, `client.py`, operates an AI agent powered by locally running models. This agent communicates with **five intelligent MCP Servers** that provide specialized tools through the Model Context Protocol (MCP).

### Available Servers & Capabilities

#### **Python MCP Servers** (Local & Deterministic)

- **🔢 Math (`servers/math_server.py`)**: 
  - Basic arithmetic: `add()`, `subtract()`, `multiply()`, `divide()`
  - Powers & roots: `power()`, `square_root()`, `factorial()`
  - Logarithms: `log()` (natural, base-10, or custom)
  - Trigonometry: `sin()`, `cos()`, `tan()` (in degrees)
  - Number theory: `gcd()`, `lcm()`, `is_prime()`, `fibonacci()`
  - Statistics: `mean()`, `median()`, `std_deviation()`

- **📐 Units (`servers/unit_server.py`)**: 
  - Length: mm, cm, m, km, inch, foot, mile, nautical mile, light-year
  - Weight: mg, g, kg, oz, lb, stone, ton
  - Volume: ml, l, gallon, quart, pint, cup, fl oz, m³
  - Speed: m/s, km/h, mph, knots, ft/s
  - Area: m², km², cm², acres, hectares, sq miles
  - Time: seconds, minutes, hours, days, weeks, months, years
  - Temperature: Celsius ↔ Fahrenheit ↔ Kelvin

- **🌤️ Weather (`servers/weather_server.py`)**: 
  - Real-time weather: `get_current_weather(location)` — temperature, humidity, wind, precipitation
  - Multi-day forecast: `get_weather_forecast(location, days)` — up to 14 days
  - Hourly forecast: `get_hourly_weather(location)` — precise hour-by-hour data
  - Compare weather between multiple locations

- **🌐 Translation (`servers/translate_server.py`)**: 
  - Translate text to **50+ languages** via Google Translate
  - Language detection: `detect_language(text)` — identify source language
  - List all supported languages: `list_supported_languages()`

- **🎬 Media (`servers/ffmpeg_server.py`)**: 
  - Media info: `get_media_info(file_path)`
  - Processing: `trim_media()`, `convert_media()`, `compress_video()`, `extract_audio()`, `merge_videos()`
  - Requires FFmpeg installed on your system.

## 🛠️ Installation & Setup

### 1. Prerequisites

- **Python 3.10+**
- **Ollama** installed with at least one model pulled (e.g., `ollama pull qwen3.5:9b`)
- **FFmpeg** (optional, for media processing tools)

### 2. Environment Setup

Clone the repository, create a virtual environment, and install dependencies.

```bash
# Create and activate a Virtual Environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the necessary python packages
pip install uv
uv pip install -r requirements.txt
```

## 💻 Usage

Ensure Ollama is running in the background (`ollama serve`), then start the multi-agent CLI:

```bash
python client.py
```

### CLI Commands

- `/help` — Show all available CLI commands
- `/tools` — List all loaded MCP tools (from all servers)
- `/models` — List all locally available Ollama models
- `/model [NAME]` — Switch to a different model on-the-fly (clears history)
- `/clear` — Clear current conversation history
- `/exit` — Quit the CLI

### Smart Tool Selection

The AI agent uses **explicit tool selection rules** to avoid hallucinations:

- **Weather queries** → Uses `get_current_weather()` or related tools.
- **Math & calculations** → Always uses math tools, never calculates in your head.
- **Unit conversions** → Always uses conversion tools, never convert manually.
- **Media Processing** → Uses FFmpeg tools for high-performance file operations.

## 🔧 Architecture Details

### Tech Stack
- **LLM**: Ollama (local models)
- **Agent Framework**: LangGraph (deterministic tool-using loop)
- **MCP Implementation**: `langchain-mcp-adapters`
- **CLI**: Rich (beautiful terminal output)

### Data Sources
- **Weather**: Open-Meteo (free, no API key)
- **Translation**: Google Translate (free, via deep-translator)
- **Media**: Local processing via FFmpeg