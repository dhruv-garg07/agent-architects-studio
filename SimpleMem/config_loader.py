"""
Config Loader - Load all configuration from environment variables (.env file)

This module replaces the config.py file and provides unified configuration
management by reading from environment variables, which come from the .env file.
"""

import os
from typing import Any

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_bool(key: str, default: bool = False) -> bool:
    """
    Get boolean value from environment variable
    
    Args:
        key: Environment variable name
        default: Default value if not found
    
    Returns:
        Boolean value
    """
    value = os.environ.get(key, str(default))
    if isinstance(value, bool):
        return value
    return value.lower() in ('true', '1', 'yes', 'on')


def get_int(key: str, default: int = 0) -> int:
    """
    Get integer value from environment variable
    
    Args:
        key: Environment variable name
        default: Default value if not found
    
    Returns:
        Integer value
    """
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def get_str(key: str, default: str = "") -> str:
    """
    Get string value from environment variable
    
    Args:
        key: Environment variable name
        default: Default value if not found
    
    Returns:
        String value
    """
    value = os.environ.get(key, default)
    # Handle None case for optional URLs
    if value in ('None', 'none', ''):
        return None if key.endswith('_URL') or key.endswith('_BASE_URL') else value
    return value


# ============================================================================
# LLM Configuration
# ============================================================================
OPENAI_API_KEY = get_str("OPENAI_API_KEY", "")
OPENAI_BASE_URL = get_str("OPENAI_BASE_URL")
LLM_MODEL = get_str("LLM_MODEL", "ServiceNow-AI/Apriel-1.5-15b-Thinker")
TOGETHER_API_KEY = get_str("TOGETHER_API_KEY", "")

# Embedding model (local, no API needed)
EMBEDDING_MODEL = get_str("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSION = get_int("EMBEDDING_DIMENSION", 384)
EMBEDDING_CONTEXT_LENGTH = get_int("EMBEDDING_CONTEXT_LENGTH", 32768)
REMOTE_EMBEDDING_URL = get_str("REMOTE_EMBEDDING_URL", "https://iotacluster-embedding-model.hf.space/gradio_api/call/embed_dense")
REMOTE_EMBEDDING_DIMENSION = get_int("REMOTE_EMBEDDING_DIMENSION", 768)

# ============================================================================
# Advanced LLM Features
# ============================================================================
ENABLE_THINKING = get_bool("ENABLE_THINKING", False)
USE_STREAMING = get_bool("USE_STREAMING", True)
USE_JSON_FORMAT = get_bool("USE_JSON_FORMAT", False)

# ============================================================================
# Memory Building Parameters
# ============================================================================
WINDOW_SIZE = get_int("WINDOW_SIZE", 40)
OVERLAP_SIZE = get_int("OVERLAP_SIZE", 2)

# ============================================================================
# Retrieval Parameters
# ============================================================================
SEMANTIC_TOP_K = get_int("SEMANTIC_TOP_K", 25)
KEYWORD_TOP_K = get_int("KEYWORD_TOP_K", 5)
STRUCTURED_TOP_K = get_int("STRUCTURED_TOP_K", 5)

# ============================================================================
# Database Configuration
# ============================================================================
LANCEDB_PATH = get_str("LANCEDB_PATH", "./lancedb_data")
MEMORY_TABLE_NAME = get_str("MEMORY_TABLE_NAME", "memory_entries")

# ============================================================================
# Parallel Processing Configuration
# ============================================================================
ENABLE_PARALLEL_PROCESSING = get_bool("ENABLE_PARALLEL_PROCESSING", True)
MAX_PARALLEL_WORKERS = get_int("MAX_PARALLEL_WORKERS", 16)
ENABLE_PARALLEL_RETRIEVAL = get_bool("ENABLE_PARALLEL_RETRIEVAL", True)
MAX_RETRIEVAL_WORKERS = get_int("MAX_RETRIEVAL_WORKERS", 8)

# ============================================================================
# Planning and Reflection Configuration
# ============================================================================
ENABLE_PLANNING = get_bool("ENABLE_PLANNING", True)
ENABLE_REFLECTION = get_bool("ENABLE_REFLECTION", True)
MAX_REFLECTION_ROUNDS = get_int("MAX_REFLECTION_ROUNDS", 2)

# ============================================================================
# LLM-as-Judge Configuration
# ============================================================================
JUDGE_API_KEY = get_str("JUDGE_API_KEY")
JUDGE_BASE_URL = get_str("JUDGE_BASE_URL", "https://api.openai.com/v1/")
JUDGE_MODEL = get_str("JUDGE_MODEL", "gpt-4.1-mini")
JUDGE_ENABLE_THINKING = get_bool("JUDGE_ENABLE_THINKING", False)
JUDGE_USE_STREAMING = get_bool("JUDGE_USE_STREAMING", False)
JUDGE_TEMPERATURE = float(os.environ.get("JUDGE_TEMPERATURE", "0.3"))

# ============================================================================
# Supabase Configuration
# ============================================================================
SUPABASE_URL = get_str("SUPABASE_URL", "")
SUPABASE_ANON_KEY = get_str("SUPABASE_ANON_KEY", "")

# ============================================================================
# ChromaDB Configuration
# ============================================================================
CHROMA_API_KEY = get_str("CHROMA_API_KEY", "")
CHROMA_TENANT = get_str("CHROMA_TENANT", "")
CHROMA_DATABASE = get_str("CHROMA_DATABASE", "")
CHROMA_DATABASE_CHAT_HISTORY = get_str("CHROMA_DATABASE_CHAT_HISTORY", "chat_history")
CHROMA_DATABASE_MANUAL_DATA = get_str("CHROMA_DATABASE_MANUAL_DATA", "manual_data")
CHROMA_DATABASE_FILE_DATA = get_str("CHROMA_DATABASE_FILE_DATA", "file_data")

# ============================================================================
# Email Configuration
# ============================================================================
SENDER_EMAIL = get_str("SENDER_EMAIL", "")
SENDER_EMAIL_PASSWORD = get_str("SENDER_EMAIL_PASSWORD", "")
