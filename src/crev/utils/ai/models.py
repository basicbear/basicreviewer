"""LLM model configurations for different providers."""

import os
import subprocess
from typing import Any, Iterator, List, Optional

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

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


class CLIChatModel(BaseChatModel):
    """A chat model that wraps a CLI command (e.g., claude CLI)."""

    command_name: str = "claude"
    cli_args: List[str] = []

    @property
    def _llm_type(self) -> str:
        return "cli-chat-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response using the CLI command."""
        # Convert messages to a single prompt string
        prompt = self._messages_to_prompt(messages)

        # Build the command
        cmd = [self.command_name, "-p", prompt] + self.cli_args

        # Run the CLI command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse the output
        response_text = result.stdout.strip()

        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert a list of messages to a single prompt string."""
        prompt_parts = []
        for msg in messages:
            if msg.type == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.type == "human":
                prompt_parts.append(f"Human: {msg.content}")
            elif msg.type == "ai":
                prompt_parts.append(f"Assistant: {msg.content}")
            else:
                prompt_parts.append(str(msg.content))
        return "\n\n".join(prompt_parts)


def get_cli_model(cli_config: dict) -> BaseChatModel:
    """Get a CLI-based model instance.

    Args:
        cli_config: CLI configuration dictionary with command_name and options

    Returns:
        CLIChatModel instance configured with the specified parameters
    """
    command_name = cli_config.get("command_name", "claude")

    # Build CLI arguments from config options
    cli_args = []
    for key, value in cli_config.items():
        if key == "command_name":
            continue
        # Add the flag and its value
        cli_args.append(str(key))
        cli_args.append(str(value))

    return CLIChatModel(command_name=command_name, cli_args=cli_args)
