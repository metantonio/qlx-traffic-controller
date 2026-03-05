from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from backend.core.config import settings

class LLMProvider:
    """Abstraction layer for language models."""
    
    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider or settings.DEFAULT_PROVIDER
        self.model = model or settings.DEFAULT_MODEL
        
        self._client = self._initialize_client()
        
    def _initialize_client(self):
        if self.provider == "ollama":
            return ChatOllama(model=self.model, base_url=settings.OLLAMA_BASE_URL)
        elif self.provider in ["openai", "anthropic"]:
            raise NotImplementedError(f"Provider {self.provider} support is pending.")
        else:
            raise ValueError(f"Unknown LLM Provider {self.provider}")
            
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Synchronous generation."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = self._client.invoke(messages)
        return response.content
        
    async def agenerate(self, system_prompt: str, user_prompt: str) -> str:
        """Asynchronous generation."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = await self._client.ainvoke(messages)
        return response.content
