import asyncio
import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from mem0 import Memory

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# ─── Globals ──────────────────────────────────────────────────────────────────

# Disable mem0 telemetry — skips slow network ping on every startup
os.environ.setdefault("MEM0_TELEMETRY", "False")

console        = Console()
SERVERS_DIR    = Path(__file__).parent / "servers"
MEMORY_DB_PATH = str(Path(__file__).parent / "memory_db")

USER_ID    = os.getenv("MEM0_USER_ID", "local_user")
EMBED_MODEL = "qwen3-embedding:0.6b"   # change here if you switch embedder

PREFERRED_MODELS = [
    "ministral-3:8b", "ministral:8b",
    "qwen3.5:9b-q4_K_M", "qwen3.5:9b", "qwen3.5",
    "qwen2.5:7b",  "qwen2.5:14b", "qwen2.5:3b",  "qwen2.5",
    "llama3.1:8b", "llama3.1:70b","llama3.1",
    "llama3.2:3b", "llama3.2:1b", "llama3.2",
    "mistral:7b",  "mistral",
    "deepseek-r1:7b", "deepseek-r1",
    "gemma2:9b",   "gemma2",
    "phi4",        "phi3",
]

EMBEDDING_KEYWORDS = ("embed", "embedding", "rerank", "minilm", "nomic-embed", "bge-")

# ─── mem0 Memory Layer ─────────────────────────────────────────────────────────

def init_memory(model_name: str):
    """
    Initialize mem0 with a fully local stack:
      LLM      → Ollama  (temperature=0 for deterministic fact extraction)
      Embedder → Ollama  qwen3-embedding:0.6b
      Store    → ChromaDB at ./memory_db  (no Docker needed)

    Uses a two-attempt strategy:
      Attempt 1: with version="v1.1" (simpler extraction, better for small models)
      Attempt 2: plain config fallback (if older mem0 doesn't support version field)
    """
    try:
        from mem0 import Memory
    except ImportError:
        console.print(
            "[yellow]⚠  mem0 not installed — memory disabled.\n"
            "   Fix: pip install mem0ai chromadb[/]"
        )
        return None

    # Base config — only fields ALL mem0 versions accept
    base_config = {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "path":            MEMORY_DB_PATH,
                "collection_name": f"mcp_cli_{USER_ID}",
            },
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model":           model_name,
                "temperature":     0,
                "max_tokens":      2000,
                "ollama_base_url": "http://localhost:11434",
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model":           EMBED_MODEL,
                "ollama_base_url": "http://localhost:11434",
            },
        },
    }

    try:
        config_v11 = {"version": "v1.1", **base_config}
        memory = Memory.from_config(config_v11)
        console.print(
            f"[bold green]✓ Memory ready[/] "
            f"[dim](ChromaDB · {EMBED_MODEL} · v1.1)[/]"
        )
        return memory
    except Exception:
        pass  # version field not supported — try plain config

    # Attempt 2: plain config without version (older mem0)
    try:
        memory = Memory.from_config(base_config)
        console.print(
            f"[bold green]✓ Memory ready[/] "
            f"[dim](ChromaDB · {EMBED_MODEL} · legacy)[/]"
        )
        return memory
    except Exception as e:
        console.print(f"[yellow]⚠  Memory init failed: {e}\n   Running without memory.[/]")
        return None


def fetch_relevant_memories(memory, user_input: str) -> str:
    """
    Semantic search over past memories relevant to the current user message.
    Returns a formatted string to inject into the system prompt, or "".
    """
    if memory is None:
        return ""
    try:
        results  = memory.search(query=user_input, user_id=USER_ID, limit=5)
        memories = results.get("results", results) if isinstance(results, dict) else results
        if not memories:
            return ""
        lines = ["Relevant memories from past conversations:"]
        for m in memories:
            text = m.get("memory", m.get("text", str(m)))
            lines.append(f"  - {text}")
        return "\n".join(lines)
    except Exception:
        return ""


