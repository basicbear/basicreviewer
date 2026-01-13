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
    **kwargs,
) -> BaseChatModel:
    """Get an LLM client based on configuration.

    Args:
        provider: LLM provider (e.g., 'claude', 'openai'). If None, reads from configs.json
        model: Model identifier. If None, reads from configs.json
        **kwargs: Additional parameters to pass to the model (e.g., temperature, max_tokens)

    Returns:
        Configured LLM client instance

    Raises:
        ValueError: If provider is not supported
        FileNotFoundError: If configs.json is not found
    """
    # Load config if provider/model not specified
    if provider is None or model is None:
        config = load_llm_config()
        provider = provider or config.get("provider", "claude")
        model = model or config.get("model", "claude-3-5-sonnet-20241022")

    # Get the appropriate model based on provider
    if provider.lower() == "claude":
        return get_claude_model(model=model, **kwargs)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. Currently supported: claude"
        )
