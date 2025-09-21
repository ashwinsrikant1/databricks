"""
Core MCP agent classes for Databricks deployment.

This module provides both development-friendly agents for notebooks
and production-ready agents for Databricks deployment.
"""

import asyncio
from typing import Any, Dict, List, Optional, Generator
from uuid import uuid4

from databricks_langchain import ChatDatabricks
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt.tool_node import ToolNode
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent
)

from .mcp_client import MCPServerManager
from .utils import handle_async_in_sync


class AgentState(dict):
    """State container for LangGraph agent."""

    def __init__(self, messages: List[BaseMessage], custom_inputs: Optional[Dict[str, Any]] = None):
        super().__init__()
        self["messages"] = messages
        self["custom_inputs"] = custom_inputs or {}


class MCPAgent:
    """
    Development-friendly MCP agent with LangGraph workflow.

    This agent is designed for notebook usage and interactive development.
    It supports complex multi-turn conversations and tool orchestration.
    """

    def __init__(
        self,
        llm_endpoint: str,
        system_prompt: str,
        server_manager: MCPServerManager
    ):
        self.llm = ChatDatabricks(endpoint=llm_endpoint)
        self.system_prompt = system_prompt
        self.server_manager = server_manager
        self.agent_graph: Optional[CompiledStateGraph] = None

    async def initialize(self):
        """Initialize the agent by connecting to servers and loading tools."""
        print("🔄 Initializing MCP Agent...")

        # Connect to all servers
        connection_results = await self.server_manager.connect_all()
        if not any(connection_results.values()):
            raise RuntimeError("Failed to connect to any MCP servers")

        # Load all tools
        tools = await self.server_manager.load_all_tools()
        if not tools:
            print("⚠️  No tools loaded - agent will work without external tools")

        # Create LangGraph workflow
        self.agent_graph = await self._create_agent_graph(tools)
        print("✅ MCP Agent initialized successfully!")

    async def _create_agent_graph(self, tools: List[Any]) -> CompiledStateGraph:
        """Create the LangGraph workflow."""

        def should_continue(state: AgentState) -> str:
            """Determine whether to continue the conversation or end it."""
            messages = state["messages"]
            last_message = messages[-1]

            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return END

        def call_model_with_tools(state: AgentState) -> Dict[str, Any]:
            """Call the language model with tools."""
            messages = state["messages"]

            # Add system prompt if not present
            if not messages or not any(
                isinstance(msg, SystemMessage) and msg.content == self.system_prompt
                for msg in messages
            ):
                system_message = SystemMessage(content=self.system_prompt)
                messages = [system_message] + list(messages)

            # Bind tools to LLM if available
            if tools:
                llm_with_tools = self.llm.bind_tools(tools)
                response = llm_with_tools.invoke(messages)
            else:
                response = self.llm.invoke(messages)

            return {"messages": [response]}

        # Define the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", call_model_with_tools)
        if tools:
            tool_node = ToolNode(tools)
            workflow.add_node("tools", tool_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        if tools:
            workflow.add_conditional_edges(
                "agent",
                should_continue,
                {"tools": "tools", END: END}
            )
            workflow.add_edge("tools", "agent")
        else:
            workflow.add_edge("agent", END)

        return workflow.compile()

    async def query(self, message: str) -> str:
        """Process a single query."""
        if not self.agent_graph:
            await self.initialize()

        state = AgentState(messages=[HumanMessage(content=message)])
        result = self.agent_graph.invoke(state)
        return result["messages"][-1].content

    async def chat(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Process a conversation with multiple messages."""
        if not self.agent_graph:
            await self.initialize()

        state = AgentState(messages=messages)
        result = self.agent_graph.invoke(state)
        return result["messages"]


class SingleTurnMCPAgent(ResponsesAgent):
    """
    Production-ready single-turn MCP agent for Databricks deployment.

    This agent is optimized for deployment via MLflow and usage in
    Databricks Playground. It handles single-turn interactions efficiently.
    """

    def __init__(
        self,
        llm_endpoint: str,
        system_prompt: str,
        server_configs: List[Dict[str, Any]]
    ):
        """
        Initialize the single-turn agent.

        Args:
            llm_endpoint: Databricks LLM serving endpoint name
            system_prompt: System prompt for the agent
            server_configs: List of MCP server configurations
                Each config should have: {'type': 'genie'|'custom', 'url': 'server_url', ...}
        """
        self.llm_endpoint = llm_endpoint
        self.system_prompt = system_prompt
        self.server_configs = server_configs
        self._initialized = False
        self._server_manager: Optional[MCPServerManager] = None
        self._tools: List[Any] = []

    def _initialize_sync(self):
        """Initialize the agent in a sync context."""
        if self._initialized:
            return

        try:
            # Use async helper to initialize
            handle_async_in_sync(self._initialize_async)
            self._initialized = True
        except Exception as e:
            print(f"Failed to initialize agent: {e}")
            # Continue without tools if initialization fails
            self._tools = []
            self._initialized = True

    async def _initialize_async(self):
        """Async initialization logic."""
        from .mcp_client import GenieServerClient, UnityCatalogMCPClient, CustomMCPClient
        from databricks.sdk import WorkspaceClient

        print("🔄 Initializing SingleTurnMCPAgent...")

        # Create server manager
        self._server_manager = MCPServerManager()
        workspace_client = WorkspaceClient()

        # Add servers based on configuration
        for config in self.server_configs:
            server_type = config.get('type', 'genie')
            server_name = config.get('name', f"{server_type}_server")

            if server_type == 'genie':
                server_url = config['url']
                server_client = GenieServerClient(server_url, workspace_client)
            elif server_type == 'unity_catalog':
                catalog = config.get('catalog', 'users')
                schema = config.get('schema', 'ashwin_srikant')
                server_client = UnityCatalogMCPClient(catalog, schema, workspace_client)
            elif server_type == 'custom':
                server_url = config['url']
                auth_config = config.get('auth', {})
                server_client = CustomMCPClient(server_url, auth_config)
            else:
                print(f"Unknown server type: {server_type}")
                continue

            self._server_manager.add_server(server_name, server_client)

        # Connect and load tools
        connection_results = await self._server_manager.connect_all()
        if any(connection_results.values()):
            self._tools = await self._server_manager.load_all_tools()
            print(f"✅ Loaded {len(self._tools)} tools")
        else:
            print("⚠️  No MCP servers connected - agent will work without external tools")

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Required predict method for MLflow compatibility."""
        return self.invoke(request)

    def invoke(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Process a single request and return a response."""
        # Ensure agent is initialized
        self._initialize_sync()

        # Extract user message
        if hasattr(request, 'messages') and request.messages:
            if isinstance(request.messages[-1], dict):
                user_content = request.messages[-1].get('content', '')
            else:
                user_content = str(request.messages[-1])
        else:
            user_content = str(request)

        # Process the request
        try:
            response_content = self._process_single_turn(user_content)
        except Exception as e:
            response_content = f"Error processing request: {e}"

        return ResponsesAgentResponse(
            id=str(uuid4()),
            output=[
                self.create_text_output_item(
                    id=str(uuid4()),
                    text=response_content
                )
            ],
            usage={
                "input_tokens": 100,  # Placeholder - in production, get from LLM
                "output_tokens": 50,
                "total_tokens": 150,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens_details": {"reasoning_tokens": 0}
            }
        )

    def _process_single_turn(self, user_message: str) -> str:
        """Process a single turn conversation."""
        llm = ChatDatabricks(endpoint=self.llm_endpoint)

        # Create messages
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message)
        ]

        # If we have tools, use them
        if self._tools:
            # Bind tools and make a single call
            llm_with_tools = llm.bind_tools(self._tools)
            response = llm_with_tools.invoke(messages)

            # If the model wants to use tools, execute them
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Execute tool calls
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name', '')
                    tool_args = tool_call.get('args', {})

                    # Find and execute the tool
                    tool_result = self._execute_tool(tool_name, tool_args)
                    tool_results.append(f"Tool {tool_name}: {tool_result}")

                # Create final response with tool results
                if tool_results:
                    final_prompt = f"""Based on the tool results below, provide a comprehensive answer to the user's question: "{user_message}"

Tool Results:
{chr(10).join(tool_results)}

Please synthesize this information into a clear, helpful response."""

                    final_messages = [
                        SystemMessage(content=self.system_prompt),
                        HumanMessage(content=final_prompt)
                    ]
                    final_response = llm.invoke(final_messages)
                    return final_response.content

            return response.content
        else:
            # No tools available, direct LLM response
            response = llm.invoke(messages)
            return response.content

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool and return the result."""
        try:
            # Find the tool
            tool = None
            for t in self._tools:
                if t.name == tool_name:
                    tool = t
                    break

            if tool:
                return tool._run(**tool_args)
            else:
                return f"Tool '{tool_name}' not found"

        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"

    def stream(self, request: ResponsesAgentRequest) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Stream responses for real-time interaction."""
        # For single-turn agent, just yield the complete response
        response = self.invoke(request)

        yield ResponsesAgentStreamEvent(
            id=response.id,
            created=response.created,
            object="agent.completion.chunk",
            model=response.model,
            choices=[{
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": response.choices[0]["message"]["content"]
                },
                "finish_reason": "stop"
            }]
        )

    def get_deployment_resources(self) -> List[Dict[str, Any]]:
        """Get resources needed for deployment."""
        if not self._initialized:
            self._initialize_sync()

        if self._server_manager:
            return self._server_manager.get_all_resources()
        return []