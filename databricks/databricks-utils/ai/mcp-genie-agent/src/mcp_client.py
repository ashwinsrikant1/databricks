"""
MCP client management for multiple server types.

This module provides an extensible framework for connecting to different
MCP servers (Genie, custom servers, etc.) and managing their tools.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Optional, Type
import concurrent.futures

from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient
from langchain_core.tools import BaseTool

from .utils import extract_response_content, handle_async_in_sync


class MCPServerClient(ABC):
    """
    Abstract base class for MCP server clients.

    This allows for easy extension to support different MCP server types.
    """

    def __init__(self, server_url: str, **kwargs):
        self.server_url = server_url
        self.client = None

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the MCP server."""
        pass

    @abstractmethod
    async def get_tools(self) -> List[Any]:
        """Get available tools from the server."""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call a tool on the server."""
        pass

    @abstractmethod
    def get_resources(self) -> List[Dict[str, Any]]:
        """Get resources needed for deployment."""
        pass


class GenieServerClient(MCPServerClient):
    """
    Client for Databricks Genie MCP servers.
    """

    def __init__(self, server_url: str, workspace_client: Optional[WorkspaceClient] = None):
        super().__init__(server_url)
        self.workspace_client = workspace_client or WorkspaceClient()

    async def connect(self) -> bool:
        """Connect to the Genie MCP server."""
        try:
            self.client = DatabricksMCPClient(
                server_url=self.server_url,
                workspace_client=self.workspace_client
            )
            return True
        except Exception as e:
            print(f"Failed to connect to Genie server: {e}")
            return False

    async def get_tools(self) -> List[Any]:
        """Get available tools from the Genie server."""
        if not self.client:
            await self.connect()

        try:
            # Use private async method to avoid event loop conflicts
            return await self.client._get_tools_async()
        except Exception as e:
            print(f"Error getting tools from Genie server: {e}")
            return []

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call a tool on the Genie server."""
        if not self.client:
            await self.connect()

        try:
            # Use private async method for Jupyter compatibility
            return await self.client._call_tools_async(tool_name, parameters)
        except Exception as e:
            print(f"Error calling tool {tool_name}: {e}")
            return f"Error: {e}"

    def get_resources(self) -> List[Dict[str, Any]]:
        """Get resources needed for deployment."""
        try:
            return self.client.get_databricks_resources() if self.client else []
        except Exception as e:
            print(f"Error getting resources: {e}")
            return []


class UnityCatalogMCPClient(MCPServerClient):
    """
    Client for Databricks Unity Catalog MCP server.

    Provides access to Unity Catalog functions as MCP tools.
    """

    def __init__(self, catalog: str, schema: str, workspace_client: Optional[WorkspaceClient] = None):
        # Construct Unity Catalog MCP server URL
        if workspace_client:
            workspace_host = workspace_client.config.host
        else:
            from databricks.sdk import WorkspaceClient
            workspace_client = WorkspaceClient()
            workspace_host = workspace_client.config.host

        server_url = f"{workspace_host}/api/2.0/mcp/functions/{catalog}/{schema}"
        super().__init__(server_url)

        self.catalog = catalog
        self.schema = schema
        self.workspace_client = workspace_client

    async def connect(self) -> bool:
        """Connect to the Unity Catalog MCP server."""
        try:
            self.client = DatabricksMCPClient(
                server_url=self.server_url,
                workspace_client=self.workspace_client
            )
            print(f"✅ Connected to Unity Catalog MCP server: {self.catalog}.{self.schema}")
            return True
        except Exception as e:
            print(f"Failed to connect to Unity Catalog MCP server {self.catalog}.{self.schema}: {e}")
            return False

    async def get_tools(self) -> List[Any]:
        """Get available Unity Catalog functions as tools."""
        if not self.client:
            await self.connect()

        try:
            # Use private async method to avoid event loop conflicts
            tools = await self.client._get_tools_async()
            print(f"Found {len(tools)} Unity Catalog functions in {self.catalog}.{self.schema}")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description[:100]}...")
            return tools
        except Exception as e:
            print(f"Error getting Unity Catalog functions from {self.catalog}.{self.schema}: {e}")
            return []

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call a Unity Catalog function with improved error handling."""
        if not self.client:
            await self.connect()

        try:
            # Try the standard MCP client method first
            result = await self.client._call_tools_async(tool_name, parameters)
            print(f"Called Unity Catalog function {tool_name} with result type: {type(result)}")
            return result
        except Exception as e:
            print(f"Error calling Unity Catalog function {tool_name}: {e}")

            # Try alternative approach with the sync method in a thread
            try:
                print(f"Attempting fallback sync call for {tool_name}...")
                import asyncio
                import concurrent.futures

                def sync_call():
                    return self.client.call_tool(tool_name, parameters)

                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(executor, sync_call)
                    print(f"Fallback successful for {tool_name}")
                    return result

            except Exception as fallback_error:
                print(f"Fallback also failed for {tool_name}: {fallback_error}")
                return f"Error: Unity Catalog function execution failed - {e}"

    def get_resources(self) -> List[Dict[str, Any]]:
        """Get resources needed for deployment."""
        try:
            return self.client.get_databricks_resources() if self.client else []
        except Exception as e:
            print(f"Error getting Unity Catalog resources: {e}")
            return []


class CustomMCPClient(MCPServerClient):
    """
    Client for custom MCP servers.

    This can be extended for other MCP server types in the future.
    """

    def __init__(self, server_url: str, auth_config: Optional[Dict] = None):
        super().__init__(server_url)
        self.auth_config = auth_config or {}

    async def connect(self) -> bool:
        """Connect to the custom MCP server."""
        # This would be implemented based on the specific custom server
        # For now, it's a placeholder
        print(f"Custom MCP client for {self.server_url} - implement as needed")
        return False

    async def get_tools(self) -> List[Any]:
        """Get available tools from the custom server."""
        # Implement based on custom server API
        return []

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call a tool on the custom server."""
        # Implement based on custom server API
        return "Custom server tool call - implement as needed"

    def get_resources(self) -> List[Dict[str, Any]]:
        """Get resources needed for deployment."""
        # Return custom resources if needed
        return []


