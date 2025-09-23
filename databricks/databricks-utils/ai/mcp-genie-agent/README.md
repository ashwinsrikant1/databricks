# MCP Genie Agent with Databricks Claude Sonnet 4

A powerful tool-calling agent that uses Databricks' **Claude Sonnet 4** endpoint with the MCP (Model Context Protocol) Genie server to query structured data tables through natural language.

## 🚀 Features

- **OAuth Authentication** - Secure service principal authentication
- **Claude Sonnet 4 Integration** - Powered by Databricks' most advanced LLM endpoint
- **MCP Integration** - Connect to Databricks Genie spaces
- **LangGraph Workflow** - Sophisticated agent orchestration
- **MLflow Compatible** - Ready for production deployment
- **Interactive Testing** - Multiple ways to test and interact with the agent

## 📁 Project Structure

```
mcp-genie-agent/
├── README.md                    # This file
├── mcp_genie_agent.ipynb       # Main Jupyter notebook
├── config.py                   # Configuration management
├── .env                       # Environment variables (edit with your values)
├── .env.example               # Environment variables template
├── requirements.txt           # Python dependencies
└── .gitignore                 # Git ignore rules
```

## 🔧 Setup

### 1. Prerequisites

- Databricks workspace with access to **Claude Sonnet 4** endpoint (`databricks-claude-sonnet-4`)
- MCP Genie server access (Beta)
- Python 3.12 or above
- Service Principal with OAuth credentials

### 2. Create Service Principal

1. **In your Databricks workspace**:
   - Go to **Settings** → **Identity and access** → **Service principals**
   - Click **Add service principal**
   - Enter name: `MCP-Genie-Agent`
   - Click **Add**

2. **Generate OAuth credentials**:
   - Select your service principal
   - Go to **OAuth secrets** tab
   - Click **Generate secret**
   - Set lifetime (max 730 days, recommended: 365 days)
   - **⚠️ Copy the Client ID and Client Secret** (shown only once!)

3. **Assign workspace permissions**:
   - Add the service principal to your workspace
   - Grant necessary permissions for Genie space access

### 3. Configure Authentication

Choose one of these methods:

#### Method 1: Environment Variables (Recommended)
```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_CLIENT_ID="your-service-principal-client-id"
export DATABRICKS_CLIENT_SECRET="your-oauth-secret"
export GENIE_SPACE_ID="your-genie-space-id"
```

#### Method 2: .env File (Included)
```bash
# Edit the included .env file with your actual values
# The file is already present with placeholder values
vim .env  # or use your preferred editor
```

#### Method 3: .databrickscfg File
```ini
[default]
host = https://your-workspace.cloud.databricks.com
client_id = your-service-principal-client-id
client_secret = your-oauth-secret
```

### 4. Install Dependencies

```bash
pip install -U "mcp>=1.9" "databricks-sdk[openai]" "mlflow>=3.1.0" "databricks-agents>=1.0.0" "databricks-mcp"
pip install databricks-langchain langgraph pydantic
```

## 🎯 Usage

### Quick Start
1. Open `mcp_genie_agent.ipynb` in Jupyter or Databricks
2. Run all cells to import and configure
3. Test OAuth setup with the validation cell
4. Run the agent test: `agent = await test_agent()`

### Interactive Session
```python
# Start an interactive chat session
await interactive_session()
```

### Single Query Testing
```python
# Test a specific query
query = "What tables are available in this Genie space?"
response = await single_query_test(query)
```

## 📝 Example Queries

### Data Discovery
- "What tables are available in this Genie space?"
- "Show me the schema for [table_name]"
- "What columns does [table_name] have?"

### Data Analysis
- "What are the top 10 records in [table_name]?"
- "Can you analyze trends in [column_name] over time?"
- "Show me summary statistics for [table_name]"

### Business Insights
- "What insights can you provide about [business_metric]?"
- "How has [kpi] changed over the last quarter?"
- "What patterns do you see in [dataset]?"

## ⚙️ Configuration

The `config.py` file provides a centralized configuration system:

```python
from config import config

# Programmatic setup
config.set_oauth_credentials(
    client_id="your-client-id",
    client_secret="your-secret",
    workspace_host="your-workspace.com"
)
config.set_genie_space_id("your-genie-space-id")

# Validate configuration
is_valid, missing = config.validate_config()
```

## 🔒 Security Best Practices

- **Never commit credentials** to version control
- **Use service principals** instead of personal access tokens
- **Set OAuth secret expiration** appropriately (max 730 days)
- **Regularly rotate credentials** for production use
- **Use environment variables** or secure config files

## 🛠️ Troubleshooting

| Error | Solution |
|-------|----------|
| `Authentication failed` | Check Client ID and Secret |
| `Workspace not found` | Verify WORKSPACE_HOSTNAME |
| `Access denied to Genie` | Assign service principal to Genie space |
| `OAuth secret expired` | Generate new OAuth secret |
| `Network timeout` | Check network connectivity to workspace |

## 🚀 Production Deployment

The agent is MLflow-compatible and ready for production:

```python
# Create agent for MLflow deployment
agent_graph = await create_agent()
mlflow_agent = MCPGenieAgent(agent_graph)

# Log and deploy with MLflow
mlflow.pyfunc.log_model("mcp_genie_agent", python_model=mlflow_agent)
```

## 📚 References

- [Databricks MCP Documentation](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [Databricks OAuth Setup](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-u2m)

## 🤝 Contributing

This project is part of the Databricks utilities collection. Feel free to extend and modify for your specific use cases.

## ⚠️ Notes

- MCP Genie server is currently in Beta
- History is not passed to Genie APIs (each query is independent)
- Consider using multiple agents for complex workflows
- Monitor OAuth token usage and refresh patterns