def save_to_memory(memory, user_input: str, agent_response: str) -> None:
    """
    Persist the current exchange so future sessions can recall context.
    mem0 automatically extracts the important facts — you don't store raw text,
    it stores semantically compressed facts (e.g. "User prefers Indian stocks").
    """
    if memory is None:
        return
    try:
        conversation = [
            {"role": "user",      "content": user_input},
            {"role": "assistant", "content": agent_response},
        ]
        memory.add(conversation, user_id=USER_ID)
    except Exception as e:
        console.print(f"[dim yellow]  ↳ Memory save failed: {e}[/]")


# ─── Ollama Helpers ────────────────────────────────────────────────────────────

def list_ollama_models() -> list[str]:
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        lines  = result.stdout.strip().splitlines()
        return [l.split()[0] for l in lines[1:] if l.strip() and not l.startswith("NAME")]
    except Exception:
        return []


def detect_ollama_model() -> str:
    models = list_ollama_models()
    if not models:
        return "ministral-3:8b"

    # Filter out embedding/reranking models — they can't do chat
    chat_models = [
        m for m in models
        if not any(kw in m.lower() for kw in EMBEDDING_KEYWORDS)
    ]
    if not chat_models:
        return models[0]  # fallback if everything got filtered (unlikely)

    for preferred in PREFERRED_MODELS:
        base = preferred.split(":")[0]
        for m in chat_models:
            if m == preferred or m.startswith(base + ":"):
                return m

    return chat_models[0]


# ─── Dynamic System Prompt ─────────────────────────────────────────────────────

def build_system_prompt(tools: list, memory_context: str = "") -> str:
    """
    Dynamically build system prompt.
    Rebuilt with explicit negative rules to prevent small models from
    defaulting to 'search' for everything and skipping translate_text.
    """
    tool_lines = [
        f"  • {t.name}: {(getattr(t, 'description', '') or '').split('.')[0].strip() or 'No description'}"
        for t in tools
    ]
    tools_block = "\n".join(tool_lines) if tool_lines else "  (none loaded)"

    memory_block = ""
    if memory_context:
        memory_block = f"""
━━ MEMORY — KNOWN USER CONTEXT ━━
{memory_context}
Use this context to personalize. Do not ask for info already known.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    return f"""\
You are a precise AI assistant. Today: {datetime.now().strftime('%A, %d %B %Y')}.
You have specialized tools. Always use the RIGHT tool — not the easiest one.
{memory_block}
━━ AVAILABLE TOOLS ({len(tools)}) ━━
{tools_block}

━━ TOOL SELECTION — EXACT RULES ━━

WEATHER queries → ALWAYS use: get_current_weather(location) or get_weather_forecast(location)
  ✗ NEVER use 'search' for weather. The weather tool gives live accurate data.

STOCK queries → ALWAYS follow this 2-step sequence:
  Step 1: search_stock_symbol("Company Name")  ← get the ticker first
  Step 2: get_stock_price(ticker)              ← then get price
  For fundamentals: get_stock_info(ticker)
  For history:      get_stock_history(ticker, period)
  For comparison:   compare_stocks([ticker1, ticker2])
  ✗ NEVER use 'search' for stock prices or fundamentals.
  ✗ NEVER call get_stock_price() without confirming ticker via search_stock_symbol() first.

MATH / CALCULATIONS → ALWAYS use math tools:
  compound_interest(), add(), multiply(), percentage(), solve_quadratic(), etc.
  ✗ NEVER calculate in your head. NEVER use 'search' for math.

UNIT CONVERSIONS → ALWAYS use convert_* tools:
  convert_length(), convert_temperature(), convert_volume(), etc.
  ✗ NEVER convert in your head. NEVER use 'search' for conversions.

'search' tool → ONLY use for:
  ✓ Current news and recent events
  ✓ General web lookups with no dedicated tool available
  ✓ Researching topics not covered by other tools
  ✗ NEVER for weather, stocks, math, or unit conversions

