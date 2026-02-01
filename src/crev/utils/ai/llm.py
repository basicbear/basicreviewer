"""LLM client utilities for crev."""

import json
from pathlib import Path
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel


from .models import get_claude_model, get_cli_model


def load_llm_config() -> dict:
    """Load LLM configuration from configs.json.

    Returns:
        Dictionary containing full LLM configuration with 'default', 'cli', and 'api' sections

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
            "Please add an 'llm' section with 'default', 'cli', and 'api' fields."
        )

    llm_config = data["llm"]

    # Validate the new structure
    if "default" not in llm_config:
        raise ValueError(
            "LLM configuration missing 'default' field. "
            "Please specify either 'cli' or 'api' as the default."
        )

    default_mode = llm_config["default"]
    if default_mode not in ("cli", "api"):
        raise ValueError(
            f"Invalid default LLM mode: {default_mode}. Must be 'cli' or 'api'."
        )

    if default_mode not in llm_config:
        raise ValueError(
            f"LLM configuration missing '{default_mode}' section for the selected default mode."
        )

    return llm_config


def get_llm_client(
    mode: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> BaseChatModel:
    """Get an LLM client based on configuration.

    Args:
        mode: LLM mode ('cli' or 'api'). If None, reads from configs.json 'default' field
        provider: LLM provider for API mode (e.g., 'claude'). If None, reads from configs.json
        model: Model identifier. If None, reads from configs.json
        temperature: Sampling temperature (0.0-1.0). If None, reads from configs.json
        max_tokens: Maximum tokens to generate. If None, reads from configs.json
        **kwargs: Additional parameters to pass to the model

    Returns:
        Configured LLM client instance

    Raises:
        ValueError: If provider or mode is not supported
        FileNotFoundError: If configs.json is not found
    """
    # Load config to get any unspecified parameters
    config = load_llm_config()

    # Determine the mode (cli or api)
    mode = mode or config.get("default", "api")

    if mode == "cli":
        return _get_cli_client(config, **kwargs)
    elif mode == "api":
        return _get_api_client(config, provider, model, temperature, max_tokens, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM mode: {mode}. Must be 'cli' or 'api'.")


def _get_cli_client(config: dict, **kwargs) -> BaseChatModel:
    """Get a CLI-based LLM client.

    Args:
        config: Full LLM configuration dictionary
        **kwargs: Additional parameters (currently unused for CLI mode)

    Returns:
        Configured CLI LLM client instance
    """
    cli_config = config.get("cli", {})
    return get_cli_model(cli_config)


def _get_api_client(
    config: dict,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> BaseChatModel:
    """Get an API-based LLM client.

    Args:
        config: Full LLM configuration dictionary
        provider: LLM provider (e.g., 'claude', 'openai'). If None, reads from config
        model: Model identifier. If None, reads from config
        temperature: Sampling temperature (0.0-1.0). If None, reads from config
        max_tokens: Maximum tokens to generate. If None, reads from config
        **kwargs: Additional parameters to pass to the model

    Returns:
        Configured API LLM client instance

    Raises:
        ValueError: If provider is not supported
    """
    api_config = config.get("api", {})

    # Use provided values or fall back to config, then to defaults
    provider = provider or api_config.get("provider", "claude")
    model = model or api_config.get("model", "claude-sonnet-4-5-20250929")
    temperature = temperature if temperature is not None else api_config.get("temperature")
    max_tokens = max_tokens if max_tokens is not None else api_config.get("max_tokens")

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
