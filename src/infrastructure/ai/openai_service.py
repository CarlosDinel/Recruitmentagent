"""OpenAI service implementation."""

import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

load_dotenv()

logger = logging.getLogger(__name__)


class OpenAIService:
    """OpenAI service for LLM interactions."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ):
        """
        Initialize OpenAI service.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (defaults to OPENAI_MODEL env var or 'gpt-5')
            temperature: Temperature for generation
            max_tokens: Maximum tokens per request
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-5')
        self.temperature = temperature or float(os.getenv('OPENAI_TEMPERATURE', '0.3'))
        self.max_tokens = max_tokens or int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=self.api_key
        )
        
        logger.info(f"OpenAIService initialized with model: {self.model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate text using OpenAI.
        
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
                llm = ChatOpenAI(
                    model=self.model,
                    temperature=temperature,
                    max_tokens=self.max_tokens,
                    api_key=self.api_key
                )
            else:
                llm = self.llm
            
            response = llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating text with OpenAI: {e}")
            raise
    
    def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None
    ) -> List[str]:
        """
        Generate text for multiple prompts.
        
        Args:
            prompts: List of user prompts
            system_prompt: Optional system prompt
            
        Returns:
            List of generated texts
        """
        results = []
        for prompt in prompts:
            try:
                result = self.generate(prompt, system_prompt)
                results.append(result)
            except Exception as e:
                logger.error(f"Error generating text for prompt: {e}")
                results.append("")
        return results
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Chat with OpenAI using message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            
        Returns:
            Assistant response
        """
        try:
            langchain_messages: List[BaseMessage] = []
            
            if system_prompt:
                langchain_messages.append(SystemMessage(content=system_prompt))
            
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                
                if role == 'system':
                    langchain_messages.append(SystemMessage(content=content))
                elif role == 'user':
                    langchain_messages.append(HumanMessage(content=content))
                elif role == 'assistant':
                    from langchain_core.messages import AIMessage
                    langchain_messages.append(AIMessage(content=content))
            
            response = self.llm.invoke(langchain_messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error in chat with OpenAI: {e}")
            raise

