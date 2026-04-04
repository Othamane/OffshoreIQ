"""
LLM provider factory.
Supports Groq (free) as primary — easy to swap for OpenAI/Anthropic.
"""

from functools import lru_cache
from langchain_groq import ChatGroq
from app.core.config import settings
from app.core.logging import logger


@lru_cache(maxsize=1)
def get_llm():
    """Returns a cached LLM instance. Groq is free at console.groq.com."""
    logger.info("Initializing LLM: %s via Groq", settings.llm_model)
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.llm_model,
        temperature=0.2,
        max_tokens=2048,
    )