class MCPTool(BaseTool):
    """
    LangChain tool wrapper for MCP server tools.

    This creates a unified interface for tools from any MCP server type.
    """

    name: str
    description: str
    # Use ClassVar to indicate these are not Pydantic fields
    tool_def: ClassVar[Any]
    server_client: ClassVar[MCPServerClient]

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, tool_def: Any, server_client: MCPServerClient):
        super().__init__(
            name=tool_def.name,
            description=tool_def.description
        )
        # Store as class variables to avoid Pydantic issues
        MCPTool.tool_def = tool_def
        MCPTool.server_client = server_client

    async def _arun(self, **kwargs) -> str:
        """Async tool execution with improved error handling."""
        try:
            # Handle query parameter specifically for Genie
            if isinstance(self.server_client, GenieServerClient):
                # Ensure 'query' parameter is included for Genie tools
                if 'query' not in kwargs and len(kwargs) == 1:
                    # If there's one unnamed parameter, treat it as query
                    value = list(kwargs.values())[0]
                    kwargs = {'query': str(value)}
                elif 'query' not in kwargs:
                    # If no query parameter, create one from all parameters
                    query_parts = [f"{k}: {v}" for k, v in kwargs.items()]
                    kwargs = {'query': "; ".join(query_parts)}

            # Call the tool with improved error handling
            result = await self.server_client.call_tool(self.tool_def.name, kwargs)

            # Extract and return the response
            response_content = extract_response_content(result)

            # If we got an error message, check if it's a transient async issue
            if isinstance(response_content, str) and "TaskGroup" in response_content:
                print(f"Detected TaskGroup error for {self.tool_def.name}, this is likely an async execution issue")
                return f"Function '{self.tool_def.name}' encountered an async execution error. The function exists and should work, but there's a technical issue with the async execution environment."

            return response_content

        except Exception as e:
            error_msg = str(e)
            if "TaskGroup" in error_msg or "unhandled errors" in error_msg:
                return f"Function '{self.tool_def.name}' encountered an async execution error (TaskGroup issue). This is a technical problem with the async execution environment, not the function itself."
            return f"Error calling tool {self.tool_def.name}: {e}"

    def _run(self, **kwargs) -> str:
        """Sync tool execution using thread executor."""
        return handle_async_in_sync(self._arun, **kwargs)


class MCPServerManager:
    """
    Manager for multiple MCP server connections.

    This allows an agent to work with multiple MCP servers simultaneously.
    """

    def __init__(self):
        self.servers: Dict[str, MCPServerClient] = {}
        self.tools: List[MCPTool] = []

    def add_server(self, name: str, server_client: MCPServerClient):
        """Add an MCP server to the manager."""
        self.servers[name] = server_client

    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all registered servers."""
        results = {}
        for name, server in self.servers.items():
            try:
                results[name] = await server.connect()
                if results[name]:
                    print(f"✅ Connected to {name} server")
                else:
                    print(f"❌ Failed to connect to {name} server")
            except Exception as e:
                print(f"❌ Error connecting to {name}: {e}")
                results[name] = False
        return results

    async def load_all_tools(self) -> List[MCPTool]:
        """Load tools from all connected servers."""
        all_tools = []

        for name, server in self.servers.items():
            try:
                print(f"Loading tools from {name}...")
                tools = await server.get_tools()
                print(f"Found {len(tools)} tools from {name}")

                for tool_def in tools:
                    mcp_tool = MCPTool(tool_def, server)
                    all_tools.append(mcp_tool)
                    print(f"  - {tool_def.name}: {tool_def.description[:100]}...")

            except Exception as e:
                print(f"Error loading tools from {name}: {e}")

        self.tools = all_tools
        print(f"✅ Total tools loaded: {len(all_tools)}")
        return all_tools

    def get_all_resources(self) -> List[Dict[str, Any]]:
        """Get all deployment resources from all servers."""
        all_resources = []
        for name, server in self.servers.items():
            try:
                resources = server.get_resources()
                all_resources.extend(resources)
                print(f"Added {len(resources)} resources from {name}")
            except Exception as e:
                print(f"Error getting resources from {name}: {e}")
        return all_resources

    def get_server_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered servers."""
        info = {}
        for name, server in self.servers.items():
            info[name] = {
                'type': type(server).__name__,
                'url': server.server_url,
                'connected': server.client is not None
            }
        return info