# Examples

This directory contains ready-to-use example code for common Databricks patterns and use cases.

## Directory Structure

- `etl/` - ETL pipeline examples
- `notebooks/` - Jupyter notebook examples

## ETL Examples

### SCD Type 2 CDC Pipeline (`etl/scd2_cdc_pipeline.py`)

Demonstrates how to implement a Slowly Changing Dimension (SCD) Type 2 pattern with Change Data Capture (CDC) using Databricks Delta Live Tables.

**Use case**: Track historical changes in dimension tables

**Features**:
- Automatic schema inference from S3
- JSON parsing and transformation
- SCD Type 2 implementation with DLT

**To use**:
```python
# Update the S3 path in the script
S3_BUCKET_PATH = "s3://your-bucket/path/to/cdc/data/"

# Run as a Delta Live Tables pipeline
```

## Notebook Examples

### Synthetic Data Generator (`notebooks/synthetic_data_generator.ipynb`)

Generates synthetic test data for experimentation.

**Use case**: Create realistic test datasets for development and testing

**To use**:
```bash
jupyter notebook notebooks/synthetic_data_generator.ipynb
```

Or upload to Databricks workspace and run there.

## Running Examples

### Prerequisites

```bash
# Install dependencies
pip install -r ../requirements.txt

# Configure Databricks authentication
export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=your-token
```

### Running Python Scripts

```bash
# Example: Run an ETL script
python etl/scd2_cdc_pipeline.py
```

### Running Notebooks

Option 1: Local Jupyter
```bash
jupyter notebook notebooks/
```

Option 2: Databricks Workspace
- Upload the notebook to your Databricks workspace
- Attach to a cluster
- Run the cells

## Adding New Examples

When adding new examples:
1. Place in appropriate subdirectory (etl/, notebooks/, etc.)
2. Include clear comments explaining the use case
3. Document any prerequisites or configuration needed
4. Update this README with a description

## Need Help?

- Check the main repository README for setup instructions
- Review Databricks documentation: https://docs.databricks.com
- Open an issue in the repository
