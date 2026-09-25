from typing import Any
import re
from services.llm_service import get_llm_service

def get_llm():
    """Returns the singleton local LLM service (Qwen)."""
    return get_llm_service()


def extract_llm_text(content: Any) -> str:
    """
    Safely extract plain text from LLM response content,
    and strip any hidden chain-of-thought (<think>...</think>) tokens.
    """
    if isinstance(content, str):
        text = content.strip()
    elif isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                texts.append(part["text"])
            elif isinstance(part, str):
                texts.append(part)
        text = "".join(texts).strip()
    else:
        text = str(content).strip()
        
    # Strip any <think>...</think> tags if present
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return cleaned

