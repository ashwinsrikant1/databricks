"""
Utility functions for MCP agents.
"""

import asyncio
import concurrent.futures
from typing import Any, Dict, List, Optional


def extract_response_content(result: Any) -> str:
    """
    Extract text content from MCP server responses.

    Args:
        result: Response from MCP server

    Returns:
        Extracted text content as string
    """
    if hasattr(result, 'content') and result.content:
        if isinstance(result.content, list) and len(result.content) > 0:
            if hasattr(result.content[0], 'text'):
                return result.content[0].text

    return str(result)


def handle_async_in_sync(async_func, *args, **kwargs):
    """
    Execute an async function in a sync context using a new event loop.

    This is needed for Jupyter environments where there's already a running event loop.

    Args:
        async_func: The async function to execute
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        The result of the async function
    """
    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            new_loop.close()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_new_loop)
        return future.result(timeout=120)  # 2 minute timeout


def parse_tool_parameters(tool_schema: Dict) -> Dict[str, Any]:
    """
    Parse tool schema to extract parameter information.

    Args:
        tool_schema: Tool input schema from MCP server

    Returns:
        Dictionary of parameter information
    """
    params = {}

    if isinstance(tool_schema, dict):
        properties = tool_schema.get('properties', {})
        required = tool_schema.get('required', [])

        for param_name, param_info in properties.items():
            params[param_name] = {
                'type': param_info.get('type', 'string'),
                'description': param_info.get('description', ''),
                'required': param_name in required
            }

    return params


def validate_environment_config(required_vars: List[str]) -> tuple[bool, List[str]]:
    """
    Validate that required environment variables are set.

    Args:
        required_vars: List of required environment variable names

    Returns:
        Tuple of (is_valid, missing_vars)
    """
    import os

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    return len(missing_vars) == 0, missing_vars


def sanitize_model_name(name: str) -> str:
    """
    Sanitize a string to be used as a model name in MLflow/Unity Catalog.

    Args:
        name: Input name string

    Returns:
        Sanitized name suitable for model registration
    """
    import re

    # Replace special characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)

    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')

    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = f"agent_{sanitized}"

    return sanitized or "mcp_agent"