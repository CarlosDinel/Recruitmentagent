"""LangChain service implementation for unified AI interactions."""

import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

load_dotenv()

logger = logging.getLogger(__name__)


class LangChainService:
    """Unified LangChain service supporting multiple AI providers."""
    
    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ):
        """
        Initialize LangChain service.
        
        Args:
            provider: AI provider ('openai' or 'anthropic')
            model: Model name (defaults based on provider)
            temperature: Temperature for generation
            max_tokens: Maximum tokens per request
        """
        self.provider = provider.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        if self.provider == "openai":
            self.model = model or os.getenv('OPENAI_MODEL', 'gpt-5')
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
            
            self.llm = ChatOpenAI(
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key
            )
            
        elif self.provider == "anthropic":
            self.model = model or os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet')
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
            
            self.llm = ChatAnthropic(
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'openai' or 'anthropic'")
        
        logger.info(f"LangChainService initialized with provider: {self.provider}, model: {self.model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate text using LangChain.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Optional temperature override
            
        Returns:
            Generated text
        """
        try:
            messages: List[BaseMessage] = []
            
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            messages.append(HumanMessage(content=prompt))
            
            # Use custom temperature if provided
            if temperature is not None:
                if self.provider == "openai":
                    llm = ChatOpenAI(
                        model=self.model,
                        temperature=temperature,
                        max_tokens=self.max_tokens,
                        api_key=os.getenv('OPENAI_API_KEY')
                    )
                else:
                    llm = ChatAnthropic(
                        model=self.model,
                        temperature=temperature,
                        max_tokens=self.max_tokens,
                        api_key=os.getenv('ANTHROPIC_API_KEY')
                    )
            else:
                llm = self.llm
            
            response = llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating text with LangChain: {e}")
            raise
    
    def invoke(self, messages: List[BaseMessage]) -> str:
        """
        Invoke LLM with LangChain messages.
        
        Args:
            messages: List of LangChain message objects
            
        Returns:
            Generated text
        """
        try:
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")
            raise

