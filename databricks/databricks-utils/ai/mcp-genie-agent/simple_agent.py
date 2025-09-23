"""
Simple MCP Genie Agent using Databricks Agent Framework.

This follows the official Databricks documentation pattern for MCP agents.
"""

import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse
from databricks_mcp import DatabricksMCPClient
from databricks.sdk import WorkspaceClient
from databricks_langchain import ChatDatabricks
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Any, Dict, List
import os
from uuid import uuid4

# Import configuration
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import config


class ToolInfo:
    """Tool information container."""
    def __init__(self, name: str, description: str, exec_fn):
        self.name = name
        self.description = description
        self.exec_fn = exec_fn


class SimpleMCPAgent(ResponsesAgent):
    """Simple MCP Agent using Databricks Agent Framework."""

    def __init__(self):
        # Remove any conflicting tokens
        if "DATABRICKS_TOKEN" in os.environ:
            del os.environ["DATABRICKS_TOKEN"]

        self.llm_endpoint = config.llm_endpoint_name
        self.system_prompt = config.system_prompt
        self.workspace_client = WorkspaceClient()
        self.tools = self._fetch_mcp_tools()
        self.llm = ChatDatabricks(endpoint=self.llm_endpoint)

    def _fetch_mcp_tools(self) -> List[ToolInfo]:
        """Fetch and prepare MCP tools."""
        try:
            print("🔄 Fetching MCP tools...")

            # Create MCP client
            mcp_client = DatabricksMCPClient(
                server_url=config.genie_server_url,
                workspace_client=self.workspace_client
            )

            # Get available tools
            tools = mcp_client.list_tools()
            print(f"✅ Found {len(tools)} MCP tools")

            # Convert to ToolInfo objects
            tool_infos = []
            for tool in tools:
                tool_info = ToolInfo(
                    name=tool.name,
                    description=tool.description,
                    exec_fn=self._create_exec_function(mcp_client, tool.name)
                )
                tool_infos.append(tool_info)
                print(f"  - {tool.name}: {tool.description[:100]}...")

            return tool_infos

        except Exception as e:
            print(f"❌ Error fetching MCP tools: {e}")
            return []

    def _create_exec_function(self, mcp_client, tool_name: str):
        """Create execution function for a tool."""
        def exec_tool(**kwargs) -> str:
            try:
                # Convert kwargs to the format expected by MCP
                result = mcp_client.call_tool(tool_name, kwargs)

                # Extract text content from result
                if hasattr(result, 'content') and result.content:
                    if isinstance(result.content, list) and len(result.content) > 0:
                        if hasattr(result.content[0], 'text'):
                            return result.content[0].text

                return str(result)
            except Exception as e:
                return f"Error calling tool {tool_name}: {e}"

        return exec_tool

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Process a request and return a response."""
        try:
            # Extract user message
            if hasattr(request, 'input') and isinstance(request.input, list):
                user_content = request.input[-1].content if request.input else ""
            elif hasattr(request, 'input'):
                user_content = str(request.input)
            else:
                user_content = str(request)

            print(f"🔍 Processing query: {user_content}")

            # Simple approach: try to determine if we should use tools
            response_content = self._process_with_llm(user_content)

            return ResponsesAgentResponse(
                id=str(uuid4()),
                output=[
                    self.create_text_output_item(
                        id=str(uuid4()),
                        text=response_content
                    )
                ],
                usage={
                    "input_tokens": 100,  # Placeholder
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0}
                }
            )

        except Exception as e:
            print(f"❌ Error in predict: {e}")
            return ResponsesAgentResponse(
                id=str(uuid4()),
                output=[
                    self.create_text_output_item(
                        id=str(uuid4()),
                        text=f"I apologize, but I encountered an error: {e}"
                    )
                ],
                usage={
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0}
                }
            )

    def _process_with_llm(self, user_message: str) -> str:
        """Process message with LLM and potentially call tools."""
        try:
            # For simplicity, let's directly call the Genie tool if we have one
            if self.tools and "query" in user_message.lower():
                tool = self.tools[0]  # Use first available tool
                print(f"🔧 Using tool: {tool.name}")

                # Call the tool with the user's query
                tool_result = tool.exec_fn(query=user_message)

                # Use LLM to interpret and respond to the tool result
                messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=f"User asked: {user_message}\n\nTool result: {tool_result}\n\nPlease provide a helpful response based on this data.")
                ]

                response = self.llm.invoke(messages)
                return response.content
            else:
                # Just use LLM without tools
                messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=user_message)
                ]

                response = self.llm.invoke(messages)
                return response.content

        except Exception as e:
            return f"I encountered an error while processing your request: {e}"


# For MLflow compatibility
def _load_pyfunc(data_path, model_config):
    """Load function for MLflow."""
    return SimpleMCPAgent()


if __name__ == "__main__":
    # Test the agent locally
    agent = SimpleMCPAgent()

    test_request = ResponsesAgentRequest(
        input="How many queries were executed in the past 7 days?"
    )

    response = agent.predict(test_request)
    print("Response:", response)