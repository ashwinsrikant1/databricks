"""
MCP Genie Agent with proper Agent Framework signatures.

This uses the correct ChatCompletionRequest/Response format.
"""

import mlflow
import os
from typing import Dict, Any, List
from databricks_mcp import DatabricksMCPClient
from databricks.sdk import WorkspaceClient
from databricks_langchain import ChatDatabricks
from langchain_core.messages import HumanMessage, SystemMessage
from mlflow.types.llm import ChatCompletionRequest, ChatCompletionResponse, ChatMessage, ChatChoice

# Import configuration
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import config

# Remove any conflicting tokens
if "DATABRICKS_TOKEN" in os.environ:
    del os.environ["DATABRICKS_TOKEN"]


def query_databricks_usage(query: str) -> str:
    """Query Databricks system tables via MCP Genie server."""
    try:
        workspace_client = WorkspaceClient()
        mcp_client = DatabricksMCPClient(
            server_url=config.genie_server_url,
            workspace_client=workspace_client
        )

        tools = mcp_client.list_tools()
        if not tools:
            return "No tools available from MCP server"

        tool = tools[0]
        result = mcp_client.call_tool(tool.name, {"query": query})

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


def predict(requests: list[ChatCompletionRequest]) -> list[ChatCompletionResponse]:
    """
    Agent function with proper ChatCompletionRequest/Response signatures.

    Args:
        requests: List of ChatCompletionRequest with messages

    Returns:
        List of ChatCompletionResponse with agent's responses
    """
    responses = []

    for request in requests:
        try:
            # Debug: Print what we're actually receiving
            print(f"DEBUG: Received request type: {type(request)}")
            print(f"DEBUG: Request content: {request}")

            # Handle different input formats
            if isinstance(request, str):
                # If we get a string, treat it as the user message
                messages = [ChatMessage(role="user", content=request)]
            elif hasattr(request, 'messages'):
                # Extract messages from request
                messages = request.messages
            else:
                # Try to convert to messages
                messages = [ChatMessage(role="user", content=str(request))]

            # Get the latest user message
            user_message = ""
            for msg in reversed(messages):
                if msg.role == "user":
                    user_message = msg.content
                    break

            if not user_message:
                response_content = "I didn't receive a clear question. Please ask me about your Databricks usage."
            else:
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
                    response_content = response.content
                else:
                    # Just use LLM for general questions
                    llm = ChatDatabricks(endpoint=config.llm_endpoint_name)

                    llm_messages = [SystemMessage(content=config.system_prompt)]
                    for msg in messages:
                        if msg.role == "user":
                            llm_messages.append(HumanMessage(content=msg.content))
                        elif msg.role == "assistant":
                            from langchain_core.messages import AIMessage
                            llm_messages.append(AIMessage(content=msg.content))

                    response = llm.invoke(llm_messages)
                    response_content = response.content

            # Create proper ChatCompletionResponse
            response = ChatCompletionResponse(
                id="mcp-genie-agent",
                object="chat.completion",
                created=0,  # Will be set by MLflow
                model=config.llm_endpoint_name,
                choices=[
                    ChatChoice(
                        index=0,
                        message=ChatMessage(
                            role="assistant",
                            content=response_content
                        ),
                        finish_reason="stop"
                    )
                ],
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            )
            responses.append(response)

        except Exception as e:
            # Return error response in proper format
            error_response = ChatCompletionResponse(
                id="mcp-genie-agent-error",
                object="chat.completion",
                created=0,
                model=config.llm_endpoint_name,
                choices=[
                    ChatChoice(
                        index=0,
                        message=ChatMessage(
                            role="assistant",
                            content=f"I apologize, but I encountered an error: {e}"
                        ),
                        finish_reason="stop"
                    )
                ],
                usage={
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            )
            responses.append(error_response)

    return responses


# Set model for MLflow
mlflow.models.set_model(predict)


if __name__ == "__main__":
    # Test the agent
    test_requests = [ChatCompletionRequest(
        messages=[
            ChatMessage(role="user", content="How many SQL queries were executed in the past 7 days?")
        ]
    )]

    responses = predict(test_requests)
    print("Agent response:", responses[0].choices[0].message.content)