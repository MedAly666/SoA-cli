#!/usr/bin/env python3
"""
TOON Utilities for SOA-CLI

Wrapper functions for Token-Oriented Object Notation (TOON) format.
TOON reduces LLM token usage by 30-60% compared to JSON while maintaining
full data fidelity.

Key benefits for SOA-CLI:
- Reduced API costs when feeding data to LLMs
- Smaller artifact files
- Better performance with large paper datasets
- Maintains 100% compatibility (lossless conversion)
"""

from typing import Any
from pathlib import Path


def encode_toon(data: Any) -> str:
    """
    Convert Python object to TOON format string.
    
    Args:
        data: Python dict, list, or primitive to encode
    
    Returns:
        TOON-formatted string
    """
    try:
        from toon_parser import stringify_advanced
        return stringify_advanced(data)
    except (ImportError, NotImplementedError, Exception):
        # Fallback to JSON if TOON not installed or fails
        import json
        return json.dumps(data, indent=2)


def decode_toon(toon_str: str) -> Any:
    """
    Parse TOON format string to Python object.
    
    Args:
        toon_str: TOON-formatted string
    
    Returns:
        Python dict, list, or primitive
    """
    try:
        from toon_parser import parse_advanced
        return parse_advanced(toon_str)
    except (ImportError, NotImplementedError, Exception):
        # Fallback to JSON if TOON not installed or fails
        import json
        return json.loads(toon_str)


def dump_toon(data: Any, file_path: str | Path, **kwargs) -> None:
    """
    Write Python object to TOON file.
    
    Args:
        data: Python object to serialize
        file_path: Path to output file (.toon extension)
        **kwargs: Additional arguments (for compatibility, ignored)
    """
    toon_str = encode_toon(data)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(toon_str)


def load_toon(file_path: str | Path) -> Any:
    """
    Read TOON file and parse to Python object.
    
    Args:
        file_path: Path to TOON file
    
    Returns:
        Parsed Python object
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        toon_str = f.read()
    return decode_toon(toon_str)


def is_toon_available() -> bool:
    """Check if simple-toon library is installed."""
    try:
        import toon_parser
        return True
    except ImportError:
        return False


# Convenience aliases matching json module API
dumps = encode_toon
loads = decode_toon
dump = dump_toon
load = load_toon


def get_toon_file_extension() -> str:
    """Get the appropriate file extension based on availability."""
    return ".toon" if is_toon_available() else ".json"


def estimate_token_savings(json_data: Any) -> dict[str, int]:
    """
    Estimate token savings by converting to TOON.
    
    Args:
        json_data: Python object to analyze
    
    Returns:
        Dict with 'json_tokens', 'toon_tokens', 'saved_tokens', 'percent_saved'
    """
    import json
    
    # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
    json_str = json.dumps(json_data, indent=2)
    json_tokens = len(json_str) // 4
    
    if is_toon_available():
        toon_str = encode_toon(json_data)
        toon_tokens = len(toon_str) // 4
    else:
        # Conservative estimate: 40% reduction
        toon_tokens = int(json_tokens * 0.6)
    
    saved = json_tokens - toon_tokens
    percent = (saved / json_tokens * 100) if json_tokens > 0 else 0
    
    return {
        'json_tokens': json_tokens,
        'toon_tokens': toon_tokens,
        'saved_tokens': saved,
        'percent_saved': round(percent, 1)
    }
