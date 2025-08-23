# FMAPI Pricing Calculator - Databricks App

An interactive web application for estimating Foundation Model API costs, deployed as a Databricks App.

## Features

- **Interactive Cost Calculator**: Real-time cost estimation based on usage patterns
- **Multiple Model Support**: Claude Sonnet 4, Claude 3.7 Sonnet, Claude Opus 4
- **Multi-Cloud Pricing**: AWS, GCP, and Azure (with markup)
- **Caching Analysis**: Factor in cache hit ratios for cost optimization
- **Visual Analytics**: Charts and graphs showing cost breakdowns
- **Volume Discounts**: Apply negotiated discount percentages

## Quick Start

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

### Deploy to Databricks

1. **Prerequisites**:
   - Databricks CLI installed and configured
   - Access to E2 Demo Field Eng workspace
   - Premium or Enterprise workspace (Apps not supported in Standard)

2. **Deploy the app**:
   ```bash
   databricks bundle deploy --target dev
   ```

3. **Access the app**:
   - Go to your Databricks workspace
   - Navigate to **Apps** in the sidebar
   - Find and open "fmapi-pricing-calculator"

## Usage

### Input Parameters

- **Model**: Select model (Claude Sonnet 4, 3.7 Sonnet, Opus 4)
- **Cloud Provider**: Choose AWS, GCP, or Azure
- **TPM (Millions)**: Tokens processed per minute in millions
- **Input/Output Tokens per Request**: Average token usage per API call
- **Cache Hit Ratio**: Percentage of requests benefiting from caching
- **Volume Discount**: Negotiated discount percentage

### Output Metrics

- **Daily/Monthly Costs**: Total projected expenses
- **Request Volume**: API calls processed per day/month
- **Cost Breakdown**: Distribution across input, output, and cache reads
- **Token Analysis**: Visual breakdown of token consumption

## Original Notebook

This app is based on the `Claude Usage Calculator.ipynb` notebook, converted to a more general Foundation Model API pricing calculator with an interactive web interface and enhanced visualizations.

## Architecture

- **Frontend**: Streamlit web application
- **Backend**: Python cost calculation engine
- **Deployment**: Databricks Apps serverless platform
- **Visualizations**: Plotly charts and metrics

## Support

For issues or questions about this Databricks App, please contact the E2 Demo Field Engineering team.