import re
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent
from rich.console import Console

console = Console()

UTILITY_TOOL_NAMES = {
    "add", "subtract", "multiply", "divide", "power", "square_root", "factorial",
    "log", "sin", "cos", "tan", "gcd", "lcm", "is_prime", "fibonacci",
    "solve_quadratic", "mean", "median", "std_deviation", "percentage",
    "percentage_change", "compound_interest",
    "convert_length", "convert_weight", "convert_temperature", "convert_volume",
    "convert_speed", "convert_area", "convert_time", "convert_pressure",
    "convert_energy", "list_conversion_categories",
    "get_current_weather", "get_weather_forecast", "get_hourly_weather", "compare_weather",
    "get_media_info", "convert_media", "extract_audio", "compress_video",
    "trim_media", "merge_videos",
}

RESEARCH_TOOL_NAMES = {
    "translate_text", "detect_language", "list_supported_languages",
}

_UTILITY_RE = re.compile(
    r'\b(calculat|add|subtract|multipl|divid|factorial|fibonacci|prime|square.?root|'
    r'percent|compound.?interest|gcd|lcm|\bsin\b|\bcos\b|\btan\b|\blog\b|'
    r'convert|conversion|\bkm\b|miles?|kilo|pound|celsius|fahrenheit|kelvin|liter|gallon|'
    r'mph|km.?h|meter|feet|foot|inches?|acre|hectare|pascal|joule|'
    r'weather|current.?weather|forecast|temperature|rain|humid|wind|sunny|cloudy|storm|snow|'
    r'ffmpeg|encode|decode|mp4|mp3|mkv|avi|wav|flac|\bvideo\b|\baudio\b|'
    r'compress.?video|extract.?audio|trim|media.?info|merge.?video|'
    r'arithmetic|math|geometry|stats?|mean|median|std.?dev)\b',
    re.IGNORECASE,
)

_RESEARCH_RE = re.compile(
    r'\b(translat|in hindi|in gujarati|in spanish|in french|in japanese|in korean|in arabic|'
    r'in german|in chinese|in russian|language)\b',
    re.IGNORECASE,
)

_UTILITY_PROMPT = """\
You are a highly capable Utility Agent. 
SYSTEM DATE: {date}. Always use this as today's date.

You handle: math, unit conversions, weather, and media processing.

STRATEGY:
1. MULTI-STEP REQUESTS: If a user asks for multiple cities/tasks, handle them ALL. 
2. WEATHER TOOL: Prefer `get_current_weather` for "current" or "now" queries. DO NOT use `get_hourly_weather` unless specifically asked for hour-by-hour data.
3. CHAINING: One tool's output is for the next tool's input. Calculate the weather, then the average, then the prime status. 
4. FINAL RESPONSE: You MUST list and summarize EVERYTHING you did. Do not just talk about the last tool result.

RULES:
- FFMPEG: Always call get_media_info(input_path) first.
- PATHS: Use forward slashes (/) only.
"""

_RESEARCH_PROMPT = """\
You are a precise Research Agent.
SYSTEM DATE: {date}. Always use this as today's date.

You handle: language translation and detection.

RULES:
1. TRANSLATION: Handle multi-part translations if requested.
2. PATHS: Always use forward slashes (/) for file paths.
3. COMPLETENESS: Ensure all parts of the user's request are addressed in your final answer.
"""

class Supervisor:
    def __init__(self, llm, all_tools: list):
        today = datetime.now().strftime("%A, %d %B %Y")

        self.utility_tools  =[t for t in all_tools if t.name in UTILITY_TOOL_NAMES]
        self.research_tools = [t for t in all_tools if t.name in RESEARCH_TOOL_NAMES]

        # Using the modern LangChain 1.0 create_agent
        self._utility_agent = create_agent(
            model=llm, 
            tools=self.utility_tools,
            system_prompt=_UTILITY_PROMPT.format(date=today)
        )
        
        self._research_agent = create_agent(
            model=llm, 
            tools=self.research_tools,
            system_prompt=_RESEARCH_PROMPT.format(date=today)
        )

        console.print(
            f"[dim]  Utility Agent  -> {len(self.utility_tools)} tools[/]\n"
            f"[dim]  Research Agent -> {len(self.research_tools)} tools[/]"
        )

    def _classify(self, query: str) -> str:
        u = len(_UTILITY_RE.findall(query))
        r = len(_RESEARCH_RE.findall(query))
        return "research" if r > u else "utility"

    async def stream(self, user_input: str, history: list):
        agent_type = self._classify(user_input)
        if agent_type == "utility":
            agent = self._utility_agent
            sys_msg = _UTILITY_PROMPT.format(date=datetime.now().strftime("%A, %d %B %Y"))
        else:
            agent = self._research_agent
            sys_msg = _RESEARCH_PROMPT.format(date=datetime.now().strftime("%A, %d %B %Y"))

        yield ("agent", agent_type)

        messages_in = [SystemMessage(content=sys_msg)]
        messages_in.extend(history)
        messages_in.append(HumanMessage(content=user_input))

        response_text = ""

        # FIX 2: Proper LangGraph v2 streaming parsing for Ollama
        async for event in agent.astream_events({"messages": messages_in}, version="v2"):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    # Handle string content
                    if isinstance(chunk.content, str):
                        response_text += chunk.content
                        yield ("token", chunk.content)
                    # Handle list content (sometimes Ollama outputs lists for tool calls)
                    elif isinstance(chunk.content, list):
                        for block in chunk.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                piece = block.get("text", "")
                                response_text += piece
                                yield ("token", piece)

            elif kind == "on_tool_start":
                yield ("tool", event.get("name", "unknown_tool"))

            elif kind == "on_tool_end":
                yield ("done", event.get("name", "unknown_tool"))

        # FIX 3: Update history cleanly (without the memory context permanently attached)
        clean_history = list(history) +[
            HumanMessage(content=user_input),
            AIMessage(content=response_text.strip()),
        ]

        yield ("finish", (response_text.strip(), clean_history, agent_type))