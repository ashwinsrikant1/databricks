"""
Configuration file for MCP Genie Agent

This file contains all configuration settings for the Databricks MCP Genie Agent.
Keep this file secure and do not commit OAuth credentials to version control.
"""

import os
from pathlib import Path
from typing import Optional

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment variables from {env_file}")
except ImportError:
    # python-dotenv not installed, continue without it
    pass

class MCPGenieConfig:
    """Configuration class for MCP Genie Agent with OAuth authentication."""

    def __init__(self):
        """Initialize configuration from environment variables or defaults."""

        # Databricks Workspace Configuration
        self.workspace_hostname: str = os.getenv(
            "DATABRICKS_HOST",
            "your-workspace.cloud.databricks.com"
        ).replace("https://", "").replace("http://", "")

        # Genie Space Configuration
        self.genie_space_id: str = os.getenv(
            "GENIE_SPACE_ID",
            "your-genie-space-id"
        )

        # OAuth Authentication
        self.databricks_host: str = f"https://{self.workspace_hostname}"
        self.client_id: Optional[str] = os.getenv("DATABRICKS_CLIENT_ID")
        self.client_secret: Optional[str] = os.getenv("DATABRICKS_CLIENT_SECRET")

        # LLM Configuration
        self.llm_endpoint_name: str = os.getenv(
            "LLM_ENDPOINT_NAME",
            "databricks-claude-sonnet-4"
        )

        # MCP Server URLs
        self.genie_server_url: str = f"https://{self.workspace_hostname}/api/2.0/mcp/genie/{self.genie_space_id}"

        # Unity Catalog Configuration
        self.unity_catalog_catalog: str = os.getenv("UNITY_CATALOG_CATALOG", "users")
        self.unity_catalog_schema: str = os.getenv("UNITY_CATALOG_SCHEMA", "ashwin_srikant")
        self.unity_catalog_server_url: str = f"https://{self.workspace_hostname}/api/2.0/mcp/functions/{self.unity_catalog_catalog}/{self.unity_catalog_schema}"

        # Agent Configuration
        self.system_prompt: str = (
            "You are a helpful assistant that can query structured data through "
            "Genie spaces and execute Unity Catalog functions to provide insights based on the results."
        )

    def validate_config(self) -> tuple[bool, list[str]]:
        """
        Validate the configuration and return validation status.

        Returns:
            tuple: (is_valid, list_of_missing_configs)
        """
        missing_configs = []

        # Check required OAuth credentials
        if not self.client_id:
            missing_configs.append("DATABRICKS_CLIENT_ID")

        if not self.client_secret:
            missing_configs.append("DATABRICKS_CLIENT_SECRET")

        # Check workspace configuration
        if self.workspace_hostname in ["your-workspace.cloud.databricks.com", ""]:
            missing_configs.append("DATABRICKS_HOST (workspace hostname)")

        # Check Genie space ID
        if self.genie_space_id in ["your-genie-space-id", ""]:
            missing_configs.append("GENIE_SPACE_ID")

        is_valid = len(missing_configs) == 0
        return is_valid, missing_configs

    def set_oauth_credentials(self, client_id: str, client_secret: str, workspace_host: str):
        """
        Set OAuth credentials programmatically.

        Args:
            client_id: Service principal client ID
            client_secret: OAuth secret
            workspace_host: Databricks workspace hostname (with or without https://)
        """
        os.environ["DATABRICKS_CLIENT_ID"] = client_id
        os.environ["DATABRICKS_CLIENT_SECRET"] = client_secret
        os.environ["DATABRICKS_HOST"] = workspace_host if workspace_host.startswith("https://") else f"https://{workspace_host}"

        # Update instance variables
        self.client_id = client_id
        self.client_secret = client_secret
        self.workspace_hostname = workspace_host.replace("https://", "").replace("http://", "")
        self.databricks_host = f"https://{self.workspace_hostname}"
        self.genie_server_url = f"https://{self.workspace_hostname}/api/2.0/mcp/genie/{self.genie_space_id}"

    def set_genie_space_id(self, genie_space_id: str):
        """
        Set the Genie space ID.

        Args:
            genie_space_id: The ID of the Genie space to connect to
        """
        os.environ["GENIE_SPACE_ID"] = genie_space_id
        self.genie_space_id = genie_space_id
        self.genie_server_url = f"https://{self.workspace_hostname}/api/2.0/mcp/genie/{self.genie_space_id}"

    def print_config(self, mask_secrets: bool = True):
        """
        Print current configuration for debugging.

        Args:
            mask_secrets: Whether to mask sensitive information
        """
        print("🔧 MCP Genie Agent Configuration:")
        print("=" * 50)
        print(f"Workspace Host: {self.databricks_host}")
        print(f"Genie Space ID: {self.genie_space_id}")
        print(f"Unity Catalog: {self.unity_catalog_catalog}.{self.unity_catalog_schema}")
        print(f"LLM Endpoint: {self.llm_endpoint_name}")
        print(f"Genie MCP Server URL: {self.genie_server_url}")
        print(f"Unity Catalog MCP Server URL: {self.unity_catalog_server_url}")

        if mask_secrets:
            client_id_masked = f"{self.client_id[:8]}..." if self.client_id else "Not set"
            client_secret_masked = f"{self.client_secret[:4]}..." if self.client_secret else "Not set"
            print(f"Client ID: {client_id_masked}")
            print(f"Client Secret: {client_secret_masked}")
        else:
            print(f"Client ID: {self.client_id}")
            print(f"Client Secret: {self.client_secret}")


# Global configuration instance
config = MCPGenieConfig()


# Convenience functions for backward compatibility
def get_config() -> MCPGenieConfig:
    """Get the global configuration instance."""
    return config


def validate_oauth_setup() -> bool:
    """
    Validate OAuth setup and print helpful messages.

    Returns:
        bool: True if setup is valid, False otherwise
    """
    is_valid, missing_configs = config.validate_config()

    if is_valid:
        print("✅ OAuth configuration is valid!")
        config.print_config(mask_secrets=True)
        return True
    else:
        print("❌ OAuth configuration is incomplete!")
        print(f"Missing configurations: {', '.join(missing_configs)}")
        print("\n📝 Please set these environment variables or use the config methods:")
        for missing in missing_configs:
            print(f"   export {missing}='your-value-here'")
        return False