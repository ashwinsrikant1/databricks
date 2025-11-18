#!/bin/bash
# Quick setup script for databricks_testing repository

set -e

echo "=== Databricks Testing Repository Setup ==="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "Python version: $(python3 --version)"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install core dependencies
echo "Installing core dependencies..."
pip install -r requirements.txt

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "For project-specific dependencies, see:"
echo "  - databricks-mcp-server/: MCP server implementation"
echo "  - cx_projects/: Customer-specific projects"
echo "  - examples/: Example scripts and notebooks"
echo ""
echo "To configure Databricks authentication, set these environment variables:"
echo "  export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com"
echo "  export DATABRICKS_TOKEN=your-token"
echo ""
echo "Or create a .env file with these values."
echo ""
