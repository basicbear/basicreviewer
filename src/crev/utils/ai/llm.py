"""LLM client utilities for crev."""

import json
from pathlib import Path
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel


from .models import get_claude_model


def load_llm_config() -> dict:
    """Load LLM configuration from configs.json.

    Returns:
        Dictionary containing LLM configuration

    Raises:
        FileNotFoundError: If configs.json is not found
        ValueError: If LLM configuration is invalid
    """
    configs_file = Path("configs.json")

    if not configs_file.exists():
        raise FileNotFoundError(
            "configs.json not found. Run 'crev init' first to create a project."
        )

    with open(configs_file) as f:
        data = json.load(f)

    if "llm" not in data:
        raise ValueError(
            "LLM configuration not found in configs.json. "
            "Please add an 'llm' section with 'provider' and 'model' fields."
        )

    return data["llm"]


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> BaseChatModel:
    """Get an LLM client based on configuration.

    Args:
        provider: LLM provider (e.g., 'claude', 'openai'). If None, reads from configs.json
        model: Model identifier. If None, reads from configs.json
        temperature: Sampling temperature (0.0-1.0). If None, reads from configs.json
        max_tokens: Maximum tokens to generate. If None, reads from configs.json
        **kwargs: Additional parameters to pass to the model

    Returns:
        Configured LLM client instance

    Raises:
        ValueError: If provider is not supported
        FileNotFoundError: If configs.json is not found
    """
    # Load config to get any unspecified parameters
    config = load_llm_config()

    # Use provided values or fall back to config, then to defaults
    provider = provider or config.get("provider", "claude")
    model = model or config.get("model", "claude-sonnet-4-5-20250929")
    temperature = temperature if temperature is not None else config.get("temperature")
    max_tokens = max_tokens if max_tokens is not None else config.get("max_tokens")

    # Build model kwargs, only including non-None values
    model_kwargs = {**kwargs}
    if temperature is not None:
        model_kwargs["temperature"] = temperature
    if max_tokens is not None:
        model_kwargs["max_tokens"] = max_tokens

    # Get the appropriate model based on provider
    if provider.lower() == "claude":
        return get_claude_model(model=model, **model_kwargs)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. Currently supported: claude"
        )
