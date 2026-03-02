#!/usr/bin/env python3
"""
Enhanced Logging Configuration for SOA-CLI

Provides detailed logging with:
- Console output (INFO level)
- File output (DEBUG level) - saved to logs/soa_pipeline.log
- Structured formatting with timestamps
- Performance tracking
- Operation context tracking
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional
from datetime import datetime
import sys


class PerformanceLogger:
    """Context manager for timing operations."""
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(self.level, f"→ Starting: {self.operation}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type is None:
            self.logger.log(self.level, f"✓ Completed: {self.operation} (took {elapsed:.2f}s)")
        else:
            self.logger.error(f"✗ Failed: {self.operation} (after {elapsed:.2f}s) - {exc_val}")
        return False


def setup_logging(log_level: str = None, log_file: str = None) -> logging.Logger:
    """
    Configure logging for SOA-CLI pipeline.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR) - from env or param
        log_file: Path to log file (optional, defaults to logs/soa_pipeline_YYYYMMDD_HHMMSS.log)
    
    Returns:
        Configured logger instance
    """
    # Get log level from environment or parameter
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create log file with timestamp
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"soa_pipeline_{timestamp}.log"
    
    # Create logger
    logger = logging.getLogger('SOA-CLI')
    logger.setLevel(logging.DEBUG)  # Capture everything, filter in handlers
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler (INFO level by default)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_format = logging.Formatter(
        '%(levelname)s | %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (DEBUG level - captures everything)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Log initialization
    logger.info("="*80)
    logger.info(f"SOA-CLI Pipeline Logging Initialized")
    logger.info(f"Log Level: {log_level} (console), DEBUG (file)")
    logger.info(f"Log File: {log_file}")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    return logger


def log_environment_config(logger: logging.Logger):
    """Log all environment configuration at startup."""
    logger.info("\n" + "="*80)
    logger.info("ENVIRONMENT CONFIGURATION")
    logger.info("="*80)
    
    # LLM Configuration
    logger.info("LLM Configuration:")
    logger.info(f"  Provider: {os.getenv('LLM_PROVIDER', 'qwen')}")
    logger.info(f"  Model: {os.getenv('LLM_MODEL', 'default')}")
    logger.info(f"  Timeout: {os.getenv('LLM_TIMEOUT', '300')}s")
    api_key = os.getenv('API_KEY', 'NOT_SET')
    logger.info(f"  API Key: {'SET' if api_key != 'NOT_SET' else 'NOT_SET'} ({'*' * 8 if api_key != 'NOT_SET' else 'MISSING'})")
    
    # Pipeline Configuration
    logger.info("\nPipeline Configuration:")
    logger.info(f"  Max Workers: {os.getenv('MAX_WORKERS', '10')}")
    logger.info(f"  Max PDF Chars: {os.getenv('MAX_PDF_CHARS', '30000')}")
    cluster_count = os.getenv('CLUSTER_COUNT', 'AUTO-DETECT')
    logger.info(f"  Cluster Count: {cluster_count}")
    logger.info(f"  Citation Style: {os.getenv('CITATION_STYLE', 'ieee')}")
    
    # Directories
    logger.info("\nDirectory Structure:")
    logger.info(f"  Papers: {os.path.abspath('papers/')}")
    logger.info(f"  Artifacts: {os.path.abspath('artifacts/')}")
    logger.info(f"  Prompts: {os.path.abspath('prompts/')}")
    logger.info(f"  Logs: {os.path.abspath('logs/')}")
    
    # Python Environment
    logger.info("\nPython Environment:")
    logger.info(f"  Version: {sys.version.split()[0]}")
    logger.info(f"  Executable: {sys.executable}")
    logger.info(f"  Working Directory: {os.getcwd()}")
    
    logger.info("="*80 + "\n")


def log_operation_start(logger: logging.Logger, operation: str, details: dict = None):
    """Log the start of a major operation with details."""
    logger.info(f"\n{'─'*80}")
    logger.info(f"OPERATION START: {operation}")
    if details:
        for key, value in details.items():
            logger.info(f"  {key}: {value}")
    logger.info(f"{'─'*80}")


def log_operation_end(logger: logging.Logger, operation: str, success: bool = True, 
                      duration: float = None, details: dict = None):
    """Log the end of a major operation with results."""
    status = "✓ SUCCESS" if success else "✗ FAILED"
    logger.info(f"{'─'*80}")
    logger.info(f"OPERATION END: {operation} - {status}")
    if duration is not None:
        logger.info(f"  Duration: {duration:.2f}s")
    if details:
        for key, value in details.items():
            logger.info(f"  {key}: {value}")
    logger.info(f"{'─'*80}\n")


def log_llm_call(logger: logging.Logger, provider: str, model: str, operation: str,
                 system_chars: int = None, user_chars: int = None, 
                 response_chars: int = None, duration: float = None,
                 retry_count: int = 0):
    """Log details of an LLM call."""
    logger.debug(f"LLM Call: {operation}")
    logger.debug(f"  Provider: {provider}")
    logger.debug(f"  Model: {model}")
    if system_chars:
        logger.debug(f"  System Prompt: {system_chars:,} chars")
    if user_chars:
        logger.debug(f"  User Prompt: {user_chars:,} chars")
    if response_chars:
        logger.debug(f"  Response: {response_chars:,} chars")
    if duration:
        logger.debug(f"  Duration: {duration:.2f}s")
    if retry_count > 0:
        logger.debug(f"  Retries: {retry_count}")


def log_file_operation(logger: logging.Logger, operation: str, file_path: str,
                       size: int = None, success: bool = True):
    """Log file I/O operations."""
    status = "✓" if success else "✗"
    msg = f"{status} {operation}: {file_path}"
    if size is not None:
        msg += f" ({size:,} bytes)"
    logger.debug(msg)


def log_pdf_extraction(logger: logging.Logger, pdf_path: str, pages_extracted: int,
                       total_pages: int, total_chars: int, was_truncated: bool,
                       original_chars: int = None):
    """Log PDF text extraction details."""
    logger.info(f"  PDF: {Path(pdf_path).name}")
    logger.info(f"    Pages: {pages_extracted}/{total_pages}")
    logger.info(f"    Characters: {total_chars:,}")
    if was_truncated:
        logger.warning(f"    ⚠️  TRUNCATED from {original_chars:,} chars")
        logger.warning(f"    Lost: {original_chars - total_chars:,} chars ({((original_chars - total_chars) / original_chars * 100):.1f}%)")
    logger.debug(f"    Full path: {pdf_path}")


def log_clustering_decision(logger: logging.Logger, optimal_k: int, scores: dict,
                            method: str = "silhouette"):
    """Log clustering analysis results."""
    logger.info(f"  Clustering Analysis ({method}):")
    logger.info(f"    Optimal k: {optimal_k}")
    logger.debug(f"    Scores: {scores}")
    # Log top 3 scores
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    for k, score in sorted_scores:
        marker = "→" if k == optimal_k else " "
        logger.info(f"    {marker} k={k}: score={score:.3f}")


def log_export_operation(logger: logging.Logger, format_name: str, output_path: str,
                        conversion_time: float = None, success: bool = True):
    """Log document export operations."""
    status = "✓" if success else "✗"
    msg = f"{status} Export ({format_name}): {output_path}"
    if conversion_time:
        msg += f" (took {conversion_time:.2f}s)"
    logger.info(f"  {msg}")


def log_state_transition(logger: logging.Logger, from_stage: str, to_stage: str,
                         papers_processed: int = None):
    """Log LangGraph state transitions."""
    logger.debug(f"State Transition: {from_stage} → {to_stage}")
    if papers_processed is not None:
        logger.debug(f"  Papers Processed: {papers_processed}")


def log_error(logger: logging.Logger, error: Exception, context: str = "",
              stack_trace: bool = True):
    """Log errors with context and optional stack trace."""
    logger.error(f"ERROR in {context}: {type(error).__name__}: {error}")
    if stack_trace:
        import traceback
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")


# Global logger instance (initialized in main)
_global_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get the global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = setup_logging()
    return _global_logger


def set_logger(logger: logging.Logger):
    """Set the global logger instance."""
    global _global_logger
    _global_logger = logger
