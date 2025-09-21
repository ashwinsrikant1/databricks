"""
MCP Agent Package

A flexible framework for creating tool-calling agents that integrate with
Multiple MCP (Model Context Protocol) servers.

Supports:
- Multiple MCP server types (Genie, custom servers, etc.)
- Databricks deployment via MLflow
- Local development and testing
- OAuth authentication
- Claude Sonnet 4 integration
"""

from .agent import MCPAgent, SingleTurnMCPAgent
from .mcp_client import MCPServerManager, GenieServerClient
from .utils import extract_response_content, handle_async_in_sync

__version__ = "1.0.0"
__all__ = [
    "MCPAgent",
    "SingleTurnMCPAgent",
    "MCPServerManager",
    "GenieServerClient",
    "extract_response_content",
    "handle_async_in_sync"
]