from abc import ABC, abstractmethod


class LlmProvider(ABC):
    @abstractmethod
    async def complete_json(self, system: str, user: str) -> str:
        """Ask the model to answer with a JSON object; return the raw text of the answer."""
