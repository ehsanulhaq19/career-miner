from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Abstract base class defining the interface for LLM provider clients."""

    @abstractmethod
    async def generate_content(self, system_prompt: str, prompt: str) -> str:
        """
        Generate content using the LLM with the given system and user prompts.

        Args:
            system_prompt: Instructions that define the model's behavior and context.
            prompt: The user's input prompt for content generation.

        Returns:
            The generated text response from the LLM.
        """
        pass
