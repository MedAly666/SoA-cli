"""
Unified LLM Client for SOA-CLI.

Provides a single interface for calling different LLM providers via their CLI tools.
Includes retry logic, error handling, and provider availability checking.
"""

import subprocess
import time
import os
import shutil
from typing import Optional


class LLMClient:
    """
    Unified client for calling LLM CLI tools.
    
    Supports multiple providers: claude, gemini, qwen, gpt, glm
    All calls route through subprocess to the respective CLI binary.
    """
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, 
                 timeout: Optional[int] = None):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider (claude/gemini/qwen/gpt/glm). Defaults to LLM_PROVIDER env var.
            model: Model name. Defaults to LLM_MODEL env var.
            timeout: Timeout in seconds. Defaults to LLM_TIMEOUT env var (default: 120).
        """
        self.provider = provider or os.getenv('LLM_PROVIDER', 'qwen')
        self.model = model or os.getenv('LLM_MODEL')
        self.timeout = timeout or int(os.getenv('LLM_TIMEOUT', '120'))
        self.max_retries = 3
        self.retry_delays = [2, 4, 8]  # Exponential backoff
        
    def call(self, system: str, user: str) -> str:
        """
        Call LLM with system and user prompts.
        
        Args:
            system: System prompt
            user: User prompt
            
        Returns:
            LLM response text
            
        Raises:
            RuntimeError: If all retry attempts fail
        """
        # Combine prompts based on provider format
        combined_prompt = self._combine_prompts(system, user)
        
        # Try calling LLM with retries
        for attempt in range(self.max_retries):
            try:
                result = self._call_cli(combined_prompt)
                return result
                
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    print(f"  [Retry {attempt + 1}/{self.max_retries}] LLM call failed, "
                          f"retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    # Max retries exhausted
                    error_msg = (
                        f"LLM call failed after {self.max_retries} attempts\n"
                        f"Provider: {self.provider}\n"
                        f"Prompt length: system={len(system)} chars, user={len(user)} chars\n"
                        f"Error: {str(e)}"
                    )
                    return f"__LLM_FAILURE__: {error_msg}"
            
            except Exception as e:
                # Non-retryable error
                error_msg = (
                    f"LLM call failed with non-retryable error\n"
                    f"Provider: {self.provider}\n"  
                    f"Error: {str(e)}"
                )
                return f"__LLM_FAILURE__: {error_msg}"
        
        # Should never reach here
        return "__LLM_FAILURE__: Unknown error"
    
    def _combine_prompts(self, system: str, user: str) -> str:
        """
        Combine system and user prompts in provider-specific format.
        
        Different CLIs may expect different input formats.
        """
        if self.provider == 'claude':
            # Claude CLI accepts system and user separately
            # We'll combine them with clear separation
            return f"""System Instructions:
{system}

User Request:
{user}"""
        
        elif self.provider == 'gemini':
            # Gemini CLI format
            return f"""<system>
{system}
</system>

<user>
{user}
</user>"""
        
        elif self.provider in ['qwen', 'gpt', 'glm']:
            # Most CLIs accept a simple combined prompt
            return f"""{system}

{user}"""
        
        else:
            # Default: simple combination
            return f"""{system}

{user}"""
    
    def _call_cli(self, prompt: str) -> str:
        """
        Call the CLI binary via subprocess.
        
        Args:
            prompt: Combined prompt text
            
        Returns:
            CLI output text
            
        Raises:
            subprocess.TimeoutExpired: If timeout occurs
            subprocess.CalledProcessError: If CLI returns non-zero
        """
        # Build command based on provider
        cmd = self._build_command()
        
        # Execute subprocess
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Check for errors
        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "No error output"
            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                output=result.stdout,
                stderr=f"CLI failed: {stderr}"
            )
        
        # Return cleaned output
        output = result.stdout.strip()
        return self._clean_output(output)
    
    def _build_command(self) -> list:
        """
        Build CLI command based on provider and model.
        
        Returns:
            Command list for subprocess
        """
        if self.provider == 'claude':
            cmd = ['claude']
            if self.model:
                cmd.extend(['-m', self.model])
            # Claude uses -p for prompt via stdin, -y for auto-confirm
            cmd.extend(['-y'])
            
        elif self.provider == 'gemini':
            cmd = ['gemini']
            if self.model:
                cmd.extend(['--model', self.model])
            cmd.extend(['-y'])  # Auto-confirm
            
        elif self.provider == 'qwen':
            cmd = ['qwen']
            if self.model:
                cmd.extend(['-m', self.model])
            cmd.extend(['-y'])  # Auto-confirm
            
        elif self.provider == 'gpt':
            cmd = ['gpt']
            if self.model:
                cmd.extend(['-m', self.model])
            cmd.extend(['-y'])
            
        elif self.provider == 'glm':
            cmd = ['glm']
            if self.model:
                cmd.extend(['--model', self.model])
            cmd.extend(['-y'])
            
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        return cmd
    
    def _clean_output(self, output: str) -> str:
        """
        Clean LLM output by removing markdown code blocks if present.
        
        Args:
            output: Raw CLI output
            
        Returns:
            Cleaned output text
        """
        # Remove markdown code blocks (```json ... ```)
        if output.startswith("```"):
            lines = output.split("\n")
            start_idx = 1
            end_idx = len(lines) - 1
            
            # Find closing ```
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end_idx = i
                    break
            
            output = "\n".join(lines[start_idx:end_idx])
        
        return output.strip()


def check_cli_available(provider: str) -> bool:
    """
    Check if the CLI binary for a provider is available.
    
    Args:
        provider: Provider name (claude/gemini/qwen/gpt/glm)
        
    Returns:
        True if CLI is available, False otherwise
    """
    binary_map = {
        'claude': 'claude',
        'gemini': 'gemini',
        'qwen': 'qwen',
        'gpt': 'gpt',
        'glm': 'glm'
    }
    
    binary = binary_map.get(provider)
    if not binary:
        return False
    
    # Check if binary exists in PATH
    return shutil.which(binary) is not None


def verify_provider_or_exit(provider: str):
    """
    Verify provider CLI is available, exit with error if not.
    
    Args:
        provider: Provider name
    """
    if not check_cli_available(provider):
        print(f"\n❌ ERROR: CLI binary '{provider}' not found in PATH")
        print(f"\nThe LLM_PROVIDER is set to '{provider}' but the '{provider}' ")
        print(f"command-line tool is not installed or not in your PATH.")
        print(f"\nPlease either:")
        print(f"  1. Install the '{provider}' CLI tool")
        print(f"  2. Change LLM_PROVIDER in .env to a provider you have installed")
        print(f"\nAvailable providers: claude, gemini, qwen, gpt, glm")
        exit(1)
