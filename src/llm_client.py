#!/usr/bin/env python3
"""
Unified LLM Client with SDK-based calls and retry logic.

This module provides a simplified interface for calling LLMs with:
- Direct SDK calls instead of subprocess/CLI
- Retry logic with exponential backoff
- Unified error handling
- Support for all providers (OpenAI, Claude, Gemini, DeepSeek, Qwen, GLM, Ollama)
"""

import os
import time
import logging
from typing import Optional
from pathlib import Path

# Import the provider abstraction layer
from src.llm_provider import get_llm_provider, get_default_llm, LLMProvider

# Get logger
logger = logging.getLogger('SOA-CLI.LLMClient')


class LLMClient:
    """
    Unified LLM client with retry logic and error handling.
    
    Usage:
        client = LLMClient()
        response = client.call(
            system="You are a helpful assistant",
            user="What is 2+2?"
        )
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        timeout: Optional[int] = None
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider name (openai, claude, gemini, etc.)
                     If None, uses LLM_PROVIDER from environment
            model: Model name (gpt-4, claude-3-opus, etc.)
                   If None, uses LLM_MODEL from environment
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Initial delay between retries in seconds (default: 1.0)
            max_delay: Maximum delay between retries in seconds (default: 60.0)
            timeout: Timeout for LLM calls in seconds
                     If None, uses LLM_TIMEOUT from environment (default: 300)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        # Get timeout from parameter or environment
        if timeout is None:
            timeout = int(os.getenv('LLM_TIMEOUT', '300'))
        self.timeout = timeout
        
        # Initialize provider
        if provider is None:
            provider = os.getenv('LLM_PROVIDER', 'qwen')
        if model is None:
            model = os.getenv('LLM_MODEL', 'qwen-turbo')
        
        self.provider_name = provider
        self.model_name = model
        
        try:
            self.provider: LLMProvider = get_llm_provider(provider, model)
            logger.info(f"LLMClient initialized: provider={provider}, model={model}, timeout={timeout}s, max_retries={max_retries}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider '{provider}' with model '{model}': {e}")
            raise RuntimeError(
                f"Failed to initialize LLM provider '{provider}' with model '{model}': {e}\n"
                f"Please check your API_KEY environment variable and provider configuration."
            )
    
    def call(
        self,
        system: str,
        user: str,
        temperature: float = 0.1,
        max_tokens: int = 4096
    ) -> str:
        """
        Call LLM with retry logic and exponential backoff.
        
        Args:
            system: System prompt (instructions for the LLM)
            user: User prompt (the actual input/question)
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens in response
        
        Returns:
            str: LLM response text
        
        Raises:
            RuntimeError: If all retry attempts fail
        """
        # Log call details
        logger.debug(f"LLM Call starting:")
        logger.debug(f"  Provider: {self.provider_name}")
        logger.debug(f"  Model: {self.model_name}")
        logger.debug(f"  System prompt: {len(system):,} chars")
        logger.debug(f"  User prompt: {len(user):,} chars")
        logger.debug(f"  Temperature: {temperature}")
        logger.debug(f"  Max tokens: {max_tokens}")
        
        last_error = None
        call_start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                attempt_start_time = time.time()
                
                # Call the provider's generate method
                response = self.provider.generate(
                    prompt=user,
                    system_prompt=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout
                )
                
                # Success - log and return response
                attempt_duration = time.time() - attempt_start_time
                total_duration = time.time() - call_start_time
                
                logger.debug(f"LLM Call succeeded:")
                logger.debug(f"  Attempt: {attempt + 1}/{self.max_retries}")
                logger.debug(f"  Response: {len(response):,} chars")
                logger.debug(f"  Duration: {attempt_duration:.2f}s (total: {total_duration:.2f}s)")
                
                return response
                
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Check if this is a retryable error
                is_retryable = any(keyword in error_msg for keyword in [
                    'timeout', 'rate limit', 'overloaded', 'connection',
                    'network', 'temporary', '429', '500', '502', '503', '504'
                ])
                
                if attempt < self.max_retries - 1 and is_retryable:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.base_delay * (2 ** attempt),
                        self.max_delay
                    )
                    
                    logger.warning(
                        f"LLM Call failed (attempt {attempt + 1}/{self.max_retries}): {type(e).__name__}: {e}"
                    )
                    logger.info(f"Retrying in {delay:.1f}s...")
                    print(f"  [LLM Retry] Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                    print(f"  [LLM Retry] Retrying in {delay:.1f}s...")
                    
                    time.sleep(delay)
                else:
                    # Non-retryable error or last attempt
                    break
        
        # All retries failed
        total_duration = time.time() - call_start_time
        logger.error(f"LLM Call failed after {self.max_retries} attempts (took {total_duration:.2f}s)")
        logger.error(f"Provider: {self.provider_name}, Model: {self.model_name}")
        logger.error(f"Last error: {type(last_error).__name__}: {last_error}")
        
        raise RuntimeError(
            f"LLM call failed after {self.max_retries} attempts.\n"
            f"Provider: {self.provider_name}, Model: {self.model_name}\n"
            f"Last error: {last_error}"
        )
    
    def call_with_prompt_file(
        self,
        system_prompt_path: str,
        user_data: dict,
        temperature: float = 0.1,
        max_tokens: int = 4096
    ) -> str:
        """
        Call LLM using a system prompt file and structured user data.
        
        This is a convenience method for the common pattern of:
        1. Load system prompt from file
        2. Format user data as JSON
        3. Combine and call LLM
        
        Args:
            system_prompt_path: Path to system prompt file
            user_data: Dictionary of user input data (will be JSON-formatted)
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
        
        Returns:
            str: LLM response text
        """
        import json
        
        # Load system prompt
        with open(system_prompt_path, 'r', encoding='utf-8') as f:
            system_text = f.read()
        
        # Format user data as JSON
        user_json = json.dumps(user_data, indent=2)
        user_prompt = f"""# Input

```json
{user_json}
```

Generate the output as valid JSON. Return ONLY the JSON with no markdown formatting."""
        
        # Call LLM
        return self.call(
            system=system_text,
            user=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def __repr__(self) -> str:
        return (
            f"LLMClient(provider={self.provider_name}, "
            f"model={self.model_name}, "
            f"max_retries={self.max_retries})"
        )


def create_default_client() -> LLMClient:
    """
    Create an LLM client with default configuration from environment.
    
    Returns:
        LLMClient configured from LLM_PROVIDER and LLM_MODEL env vars
    """
    return LLMClient()


# Convenience function for quick calls
def call_llm(system: str, user: str, **kwargs) -> str:
    """
    Quick LLM call with default configuration.
    
    Args:
        system: System prompt
        user: User prompt
        **kwargs: Additional arguments passed to LLMClient.call()
    
    Returns:
        str: LLM response
    
    Example:
        >>> response = call_llm(
        ...     system="You are a helpful assistant",
        ...     user="What is 2+2?"
        ... )
    """
    client = create_default_client()
    return client.call(system, user, **kwargs)
