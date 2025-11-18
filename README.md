# Databricks Utilities & Testing

A collection of utilities, tools, and examples for working with Databricks. This repository is designed for easy self-service testing and experimentation.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/ashwinsrikant1/databricks.git
cd databricks

# Run the setup script
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Repository Structure

```
databricks_testing/
├── databricks/              # Core Databricks utilities and tools
│   ├── databricks-app/      # Databricks applications
│   ├── databricks-utils/    # General utilities and helpers
│   └── databricks-go/       # Go-based tools
├── cx_projects/             # Customer-specific implementations (submodule)
├── mcp/                     # Databricks MCP SDK (submodule)
├── examples/                # Example scripts and notebooks
│   ├── etl/                 # ETL pipeline examples
│   └── notebooks/           # Jupyter notebook examples
├── docs/                    # Documentation and planning
├── requirements.txt         # Core Python dependencies
└── setup.sh                 # Quick setup script
```

## Configuration

### Databricks Authentication

Set these environment variables or create a `.env` file:

```bash
export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=your-personal-access-token
```

Or create a `.env` file:

```env
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token
```

## Components

### Core Utilities (`databricks/`)

General-purpose Databricks utilities:
- Cluster management scripts
- Data processing utilities
- Go-based SQL drivers and tools

See `databricks/README.md` for details.

### Databricks MCP Server (`databricks/databricks-utils/ai/databricks-mcp-server/`)

MCP (Model Context Protocol) server for Databricks integration.

To use:
```bash
cd databricks/databricks-utils/ai/databricks-mcp-server
pip install -e .
./start_mcp_server.sh
```

See the server's README for full documentation.

### Examples (`examples/`)

Ready-to-use example code:
- **ETL Examples**: SCD Type 2 pipelines, CDC processing
- **Notebooks**: Data generation, analysis examples

### Customer Projects (`cx_projects/`)

Customer-specific implementations (private submodule).

To initialize:
```bash
git submodule update --init --recursive
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run tests
pytest
```

### Adding New Dependencies

Update `requirements.txt` and run:
```bash
pip install -r requirements.txt
```

## Submodules

This repository uses git submodules:
- `cx_projects`: Customer-specific code (private)
- `mcp`: Databricks MCP SDK

To update submodules:
```bash
git submodule update --remote
```

## Contributing

1. Create a new branch for your changes
2. Make your changes
3. Test your changes
4. Submit a pull request

## Documentation

- Setup guides: `docs/`
- API documentation: See individual component READMEs
- Examples: `examples/`

## License

See individual component licenses.
