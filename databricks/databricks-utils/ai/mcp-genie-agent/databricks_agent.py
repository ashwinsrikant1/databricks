"""
MCP Genie Agent using official Databricks Agent Framework pattern.

This follows the @agent decorator approach from Databricks documentation.
"""

import os
from typing import Dict, Any
from databricks.agents import agent
from databricks_mcp import DatabricksMCPClient
from databricks.sdk import WorkspaceClient
from databricks_langchain import ChatDatabricks

# Import configuration
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import config

# Remove any conflicting tokens
if "DATABRICKS_TOKEN" in os.environ:
    del os.environ["DATABRICKS_TOKEN"]


# Initialize MCP client
workspace_client = WorkspaceClient()
mcp_client = DatabricksMCPClient(
    server_url=config.genie_server_url,
    workspace_client=workspace_client
)

# Initialize LLM
llm = ChatDatabricks(endpoint=config.llm_endpoint_name)


@agent
def mcp_genie_agent(messages: list) -> str:
    """
    MCP Genie Agent for querying Databricks system tables.

    This agent can answer questions about your Databricks usage by querying
    system tables through the Genie space.
    """

    # Get the latest user message
    user_message = messages[-1]["content"] if messages else ""

    try:
        # Get available tools from MCP server
        tools = mcp_client.list_tools()

        if tools and any(keyword in user_message.lower() for keyword in ["query", "queries", "sql", "databricks", "usage", "data"]):
            # Use the first available tool (should be the Genie query tool)
            tool = tools[0]
            print(f"🔧 Using MCP tool: {tool.name}")

            # Call the MCP tool with the user's query
            result = mcp_client.call_tool(tool.name, {"query": user_message})

            # Extract text content from result
            tool_result = ""
            if hasattr(result, 'content') and result.content:
                if isinstance(result.content, list) and len(result.content) > 0:
                    if hasattr(result.content[0], 'text'):
                        tool_result = result.content[0].text
                    else:
                        tool_result = str(result.content[0])
                else:
                    tool_result = str(result.content)
            else:
                tool_result = str(result)

            # Use LLM to interpret and respond to the tool result
            system_prompt = config.system_prompt
            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User asked: {user_message}\n\nData from system tables: {tool_result}\n\nPlease provide a helpful, concise response based on this data."}
            ]

            response = llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User asked: {user_message}\n\nData from system tables: {tool_result}\n\nPlease provide a helpful, concise response based on this data."}
            ])

            return response.content

        else:
            # No tools needed or available, just use LLM directly
            system_prompt = config.system_prompt
            all_messages = [{"role": "system", "content": system_prompt}] + messages

            response = llm.invoke(all_messages)
            return response.content

    except Exception as e:
        return f"I apologize, but I encountered an error while processing your request: {e}"


if __name__ == "__main__":
    # Test the agent
    test_messages = [
        {"role": "user", "content": "How many queries were executed in the past 7 days?"}
    ]

    response = mcp_genie_agent(test_messages)
    print("Agent response:", response)