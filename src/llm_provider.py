#!/usr/bin/env python3
"""
Multi-Provider LLM Abstraction Layer

Supports: OpenAI (GPT), Anthropic (Claude), Google (Gemini), 
          DeepSeek, Qwen, GLM, and any OpenAI-compatible API
"""

import os
import subprocess
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, model: str, **kwargs):
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT models (gpt-4, gpt-4-turbo, gpt-3.5-turbo)."""
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            from openai import OpenAI
            
            client = OpenAI(base_url="https://openrouter.ai/api/v1",api_key=os.getenv("API_KEY"))
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 4096)
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")
    
    def is_available(self) -> bool:
        return bool(os.getenv("API_KEY"))


class AnthropicProvider(LLMProvider):
    """Anthropic Claude models (claude-3-opus, claude-3-sonnet, claude-3-haiku)."""
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            from anthropic import Anthropic
            
            client = Anthropic(api_key=os.getenv("API_KEY"))
            
            response = client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                temperature=kwargs.get("temperature", 0.1),
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")
    
    def is_available(self) -> bool:
        return bool(os.getenv("API_KEY"))


class GoogleProvider(LLMProvider):
    """Google Gemini models (gemini-pro, gemini-1.5-pro)."""
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("API_KEY"))
            
            model = genai.GenerativeModel(self.model)
            
            # Combine system prompt and user prompt
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            response = model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": kwargs.get("temperature", 0.1),
                    "max_output_tokens": kwargs.get("max_tokens", 4096)
                }
            )
            
            return response.text
        except Exception as e:
            raise RuntimeError(f"Google API error: {e}")
    
    def is_available(self) -> bool:
        return bool(os.getenv("API_KEY"))


class DeepSeekProvider(LLMProvider):
    """DeepSeek models (deepseek-chat, deepseek-coder) - OpenAI-compatible API."""
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=os.getenv("API_KEY"),
                base_url="https://api.deepseek.com"
            )
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 4096)
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"DeepSeek API error: {e}")
    
    def is_available(self) -> bool:
        return bool(os.getenv("API_KEY"))


class QwenProvider(LLMProvider):
    """Qwen models via local CLI or API."""
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        # Try API first if available
        if os.getenv("API_KEY"):
            return self._generate_via_api(prompt, system_prompt, **kwargs)
        else:
            return self._generate_via_cli(prompt, system_prompt, **kwargs)
    
    def _generate_via_api(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Use Qwen API (OpenAI-compatible)."""
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=os.getenv("API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.1)
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Qwen API error: {e}")
    
    def _generate_via_cli(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Use local Qwen CLI."""
        try:
            # Combine prompts
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            cmd = ["qwen", "-m", self.model, "-y"] if self.model else ["qwen", "-y"]
            
            result = subprocess.run(
                cmd,
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=kwargs.get("timeout", 300)
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Qwen CLI error: {result.stderr}")
            
            return result.stdout.strip()
        except Exception as e:
            raise RuntimeError(f"Qwen CLI error: {e}")
    
    def is_available(self) -> bool:
        # Check if API key exists or CLI is available
        if os.getenv("API_KEY"):
            return True
        try:
            subprocess.run(["qwen", "--version"], capture_output=True, timeout=5)
            return True
        except:
            return False


class GLMProvider(LLMProvider):
    """GLM models (ChatGLM) - OpenAI-compatible API."""
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=os.getenv("API_KEY"),
                base_url="https://open.bigmodel.cn/api/paas/v4/"
            )
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.1)
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"GLM API error: {e}")
    
    def is_available(self) -> bool:
        return bool(os.getenv("API_KEY"))


class OllamaProvider(LLMProvider):
    """Ollama local models (llama2, mistral, etc.)."""
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            import requests
            
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt or "",
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.1)
                }
            }
            
            response = requests.post(f"{base_url}/api/generate", json=payload)
            response.raise_for_status()
            
            return response.json()["response"]
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")
    
    def is_available(self) -> bool:
        try:
            import requests
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            response = requests.get(f"{base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False


# Provider registry
PROVIDERS = {
    "openai": OpenAIProvider,
    "gpt": OpenAIProvider,  # Alias
    "anthropic": AnthropicProvider,
    "claude": AnthropicProvider,  # Alias
    "google": GoogleProvider,
    "gemini": GoogleProvider,  # Alias
    "deepseek": DeepSeekProvider,
    "qwen": QwenProvider,
    "glm": GLMProvider,
    "chatglm": GLMProvider,  # Alias
    "ollama": OllamaProvider,
}


def get_llm_provider(provider: str, model: str, **kwargs) -> LLMProvider:
    """
    Factory function to get LLM provider.
    
    Args:
        provider: Provider name (openai, claude, gemini, deepseek, qwen, glm, ollama)
        model: Model name (e.g., gpt-4, claude-3-opus-20240229, gemini-pro)
        **kwargs: Additional provider-specific configuration
    
    Returns:
        LLMProvider instance
    
    Examples:
        >>> llm = get_llm_provider("openai", "gpt-4")
        >>> llm = get_llm_provider("claude", "claude-3-opus-20240229")
        >>> llm = get_llm_provider("qwen", "qwen-turbo")
    """
    provider_lower = provider.lower()
    
    if provider_lower not in PROVIDERS:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Available: {', '.join(PROVIDERS.keys())}"
        )
    
    provider_class = PROVIDERS[provider_lower]
    instance = provider_class(model, **kwargs)
    
    if not instance.is_available():
        raise RuntimeError(
            f"{provider} provider is not configured. "
            f"Please set the required API key or install the dependency."
        )
    
    return instance


def get_default_llm() -> LLMProvider:
    """
    Get default LLM from environment variables.
    Checks LLM_PROVIDER and LLM_MODEL env vars, falls back to Qwen CLI.
    """
    provider = os.getenv("LLM_PROVIDER", "qwen")
    model = os.getenv("LLM_MODEL", "qwen-turbo")
    
    return get_llm_provider(provider, model)
