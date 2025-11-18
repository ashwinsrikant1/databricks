# Contributing Guide

Thank you for your interest in contributing to the Databricks Utilities repository!

## Getting Started

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ashwinsrikant1/databricks.git
   cd databricks
   ```

2. **Initialize submodules** (if you need the MCP SDK)
   ```bash
   git submodule update --init --recursive
   ```

3. **Run setup**
   ```bash
   ./setup.sh
   ```

4. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

### Development Workflow

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the repository structure guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   pytest
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Repository Structure Guidelines

### Where to Add New Code

- **Utilities**: Add to `databricks/databricks-utils/`
- **Applications**: Add to `databricks/databricks-app/`
- **Examples**: Add to `examples/etl/` or `examples/notebooks/`
- **Documentation**: Add to `docs/`

> **Note**: Customer-specific code should be maintained in a separate private repository, not in this public utilities repository.

### File Organization

```
databricks/
├── databricks/           # Core utilities and tools
├── examples/             # Self-contained examples
├── docs/                 # Documentation
└── mcp/                  # MCP SDK (submodule)
```

## Code Standards

### Python Code

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Include type hints where appropriate

Example:
```python
def process_data(input_path: str, output_path: str) -> None:
    """
    Process data from input path and save to output path.

    Args:
        input_path: Path to input data
        output_path: Path to save processed data
    """
    # Implementation
    pass
```

### Documentation

- Update README files when adding new features
- Add examples for new utilities
- Document any prerequisites or dependencies
- Include configuration examples

### Testing

- Add unit tests for new functions
- Add integration tests for new features
- Ensure all tests pass before submitting PR

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=databricks
```

## Dependencies

### Adding New Dependencies

1. **Core dependencies**: Add to root `requirements.txt`
   ```bash
   echo "new-package>=1.0.0" >> requirements.txt
   ```

2. **Component-specific**: Add to component's requirements.txt or pyproject.toml

3. **Document the dependency**: Explain why it's needed in the README

### Dependency Guidelines

- Use version pinning for stability: `package>=1.0.0,<2.0.0`
- Minimize dependencies where possible
- Document any optional dependencies

## Git Guidelines

### Commit Messages

Use clear, descriptive commit messages:

```
Add SCD Type 2 pipeline example

- Implements CDC pattern with Delta Live Tables
- Includes automatic schema inference
- Adds comprehensive documentation
```

### Branch Naming

- Features: `feature/description`
- Bug fixes: `fix/description`
- Documentation: `docs/description`
- Examples: `example/description`

### Working with Submodules

When updating the MCP submodule:

```bash
# Update submodule
cd mcp
git pull origin main
cd ..

# Commit the submodule update
git add mcp
git commit -m "Update mcp submodule"
```

## Best Practices

### Self-Service Design

This repository is designed for self-service use:

- **Minimal setup**: Users should be able to run `./setup.sh` and start working
- **Clear documentation**: Every component should have a README
- **Working examples**: Provide ready-to-run examples
- **Independent scripts**: Scripts should be runnable without complex dependencies

### Security

- **Never commit credentials**: Use .env files (git-ignored)
- **No hardcoded secrets**: Use environment variables
- **Review .env.example**: Ensure example files don't contain real credentials

### Testing Before Committing

Always test your changes:

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Test your specific changes
python your_new_script.py

# Check for common issues
python -m flake8 .
```

## Getting Help

- Check existing documentation in `docs/`
- Review similar examples in `examples/`
- Open an issue for questions or problems
- Reach out to maintainers

## Release Process

1. Update version numbers
2. Update CHANGELOG
3. Run full test suite
4. Create release tag
5. Update documentation

## Questions?

Open an issue or reach out to the repository maintainers.

Thank you for contributing!
