"""
Configuration for API providers.
Supports any OpenAI-compatible API endpoint.
"""

import os
from pathlib import Path

# Load from environment or config file
def _load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

_load_env()

# === API Configuration ===
# Vision API (for analyzing screenshots)
VISION_API_KEY = os.environ.get("VISION_API_KEY", "")
VISION_BASE_URL = os.environ.get("VISION_BASE_URL", "")  # e.g., "https://api.minimax.chat/v1"
VISION_MODEL = os.environ.get("VISION_MODEL", "gpt-4o")

# LLM API (for generating project brief)
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")  # e.g., "https://api.minimax.chat/v1"
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o")

# Whisper (local, no API needed)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

# === Provider Presets ===

PRESETS = {
    "openai": {
        "vision_base_url": "",
        "vision_model": "gpt-4o",
        "llm_base_url": "",
        "llm_model": "gpt-4o",
    },
    "minimax": {
        "vision_base_url": "https://api.minimax.io/v1",
        "vision_model": "MiniMax-VL-01",
        "llm_base_url": "https://api.minimax.io/v1",
        "llm_model": "MiniMax-M2.7-highspeed",
    },
    "siliconflow": {
        "vision_base_url": "https://api.siliconflow.cn/v1",
        "vision_model": "Qwen/Qwen2-VL-72B-Instruct",
        "llm_base_url": "https://api.siliconflow.cn/v1",
        "llm_model": "Qwen/Qwen2.5-72B-Instruct",
    },
    "deepseek": {
        "vision_base_url": "https://api.deepseek.com/v1",
        "vision_model": "deepseek-chat",
        "llm_base_url": "https://api.deepseek.com/v1",
        "llm_model": "deepseek-chat",
    },
    "zhipuai": {
        "vision_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "vision_model": "glm-4v-plus",
        "llm_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "llm_model": "glm-4",
    },
}


def apply_preset(name):
    """Apply a preset configuration."""
    if name not in PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(PRESETS.keys())}")
    p = PRESETS[name]
    return {
        "vision_base_url": p["vision_base_url"],
        "vision_model": p["vision_model"],
        "llm_base_url": p["llm_base_url"],
        "llm_model": p["llm_model"],
    }


def get_provider_display():
    """Return a human-readable list of available providers."""
    return list(PRESETS.keys())
