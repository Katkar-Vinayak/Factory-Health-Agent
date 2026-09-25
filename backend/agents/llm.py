import os
from typing import Any
from dotenv import load_dotenv

load_dotenv()

def get_llm():
    # Use Google Gemini if key is present
    if os.getenv("GEMINI_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Set max_retries=0 so that if free-tier quota is exhausted,
        # it immediately falls back to the deterministic engine without blocking.
        return ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0, max_retries=0)
    
    # Otherwise fallback to OpenAI if key is present
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o", temperature=0, max_retries=0)
    
    raise ValueError("No API key found for LLM (GEMINI_API_KEY or OPENAI_API_KEY)")


def extract_llm_text(content: Any) -> str:
    """
    Safely extract plain text from LLM response content,
    handling both string and list-of-dicts (common in Gemini 3.x LangChain integrations).
    """
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                texts.append(part["text"])
            elif isinstance(part, str):
                texts.append(part)
        return "".join(texts).strip()
    return str(content).strip()
