import asyncio
import sys
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama

from config import detect_ollama_model, list_ollama_models, build_server_configs
from agents.supervisor import Supervisor, UTILITY_TOOL_NAMES, RESEARCH_TOOL_NAMES

console = Console()


def _print_help():
    t = Table(title="Commands", header_style="bold cyan", border_style="dim")
    t.add_column("Command",    style="bold yellow", no_wrap=True)
    t.add_column("Description")
    for cmd, desc in [
        ("/help",       "Show this help"),
        ("/tools",      "List all MCP tools and their assigned agent"),
        ("/models",     "List available Ollama models"),
        ("/model NAME", "Switch model (clears history)"),
        ("/clear",      "Clear conversation history"),
        ("/exit",       "Quit"),
    ]:
        t.add_row(cmd, desc)
    console.print(t)


def _print_tools(tools: list):
    t = Table(title=f"MCP Tools  [{len(tools)} total]", header_style="bold cyan", border_style="dim")
    t.add_column("#",          style="dim", width=4)
    t.add_column("Tool",       style="bold yellow")
    t.add_column("Agent",      style="cyan", width=10)
    t.add_column("Description")
    for i, tool in enumerate(tools, 1):
        if tool.name in UTILITY_TOOL_NAMES:
            label = "Utility"
        elif tool.name in RESEARCH_TOOL_NAMES:
            label = "Research"
        else:
            label = "—"
        desc = (getattr(tool, "description", "") or "—").split(".")[0][:80]
        t.add_row(str(i), tool.name, label, desc)
    console.print(t)


def _print_models():
    models = list_ollama_models()
    if not models:
        console.print("[red]No Ollama models found. Is `ollama serve` running?[/]")
        return []
    t = Table(title="Available Ollama Models", header_style="bold cyan", border_style="dim")
    t.add_column("Model", style="bold yellow")
    for m in models:
        t.add_row(m)
    console.print(t)
    return models


async def _run_streaming(supervisor, user_input, history):
    """
    Drive the supervisor stream, printing tool activity and response tokens live.
    Returns (response_text, updated_history, agent_type).
    """
    response_text = ""
    new_history   = history
    agent_type    = "unknown"
    streaming_started = False

    async for event_type, payload in supervisor.stream(user_input, history):
        if event_type == "agent":
            agent_type = payload
            console.print(f"  [dim]-> routing to [bold]{payload}[/bold] agent[/]")

        elif event_type == "tool":
            if streaming_started:
                sys.stdout.write("\n")
                sys.stdout.flush()
                streaming_started = False
            console.print(f"  [bold yellow]⚙  {payload}[/]")

        elif event_type == "done":
            console.print(f"  [bold green]✓  {payload}[/]")

        elif event_type == "token":
            if not streaming_started:
                console.print(f"\n[bold magenta]Agent ({agent_type}):[/]")
                streaming_started = True
            sys.stdout.write(payload)
            sys.stdout.flush()

        elif event_type == "finish":
            response_text, new_history, agent_type = payload
            if streaming_started:
                sys.stdout.write("\n")
                sys.stdout.flush()

    return response_text, new_history, agent_type


async def main():
    with console.status("[bold cyan]Detecting Ollama models...[/]"):
        model_name = detect_ollama_model()

    console.clear()
    console.print(Panel(
        f"[bold cyan]mcp-pilot[/bold cyan]\n"
        f"Model  : [bold green]{model_name}[/]\n"
        f"Type   : [bold yellow]/help[/] for all commands",
        title="[bold white]Welcome[/]", expand=False, border_style="cyan",
    ))

    server_configs = build_server_configs()

    console.print(f"\n[dim cyan]Connecting to {len(server_configs)} MCP servers...[/]")
    try:
        client = MultiServerMCPClient(server_configs)
        tools  = await client.get_tools()
        console.print(f"[bold green]✓ {len(tools)} tools loaded from {len(server_configs)} servers.[/]\n")
    except Exception as e:
        console.print(f"[bold red]✗ MCP connection failed:[/] {e}")
        return

    llm = ChatOllama(model=model_name, temperature=0.1)

    with console.status("[cyan]Building agents...[/]"):
        supervisor = Supervisor(llm, tools)

    console.print()
    history: list = []

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
            console.print("[dim green]✓ History cleared.[/]")
            continue
        elif cmd == "/help":
            _print_help()
            continue
        elif cmd == "/tools":
            _print_tools(tools)
            continue
        elif cmd == "/models":
            _print_models()
            continue
        elif cmd.startswith("/model "):
            new_model = user_input[7:].strip()
            if not new_model:
                console.print("[red]Usage: /model MODEL_NAME[/]")
                continue
            model_name = new_model
            llm        = ChatOllama(model=model_name, temperature=0.1)
            history    = []
            with console.status("[cyan]Re-initializing...[/]"):
                supervisor = Supervisor(llm, tools)
            console.print(f"[bold green]✓ Switched to [cyan]{model_name}[/cyan] (history cleared)[/]")
            continue

        console.print()
        try:
            response, history, agent_type = await _run_streaming(
                supervisor, user_input, history
            )

        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {e}")
            console.print("[dim]Tip: Ensure Ollama is running (`ollama serve`).[/]")

        console.print("\n" + "─" * 55)


if __name__ == "__main__":
    asyncio.run(main())