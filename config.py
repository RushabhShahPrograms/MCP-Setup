import os
import sys
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
SERVERS_DIR = Path(__file__).parent / "servers"

PREFERRED_MODELS = [
    "ministral-3:8b", "ministral:8b",
    "qwen3.5:9b-q4_K_M", "qwen3.5:9b", "qwen3.5",
    "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:3b", "qwen2.5",
    "llama3.1:8b", "llama3.1:70b", "llama3.1",
    "llama3.2:3b", "llama3.2:1b", "llama3.2",
    "mistral:7b", "mistral",
    "deepseek-r1:7b", "deepseek-r1",
    "gemma2:9b", "gemma2",
    "phi4", "phi3",
]


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
        return "qwen2.5:3b"
    chat_models = models
    for preferred in PREFERRED_MODELS:
        base = preferred.split(":")[0]
        for m in chat_models:
            if m == preferred or m.startswith(base + ":"):
                return m
    return chat_models[0]


def build_server_configs() -> dict:
    configs: dict = {
        "math":      {"command": sys.executable, "args": [str(SERVERS_DIR / "math_server.py")],      "transport": "stdio"},
        "units":     {"command": sys.executable, "args": [str(SERVERS_DIR / "unit_server.py")],      "transport": "stdio"},
        "weather":   {"command": sys.executable, "args": [str(SERVERS_DIR / "weather_server.py")],   "transport": "stdio"},
        "translate": {"command": sys.executable, "args": [str(SERVERS_DIR / "translate_server.py")], "transport": "stdio"},
        "ffmpeg":    {"command": sys.executable, "args": [str(SERVERS_DIR / "ffmpeg_server.py")],    "transport": "stdio"},
    }

    return configs