━━ TRANSLATION — MANDATORY ━━
If user says "in Hindi", "in Gujarati", "in Japanese", "reply in [language]",
"answer in [language]", or any language instruction:
  Step 1: Complete ALL other tool calls to get the English result.
  Step 2: Call translate_text(english_result, target_language) — ALWAYS.
  Step 3: Show ONLY the translated output. Do not show English version.
  ✗ NEVER translate text yourself. ALWAYS use the translate_text tool.
  ✗ NEVER skip translation when user has requested it.

━━ ERROR RECOVERY ━━
  • Tool returns "Error: ..." → do NOT repeat the same call.
  • Stock tool failed?  → re-check ticker via search_stock_symbol() first.
  • After 2 failed retries → tell the user what failed and why, then stop.
  • NEVER call any tool with empty or undefined arguments.

━━ GENERAL ━━
  • Call tools one at a time. Wait for result before next call.
  • Format final answer in clean Markdown. Use tables for comparisons.
  • Be concise — answer first, details below.
"""


# ─── Filesystem Path Builder ──────────────────────────────────────────────────

def build_filesystem_paths() -> list[str]:
    """
    Build paths the filesystem MCP server is allowed to access.
    Covers home + all common user folders on Windows / Linux / macOS.
    Only paths that actually exist on this machine are included.
    These are also injected into the system prompt so the model never guesses.
    """
    home = Path.home()
    candidates = [
        home,                                           # C:\Users\You  or  /home/you
        Path.cwd(),                                     # script working directory
        home / "Downloads",
        home / "Documents",
        home / "Desktop",
        home / "Pictures",
        home / "Videos",
        home / "Music",
        # Windows: handle cases where home resolves oddly (e.g. OneDrive redirect)
        Path("C:/Users") / home.name / "Downloads",
        Path("C:/Users") / home.name / "Documents",
        Path("C:/Users") / home.name / "Desktop",
        Path("C:/"),
        Path("D:/"),
        Path("E:/"),
    ]
    valid, seen = [], set()
    for p in candidates:
        try:
            resolved = str(p.resolve())
            if p.exists() and resolved not in seen:
                valid.append(resolved)
                seen.add(resolved)
        except Exception:
            pass
    return valid


# Compute once at import time so build_system_prompt can reference it
_FILESYSTEM_PATHS: list[str] = build_filesystem_paths()


# ─── Server Config Builder ─────────────────────────────────────────────────────

def build_server_configs() -> dict:
    serpapi_key   = os.getenv("SERPAPI_API_KEY", "").strip()
    allowed_paths = _FILESYSTEM_PATHS

    configs: dict = {
        "math":    {"command": sys.executable, "args": [str(SERVERS_DIR / "math_server.py")],    "transport": "stdio"},
        "units":   {"command": sys.executable, "args": [str(SERVERS_DIR / "unit_server.py")],    "transport": "stdio"},
        "weather": {"command": sys.executable, "args": [str(SERVERS_DIR / "weather_server.py")], "transport": "stdio"},
        "stocks":  {"command": sys.executable, "args": [str(SERVERS_DIR / "stock_server.py")],   "transport": "stdio"},
        "filesystem": {
            "command":   "npx",
            "args":      ["-y", "@modelcontextprotocol/server-filesystem"] + allowed_paths,
            "transport": "stdio",
        },
    }

    if serpapi_key:
        configs["serpapi"] = {
            "url":       f"https://mcp.serpapi.com/{serpapi_key}/mcp",
            "transport": "streamable_http",
        }
    else:
        console.print("[yellow]⚠  SERPAPI_API_KEY missing — web search unavailable.[/]")

    return configs


# ─── CLI Display Helpers ───────────────────────────────────────────────────────

def print_help(tools: list) -> None:
    t = Table(title="CLI Commands", show_header=True, header_style="bold cyan", border_style="dim")
    t.add_column("Command",      style="bold yellow", no_wrap=True)
    t.add_column("Description")
    t.add_row("/help",           "Show this help message")
    t.add_row("/tools",          "List all loaded MCP tools and descriptions")
    t.add_row("/models",         "List all locally available Ollama models")
    t.add_row("/model NAME",     "Switch to a different model (clears history)")
    t.add_row("/memories",       "Show everything in long-term memory")
    t.add_row("/forget",         "Wipe ALL stored memories (fresh start)")
    t.add_row("/clear",          "Clear current conversation history (keeps memory)")
    t.add_row("/exit",           "Quit the CLI")
    console.print(t)


def print_tools(tools: list) -> None:
    t = Table(title=f"Loaded MCP Tools [{len(tools)} total]", show_header=True, header_style="bold cyan", border_style="dim")
    t.add_column("#",    style="dim", width=4)
    t.add_column("Tool", style="bold yellow")
    t.add_column("Description")
    for i, tool in enumerate(tools, 1):
        desc = (getattr(tool, "description", "") or "—").split(".")[0][:90]
        t.add_row(str(i), tool.name, desc)
    console.print(t)


def print_memories(memory) -> None:
    if memory is None:
        console.print("[yellow]Memory layer is not active.[/]")
        return
    try:
        results = memory.get_all(user_id=USER_ID)
        items   = results.get("results", results) if isinstance(results, dict) else results
        if not items:
            console.print("[dim]No memories stored yet. Have a few conversations first![/]")
            return
        t = Table(title=f"Long-Term Memories [{len(items)}]", header_style="bold cyan", border_style="dim")
        t.add_column("#",       style="dim", width=4)
        t.add_column("Memory",  style="white")
        t.add_column("Saved",   style="dim")
        for i, m in enumerate(items, 1):
            text    = str(m.get("memory", m.get("text", m)))[:120]
            created = str(m.get("created_at", ""))[:16]
            t.add_row(str(i), text, created)
        console.print(t)
    except Exception as e:
        console.print(f"[red]Could not retrieve memories: {e}[/]")


def forget_memories(memory) -> None:
    if memory is None:
        console.print("[yellow]Memory layer is not active.[/]")
        return
    try:
        memory.delete_all(user_id=USER_ID)
        console.print("[bold green]✓ All memories wiped.[/]")
    except Exception as e:
        console.print(f"[red]Failed to delete memories: {e}[/]")


def print_models() -> list[str]:
    models = list_ollama_models()
    if not models:
        console.print("[red]No Ollama models found. Is `ollama serve` running?[/]")
        return []
    t = Table(title="Available Ollama Models", header_style="bold cyan", border_style="dim")
    t.add_column("Model Name", style="bold yellow")
    for m in models:
        t.add_row(m)
    console.print(t)
    return models


# ─── Agent Turn ────────────────────────────────────────────────────────────────

async def run_agent_turn(
    llm, tools: list, user_input: str, history: list, memory
) -> tuple[str, list]:
    """
    One user → agent round-trip.
      1. Fetch relevant past memories → rebuild prompt with personal context
      2. Run the agent
      3. Save this exchange to long-term memory
    """
    # ── 1. Memory-aware prompt ─────────────────────────────────────────────────
    memory_context = fetch_relevant_memories(memory, user_input)
    if memory_context:
        console.print("[dim cyan]  ↳ Memory context injected from past sessions[/]")

    agent = create_agent(
        llm, tools,
        system_prompt=build_system_prompt(tools, memory_context)
    )

    # ── 2. Run ─────────────────────────────────────────────────────────────────
    history.append(HumanMessage(content=user_input))

    with console.status("[bold cyan]Thinking...[/]", spinner="dots"):
        result = await agent.ainvoke({"messages": history})

    messages      = result["messages"]
    response_text = ""

    for msg in messages[len(history):]:
        if isinstance(msg, AIMessage):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    console.print(f"  [bold yellow]⚙  Calling:[/] [cyan]{tc['name']}[/]")
            if isinstance(msg.content, str) and msg.content.strip():
                response_text = msg.content
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        response_text += block.get("text", "") + "\n"
        elif isinstance(msg, ToolMessage):
            console.print(f"  [bold green]✓  Result:[/]  [cyan]{msg.name}[/]")

    response_text = response_text.strip()

    # ── 3. Persist to long-term memory ────────────────────────────────────────
    if response_text:
        save_to_memory(memory, user_input, response_text)

    return response_text, list(messages)


# ─── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    with console.status("[bold cyan]Detecting Ollama models...[/]"):
        model_name = detect_ollama_model()

    console.clear()
    console.print(Panel(
        f"[bold cyan]MCP Multi-Agent CLI[/bold cyan]\n"
        f"Model  : [bold green]{model_name}[/]\n"
        f"User ID: [dim]{USER_ID}[/dim]\n"
        f"Type   : [bold yellow]/help[/] to see all commands",
        title="[bold white]Welcome[/]", expand=False, border_style="cyan",
    ))

    # ── Memory ─────────────────────────────────────────────────────────────────
    with console.status("[bold cyan]Initializing memory layer...[/]"):
        memory = init_memory(model_name)

    # ── MCP Servers ────────────────────────────────────────────────────────────
    server_configs = build_server_configs()
    console.print(f"\n[dim cyan]Connecting to {len(server_configs)} MCP servers...[/]")
    try:
        client = MultiServerMCPClient(server_configs)
        tools  = await client.get_tools()
        console.print(
            f"[bold green]✓ Connected — {len(tools)} tools loaded "
            f"from {len(server_configs)} servers.[/]\n"
        )
    except Exception as e:
        console.print(f"[bold red]✗ Failed to connect to MCP servers:[/] {e}\n")
        return

    # ── LLM (passed explicitly so model switching is clean) ────────────────────
    llm = ChatOllama(
        model=model_name,
        temperature=0.1,
    )
    history: list = []

    # ── REPL ───────────────────────────────────────────────────────────────────
    while True:
        try:
            ts         = datetime.now().strftime("%H:%M")
            user_input = console.input(f"\n[bold blue]You ({ts}):[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/]")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("/exit", "exit", "/quit", "quit"):
            console.print("[dim]Goodbye![/]")
            break
        elif cmd in ("/clear", "clear"):
            history = []
            console.clear()
            console.print("[dim green]✓ History cleared (memories are preserved).[/]")
            continue
        elif cmd == "/help":
            print_help(tools)
            continue
        elif cmd == "/tools":
            print_tools(tools)
            continue
        elif cmd == "/models":
            print_models()
            continue
        elif cmd == "/memories":
            print_memories(memory)
            continue
        elif cmd == "/forget":
            forget_memories(memory)
            continue
        elif cmd.startswith("/model "):
            new_model = user_input[7:].strip()
            if not new_model:
                console.print("[red]Usage: /model MODEL_NAME[/]")
                continue
            model_name = new_model
            llm        = ChatOllama(model=model_name, temperature=0.1)
            history    = []
            with console.status("[cyan]Re-initializing memory with new model...[/]"):
                memory = init_memory(model_name)
            console.print(
                f"[bold green]✓ Switched to[/] [cyan]{model_name}[/] "
                f"[dim](history cleared)[/]"
            )
            continue

        # ── Agent inference ────────────────────────────────────────────────────
        console.print()
        try:
            response, history = await run_agent_turn(
                llm, tools, user_input, history, memory
            )
            console.print("\n[bold magenta]Agent:[/]")
            console.print(
                Markdown(response) if response else "[dim]*(No text response)*[/dim]"
            )
        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {e}")
            console.print("[dim]Tip: Ensure Ollama is running (`ollama serve`).[/]")

        console.print("\n" + "─" * 55)


if __name__ == "__main__":
    asyncio.run(main())