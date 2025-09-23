"""
Deployment package for MCP agents.

This package contains deployment configuration and scripts for deploying
MCP agents to Databricks via MLflow.
"""

from .agent_config import deployment_config, DeploymentConfig
from .deploy_agent import main as deploy_main

__all__ = ["deployment_config", "DeploymentConfig", "deploy_main"]