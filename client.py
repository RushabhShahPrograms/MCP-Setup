#!/usr/bin/env python3
"""MCP Multi-Agent CLI — Math · Units · Weather · Stocks × Ollama"""

import asyncio
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.rule import Rule
from rich import box

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# ─── Config ───────────────────────────────────────────────────────────────────

console     = Console()
SERVERS_DIR = Path(__file__).parent / "servers"

SYSTEM_PROMPT = """\
You are a highly capable AI assistant with access to specialized tools:
- Math tools: arithmetic, algebra, statistics, trigonometry, and more
- Unit conversion tools: length, weight, temperature, volume, speed, area, time, pressure, energy
- Weather tools: current conditions, forecasts, hourly data, location comparisons
- Stock market tools: live prices, fundamentals, history, comparisons, dividends, indices

Always use the appropriate tool when the user asks for calculations, conversions, weather, or stock data.
Be concise, accurate, and format numbers clearly. When showing results, present them in a readable way.
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


# ─── UI helpers ───────────────────────────────────────────────────────────────

def print_header(model_name: str):
    console.clear()

    banner = Text()
    banner.append("  MCP", style="bold cyan")
    banner.append(" Agent", style="bold white")
    banner.append(" CLI\n", style="bold cyan")
    banner.append("  ─────────────────────────────\n", style="dim cyan")
    banner.append("  Multi-Server  ", style="dim white")
    banner.append("×", style="bold cyan")
    banner.append("  Ollama  ", style="dim white")
    banner.append("×", style="bold cyan")
    banner.append("  LangGraph\n\n", style="dim white")
    banner.append("  Model  ", style="dim white")
    banner.append(model_name, style="bold cyan")
    banner.append("\n\n", style="")
    banner.append("  🔢 Math    ", style="bold blue")
    banner.append("📐 Units    ", style="bold green")
    banner.append("🌤  Weather    ", style="bold yellow")
    banner.append("📈 Stocks", style="bold red")

    console.print(Panel(banner, border_style="cyan", padding=(1, 3)))
    console.print()


def print_servers_status(tools_count: int, connected: bool):
    t = Table(
        show_header=True, header_style="bold cyan",
        box=box.SIMPLE_HEAVY, border_style="dim cyan", padding=(0, 1),
    )
    t.add_column("Server",       style="bold white", width=14)
    t.add_column("Status",       width=12)
    t.add_column("Capabilities", style="dim white")

    ok  = "[bold green]● Online[/]"
    err = "[bold red]✗ Failed[/]"
    s   = ok if connected else err

    servers = [
        ("🔢  Math",     "arithmetic, algebra, stats, trig, compound interest"),
        ("📐  Units",    "length, weight, temp, volume, speed, area, time, energy"),
        ("🌤   Weather", "current, multi-day forecast, hourly, city compare"),
        ("📈  Stocks",   "price, fundamentals, history, compare, dividends, indices"),
    ]
    for name, caps in servers:
        t.add_row(name, s, caps)

    console.print(t)
    if connected:
        console.print(f"  [dim green]✓ {tools_count} tools ready[/]\n")


def user_bubble(text: str):
    console.print()
    console.print(Panel(
        Text(text, style="white"),
        title="[bold green] You [/]", title_align="left",
        border_style="green", padding=(0, 2),
    ))


def agent_bubble(text: str):
    content = Markdown(text) if text.strip() else Text("(no text response)", style="dim")
    console.print(Panel(
        content,
        title="[bold magenta] Agent [/]", title_align="left",
        border_style="magenta", padding=(1, 2),
    ))


def tool_call_indicator(name: str, args: str = ""):
    short = args[:100].replace("\n", " ") if args else ""
    console.print(
        f"  [bold yellow]⚙[/]  [yellow]{name}[/]"
        + (f"  [dim]{short}[/]" if short else "")
    )


def tool_result_indicator(name: str):
    console.print(f"  [dim green]✓  {name}[/]")


def print_help(model_name: str):
    t = Table(box=box.SIMPLE_HEAVY, border_style="dim cyan", show_header=False, padding=(0, 1))
    t.add_column("Cmd",  style="bold cyan",  width=16)
    t.add_column("Desc", style="dim white")
    rows = [
        ("/help",       "Show this help"),
        ("/clear",      "Clear screen & reset conversation context"),
        ("/history",    "Show conversation history"),
        ("/models",     "List all available Ollama models"),
        ("/model NAME", "Switch to a different model (e.g. /model llama3.1:8b)"),
        ("/exit",       "Quit"),
    ]
    for cmd, desc in rows:
        t.add_row(cmd, desc)
    console.print(Panel(t, title="[bold cyan] Commands [/]", border_style="cyan"))

    ex = Table(box=None, show_header=False, padding=(0, 1))
    ex.add_column("Tag", style="bold cyan",  width=10)
    ex.add_column("Q",   style="dim white")
    examples = [
        ("math",    "Compound interest on $50k at 6.5% for 15 years, monthly compounding"),
        ("units",   "Convert 100 mph to km/h and m/s"),
        ("weather", "7-day forecast for Tokyo and compare it with London right now"),
        ("stocks",  "Compare AAPL, MSFT, GOOGL — show P/E, market cap and 52w range"),
    ]
    for tag, q in examples:
        ex.add_row(tag, q)
    console.print(Panel(ex, title="[bold cyan] Example Queries [/]", border_style="dim cyan"))
    console.print(f"  [dim]Active model:[/] [bold cyan]{model_name}[/]\n")


def print_history(messages: list):
    if not messages:
        console.print("  [dim]No history yet.[/]\n")
        return
    console.print(Rule("[bold cyan] Conversation History [/]"))
    for msg in messages:
        if isinstance(msg, HumanMessage):
            console.print(f"  [bold green]You:[/]   {str(msg.content)[:200]}")
        elif isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content.strip():
            console.print(f"  [bold magenta]Agent:[/] {msg.content[:200]}")
    console.print(Rule(style="dim"))
    console.print()


def print_models(models: list, current: str):
    t = Table(
        title="[bold cyan] Available Ollama Models [/]",
        box=box.SIMPLE_HEAVY, border_style="cyan",
        show_header=True, header_style="bold white", padding=(0, 1),
    )
    t.add_column("Model", style="bold white")
    t.add_column("",      width=4, justify="center")
    for m in models:
        marker = "[bold green]●  active[/]" if m == current else "[dim]○[/]"
        t.add_row(m, marker)
    console.print(t)
    console.print()


# ─── Agent turn ───────────────────────────────────────────────────────────────

async def run_agent_turn(agent, user_input: str, history: list):
    history.append(HumanMessage(content=user_input))

    with Live(
        Spinner("dots2", text="[dim cyan]  Thinking…[/]", style="cyan"),
        console=console, refresh_per_second=12, transient=True,
    ):
        result = await agent.ainvoke({"messages": history})

    messages      = result["messages"]
    response_text = ""

    for msg in messages[len(history):]:
        if isinstance(msg, AIMessage):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_call_indicator(tc["name"], str(tc.get("args", "")).replace("\n", " "))
            if isinstance(msg.content, str) and msg.content.strip():
                response_text = msg.content
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        response_text = block.get("text", "")
        elif isinstance(msg, ToolMessage):
            tool_result_indicator(msg.name)

    return response_text, list(messages)


# ─── Entry point ──────────────────────────────────────────────────────────────

async def main():
    # Detect model silently before any UI
    with console.status("[dim cyan]Detecting Ollama models…[/]", spinner="dots2"):
        model_name = detect_ollama_model()

    print_header(model_name)

    server_configs = {
        "math":    {"command": sys.executable, "args": [str(SERVERS_DIR / "math_server.py")],    "transport": "stdio"},
        "units":   {"command": sys.executable, "args": [str(SERVERS_DIR / "unit_server.py")],    "transport": "stdio"},
        "weather": {"command": sys.executable, "args": [str(SERVERS_DIR / "weather_server.py")], "transport": "stdio"},
        "stocks":  {"command": sys.executable, "args": [str(SERVERS_DIR / "stock_server.py")],   "transport": "stdio"},
    }

    console.print("  [dim cyan]Connecting to MCP servers…[/]")
    try:
        client = MultiServerMCPClient(server_configs)
        tools  = await client.get_tools()
        print_servers_status(len(tools), connected=True)
    except Exception as e:
        print_servers_status(0, connected=False)
        console.print(f"  [bold red]Error:[/] {e}\n")
        return

    llm   = ChatOllama(model=model_name, temperature=0)
    agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
    history: list = []

    console.print(Panel(
        "[dim]Ask anything — math, unit conversions, weather, stocks. "
        "Type [bold cyan]/help[/] for commands or [bold cyan]/exit[/] to quit.[/]",
        border_style="dim cyan", padding=(0, 2),
    ))
    console.print()

    # ── Chat loop ──────────────────────────────────────────────────────────────
    while True:
        try:
            ts         = datetime.now().strftime("%H:%M")
            user_input = Prompt.ask(f"[bold green]  You[/] [dim]({ts})[/]").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd   = parts[0].lower()

            if cmd == "/exit":
                break
            elif cmd == "/help":
                print_help(model_name)
            elif cmd == "/clear":
                history = []
                print_header(model_name)
                console.print("  [dim green]✓ Context cleared.[/]\n")
            elif cmd == "/history":
                print_history(history)
            elif cmd == "/models":
                models = list_ollama_models()
                print_models(models, model_name) if models else console.print("  [bold red]Could not reach Ollama.[/]\n")
            elif cmd == "/model":
                if len(parts) < 2:
                    console.print(f"  [dim]Usage:[/] /model <name>   current: [bold cyan]{model_name}[/]\n")
                else:
                    model_name = parts[1].strip()
                    llm        = ChatOllama(model=model_name, temperature=0)
                    agent      = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
                    history    = []
                    print_header(model_name)
                    console.print(f"  [dim green]✓ Switched to [bold cyan]{model_name}[/].[/]\n")
            else:
                console.print(f"  [bold red]Unknown command:[/] {cmd}  — /help for options.\n")
            continue

        user_bubble(user_input)
        console.print()

        try:
            response, history = await run_agent_turn(agent, user_input, history)
            console.print()
            agent_bubble(response or "*(No text response — see tool output above)*")
        except Exception as e:
            console.print(f"\n  [bold red]Error:[/] {e}")
            console.print("  [dim]Check that Ollama is running: ollama serve[/]\n")

        console.print()

    console.print()
    console.print(Panel("[dim]Goodbye! 👋[/]", border_style="dim cyan", padding=(0, 4)))
    console.print()


if __name__ == "__main__":
    asyncio.run(main())