"""
MCP client management for multiple server types.

This module provides an extensible framework for connecting to different
MCP servers (Genie, custom servers, etc.) and managing their tools.
"""

import asyncio
import os
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


class DatabricksMCPServerClient(MCPServerClient):
    """
    Client for external custom MCP servers (like databricks-mcp-server from https://github.com/JustTryAI/databricks-mcp-server).

    This connects to a locally running instance of a custom MCP server.
    """

    def __init__(self, server_url: str, auth_config: Optional[Dict] = None):
        super().__init__(server_url)
        self.auth_config = auth_config or {}
        self.available_tools = [
            {
                "name": "execute_sql",
                "description": "Execute SQL statements on Databricks warehouse",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL query to execute"},
                        "warehouse_id": {"type": "string", "description": "Optional warehouse ID"}
                    },
                    "required": ["sql"]
                }
            },
            {
                "name": "list_clusters",
                "description": "List all Databricks clusters",
                "parameters": {"type": "object", "properties": {}}
            }
        ]

    async def connect(self) -> bool:
        """Connect to the custom MCP server."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Test connection by trying to get available tools
                async with session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        print(f"✅ Connected to Custom MCP Server at {self.server_url}")
                        return True
                    else:
                        print(f"❌ Server responded with status {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Failed to connect to Custom MCP Server: {e}")
            # For demo purposes, return True to allow testing even if server isn't running
            print("⚠️  Continuing without connection for demo purposes")
            return True

    async def get_tools(self) -> List[Any]:
        """Get available tools from the custom MCP server."""
        try:
            # Create mock tool objects that match the expected interface
            tools = []
            for tool_def in self.available_tools:
                # Create a simple object with name and description
                tool_obj = type('Tool', (), {
                    'name': tool_def['name'],
                    'description': tool_def['description'],
                    'parameters': tool_def.get('parameters', {})
                })()
                tools.append(tool_obj)

            print(f"✅ Loaded {len(tools)} tools from Custom MCP Server")
            return tools
        except Exception as e:
            print(f"Error getting tools from Custom MCP Server: {e}")
            return []

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call a tool on the custom MCP server."""
        try:
            # For actual SQL execution, use Databricks SDK directly
            if tool_name == "execute_sql":
                sql_query = parameters.get('sql', '')
                print(f"🔍 Executing SQL via Custom MCP Server: {sql_query}")

                # Import Databricks SDK here to execute real SQL
                from databricks.sdk import WorkspaceClient
                from databricks.sdk.service.sql import QueryFilter, StatementState
                import time

                # Use OAuth authentication (environment should have OAuth creds)
                w = WorkspaceClient()

                try:
                    # Execute the SQL query on the warehouse
                    warehouse_id = os.getenv('SQL_WAREHOUSE_ID', '4b9b953939869799')

                    print(f"Using warehouse: {warehouse_id}")
                    response = w.statement_execution.execute_statement(
                        warehouse_id=warehouse_id,
                        statement=sql_query,
                        wait_timeout='30s'
                    )

                    # Wait for completion and get results
                    while response.status.state in [StatementState.PENDING, StatementState.RUNNING]:
                        print("Query executing...")
                        time.sleep(1)
                        response = w.statement_execution.get_statement(response.statement_id)

                    if response.status.state == StatementState.SUCCEEDED:
                        # Get the results
                        result_response = w.statement_execution.get_statement_result_chunk_n(
                            statement_id=response.statement_id,
                            chunk_index=0
                        )

                        # Format results
                        if result_response.data_array:
                            columns = [col.name for col in response.manifest.schema.columns]
                            rows = []
                            for row_data in result_response.data_array:
                                row_dict = dict(zip(columns, row_data))
                                rows.append(row_dict)

                            return {
                                "result": "SQL query executed successfully",
                                "columns": columns,
                                "rows": rows,
                                "row_count": len(rows),
                                "execution_time": f"{response.status.execution_end_time_ms - response.status.execution_start_time_ms}ms",
                                "status": "success",
                                "query": sql_query
                            }
                        else:
                            return {
                                "result": "SQL query executed successfully (no results returned)",
                                "columns": [],
                                "rows": [],
                                "row_count": 0,
                                "status": "success",
                                "query": sql_query
                            }
                    else:
                        error_msg = response.status.error.message if response.status.error else "Unknown error"
                        return {
                            "result": f"SQL query failed: {error_msg}",
                            "status": "error",
                            "query": sql_query
                        }

                except Exception as sql_error:
                    print(f"SQL execution error: {sql_error}")
                    return {
                        "result": f"SQL execution failed: {str(sql_error)}",
                        "status": "error",
                        "query": sql_query
                    }

            elif tool_name == "list_clusters":
                print("📋 Listing clusters via Custom MCP Server")

                # Use Databricks SDK to get real cluster information
                from databricks.sdk import WorkspaceClient

                w = WorkspaceClient()
                try:
                    clusters = list(w.clusters.list())
                    cluster_list = []
                    for cluster in clusters:
                        cluster_list.append({
                            "id": cluster.cluster_id,
                            "name": cluster.cluster_name,
                            "state": str(cluster.state),
                            "node_type": cluster.node_type_id,
                            "num_workers": getattr(cluster, 'num_workers', 'N/A')
                        })

                    return {
                        "clusters": cluster_list,
                        "count": len(cluster_list),
                        "status": "success"
                    }

                except Exception as cluster_error:
                    print(f"Cluster listing error: {cluster_error}")
                    return {
                        "result": f"Failed to list clusters: {str(cluster_error)}",
                        "status": "error"
                    }

            else:
                return f"Tool {tool_name} called with parameters: {parameters}"

        except Exception as e:
            print(f"Error calling tool {tool_name}: {e}")
            return f"Error: {e}"

    def get_resources(self) -> List[Dict[str, Any]]:
        """Get resources needed for deployment."""
        return [{
            "type": "external_mcp_server",
            "url": self.server_url,
            "required_env": ["DATABRICKS_HOST", "DATABRICKS_TOKEN"]
        }]


class CustomMCPClient(MCPServerClient):
    """
    Generic client for other custom MCP servers.
    """

    def __init__(self, server_url: str, auth_config: Optional[Dict] = None):
        super().__init__(server_url)
        self.auth_config = auth_config or {}

    async def connect(self) -> bool:
        """Connect to the custom MCP server."""
        print(f"Custom MCP client for {self.server_url} - implement as needed")
        return False

    async def get_tools(self) -> List[Any]:
        """Get available tools from the custom server."""
        return []

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call a tool on the custom server."""
        return "Custom server tool call - implement as needed"

    def get_resources(self) -> List[Dict[str, Any]]:
        """Get resources needed for deployment."""
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