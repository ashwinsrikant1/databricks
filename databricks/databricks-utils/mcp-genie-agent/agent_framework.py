"""
MCP Genie Agent using proper Databricks Agent Framework.

This creates an agent that can be deployed using databricks.agents.deploy()
"""

import mlflow
import os
from typing import Dict, Any, List
from databricks_mcp import DatabricksMCPClient
from databricks.sdk import WorkspaceClient
from databricks_langchain import ChatDatabricks
from langchain_core.messages import HumanMessage, SystemMessage

# Import configuration
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import config

# Remove any conflicting tokens
if "DATABRICKS_TOKEN" in os.environ:
    del os.environ["DATABRICKS_TOKEN"]


def query_databricks_usage(query: str) -> str:
    """
    Query Databricks system tables via MCP Genie server.

    Args:
        query: Natural language query about Databricks usage

    Returns:
        Results from the system tables
    """
    try:
        # Initialize clients
        workspace_client = WorkspaceClient()
        mcp_client = DatabricksMCPClient(
            server_url=config.genie_server_url,
            workspace_client=workspace_client
        )

        # Get available tools
        tools = mcp_client.list_tools()
        if not tools:
            return "No tools available from MCP server"

        # Use the first tool (should be the Genie query tool)
        tool = tools[0]
        result = mcp_client.call_tool(tool.name, {"query": query})

        # Extract text content
        if hasattr(result, 'content') and result.content:
            if isinstance(result.content, list) and len(result.content) > 0:
                if hasattr(result.content[0], 'text'):
                    return result.content[0].text
                else:
                    return str(result.content[0])
            else:
                return str(result.content)
        else:
            return str(result)

    except Exception as e:
        return f"Error querying system tables: {e}"


def mcp_genie_agent_predict(messages: List[Dict[str, str]]) -> str:
    """
    Main agent function that processes messages and returns responses.

    Args:
        messages: List of message dictionaries with 'role' and 'content'

    Returns:
        Agent response as string
    """
    try:
        # Get the latest user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if not user_message:
            return "I didn't receive a clear question. Please ask me about your Databricks usage."

        # Check if this looks like a query about Databricks usage/data
        query_keywords = ["query", "queries", "sql", "databricks", "usage", "data", "cluster", "compute", "cost", "user", "table", "database", "executed", "run", "job"]

        if any(keyword in user_message.lower() for keyword in query_keywords):
            # Use MCP to query system tables
            tool_result = query_databricks_usage(user_message)

            # Use LLM to interpret the results
            llm = ChatDatabricks(endpoint=config.llm_endpoint_name)

            llm_messages = [
                SystemMessage(content=config.system_prompt),
                HumanMessage(content=f"User asked: {user_message}\n\nData from Databricks system tables: {tool_result}\n\nPlease provide a helpful, concise response based on this data.")
            ]

            response = llm.invoke(llm_messages)
            return response.content
        else:
            # Just use LLM for general questions
            llm = ChatDatabricks(endpoint=config.llm_endpoint_name)

            llm_messages = [SystemMessage(content=config.system_prompt)]
            for msg in messages:
                if msg.get("role") == "user":
                    llm_messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    from langchain_core.messages import AIMessage
                    llm_messages.append(AIMessage(content=msg.get("content", "")))

            response = llm.invoke(llm_messages)
            return response.content

    except Exception as e:
        return f"I apologize, but I encountered an error: {e}"


# Register the function as a tool for MLflow
mlflow.models.set_model(mcp_genie_agent_predict)


if __name__ == "__main__":
    # Test the agent
    test_messages = [
        {"role": "user", "content": "How many SQL queries were executed in the past 7 days?"}
    ]

    response = mcp_genie_agent_predict(test_messages)
    print("Agent response:", response)