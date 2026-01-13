"""LLM model configurations for different providers."""

import os
from typing import Optional

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel

# Load environment variables from .env file
load_dotenv()


def get_claude_model(
    model: str = None,
    temperature: float = 0.0,
    max_tokens: int = 8192,
    api_key: Optional[str] = None,
) -> BaseChatModel:
    """Get a Claude model instance from Anthropic.

    Args:
        model: Model identifier
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
        max_tokens: Maximum tokens to generate
        api_key: Anthropic API key (if None, reads from ANTHROPIC_API_KEY env var)

    Returns:
        ChatAnthropic instance configured with the specified parameters

    Raises:
        ValueError: If API key is not provided and not found in environment
    """
    # Get API key from parameter or environment
    if api_key is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise ValueError(
            "Anthropic API key not found. Please set ANTHROPIC_API_KEY in your .env file "
            "or pass it as a parameter."
        )

    return ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
    )
