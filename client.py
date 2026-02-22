#!/usr/bin/env python3
"""MCP Multi-Agent CLI — Math · Units · Weather · Stocks × Ollama"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()  # Load environment variables (like TAVILY_API_KEY) from .env file

from rich.console import Console
from rich.markdown import Markdown

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# ─── Config ───────────────────────────────────────────────────────────────────

console = Console()
SERVERS_DIR = Path(__file__).parent / "servers"

# ENHANCED PROMPT: Specifically target local models like Ollama, which often fail
# to use tools correctly or hallucinate results. Tell it *exactly* how to behave.
SYSTEM_PROMPT = """\
You are a highly capable AI assistant with access to specific tools.
You MUST use a tool if the user asks for calculations, conversions, weather, stock data, or a web search. 
Do NOT guess or calculate these values yourself. Wait for the tool output and then clearly present it.

Available capabilities:
- Math tools: arithmetic, algebra, statistics, trigonometry, and more
- Unit conversion tools: length, weight, temperature, volume, speed, area, time, pressure, energy
- Weather tools: current conditions, forecasts, hourly data, location comparisons
- Stock market tools: live prices, fundamentals, history, comparisons, dividends, indices
- Web search tools: Use this to search the internet for the most up-to-date facts, news, and information.

RULES:
1. Always call the appropriate tool when facts, calculations, or external data are needed.
2. If multiple steps are required, call tools one by one and wait for the result.
3. Be concise and format the numbers/data clearly in your final response.
4. Never assume a stock price, weather condition, math result, or current event data. Use the web search tools when looking for current facts not covered by other tools.
"""

# ─── Ollama auto-detect ───────────────────────────────────────────────────────

PREFERRED_MODELS = [
    "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:3b", "qwen2.5",
    "llama3.1:8b", "llama3.1:70b", "llama3.1",
    "llama3.2:3b", "llama3.2:1b", "llama3.2",
    "mistral:7b", "mistral",
    "deepseek-r1:7b", "deepseek-r1",
    "gemma2:9b", "gemma2",
    "phi4", "phi3",
]

def list_ollama_models() -> list:
    """Return all locally available Ollama model names."""
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().splitlines()
        return [l.split()[0] for l in lines[1:] if l.strip() and not l.startswith("NAME")]
    except Exception:
        return []

def detect_ollama_model() -> str:
    """Pick the best available model, preferring tool-capable ones."""
    models = list_ollama_models()
    if not models:
        return "qwen2.5:7b"
    for pref in PREFERRED_MODELS:
        for m in models:
            if m == pref or m.startswith(pref.split(":")[0] + ":"):
                return m
    return models[0]

# ─── Agent turn ───────────────────────────────────────────────────────────────

async def run_agent_turn(agent, user_input: str, history: list):
    history.append(HumanMessage(content=user_input))

    with console.status("[bold cyan]Thinking...[/]", spinner="dots"):
        result = await agent.ainvoke({"messages": history})

    messages = result["messages"]
    response_text = ""

    for msg in messages[len(history):]:
        if isinstance(msg, AIMessage):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    console.print(f"  [bold yellow]⚙ Executing Tool:[/] {tc['name']}")
            if isinstance(msg.content, str) and msg.content.strip():
                response_text = msg.content
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        response_text += block.get("text", "") + "\n"
        elif isinstance(msg, ToolMessage):
            console.print(f"  [bold green]✓ Tool Completed:[/] {msg.name}")

    return response_text, list(messages)

# ─── Entry point ──────────────────────────────────────────────────────────────

async def main():
    with console.status("[bold cyan]Detecting Ollama models...[/]"):
        model_name = detect_ollama_model()

    console.clear()
    console.print("[bold cyan]==== MCP Agent CLI ====[/]")
    console.print(f"Model: [bold green]{model_name}[/]\n")

    server_configs = {
        "math":    {"command": sys.executable, "args": [str(SERVERS_DIR / "math_server.py")],    "transport": "stdio"},
        "units":   {"command": sys.executable, "args": [str(SERVERS_DIR / "unit_server.py")],    "transport": "stdio"},
        "weather": {"command": sys.executable, "args": [str(SERVERS_DIR / "weather_server.py")], "transport": "stdio"},
        "stocks":  {"command": sys.executable, "args": [str(SERVERS_DIR / "stock_server.py")],   "transport": "stdio"},
        "tavily":  {"command": "npx", "args": ["-y", "tavily-mcp@latest"], "transport": "stdio"},
    }

    console.print("[dim cyan]Connecting to MCP servers...[/]")
    try:
        client = MultiServerMCPClient(server_configs)
        tools = await client.get_tools()
        console.print(f"[bold green]✓ Successfully connected to servers. Loaded {len(tools)} tools.[/]\n")
    except Exception as e:
        console.print(f"[bold red]Failed to connect to servers: {e}[/]\n")
        return

    llm = ChatOllama(model=model_name, temperature=0.1)
    agent = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT)
    history: list = []

    console.print("[dim]Type your message, or type 'exit' to quit. Use 'clear' to reset history.[/]\n")

    while True:
        try:
            ts = datetime.now().strftime("%H:%M")
            user_input = console.input(f"[bold blue]You ({ts}):[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd == "exit" or cmd == "/exit":
            break
        elif cmd == "clear" or cmd == "/clear":
            history = []
            console.clear()
            console.print("[dim green]Context cleared.[/]\n")
            continue
        
        console.print()
        try:
            response, history = await run_agent_turn(agent, user_input, history)
            console.print("\n[bold magenta]Agent:[/]")
            console.print(Markdown(response) if response else "*(No text response)*")
        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {e}")
            console.print("[dim]Ensure Ollama is running (`ollama serve`).[/]")

        console.print("\n" + "─" * 40 + "\n")

if __name__ == "__main__":
    asyncio.run(main())