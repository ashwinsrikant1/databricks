# Databricks notebook source
# MAGIC %md
# MAGIC # Claude Usage Calculator
# MAGIC ### Interactive Cost Estimation for Claude Models on Bedrock

# COMMAND ----------

# MAGIC %pip install plotly

# COMMAND ----------

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration Widgets

# COMMAND ----------

# Create Databricks widgets for user input
dbutils.widgets.removeAll()

dbutils.widgets.dropdown("model", "claude-sonnet-4", ["claude-sonnet-4", "claude-3-7-sonnet", "claude-opus-4"], "Model")
dbutils.widgets.dropdown("cloud", "aws", ["aws", "gcp", "azure"], "Cloud Provider") 
dbutils.widgets.text("tpm_millions", "8.0", "TPM (Millions)")
dbutils.widgets.text("input_tokens_per_request", "30000", "Input Tokens / Request")
dbutils.widgets.text("output_tokens_per_request", "1200", "Output Tokens / Request")
dbutils.widgets.text("caching_ratio_percent", "80.0", "Cache Hit Ratio (%)")
dbutils.widgets.text("discount_percent", "0", "Volume Discount (%)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Claude Pricing Calculator

# COMMAND ----------

class ClaudeBedrockPricing:
    def __init__(self):
        # Pricing per 1K tokens (as of January 2025)
        self.pricing = {
            "claude-sonnet-4": {
                "input_per_1k": 0.003,     # $3.00 per 1M tokens
                "output_per_1k": 0.015,    # $15.00 per 1M tokens
                "cache_write_per_1k": 0.00375,  # $3.75 per 1M tokens
                "cache_read_per_1k": 0.0003     # $0.30 per 1M tokens
            },
            "claude-3-7-sonnet": {
                "input_per_1k": 0.003,     # $3.00 per 1M tokens
                "output_per_1k": 0.015,    # $15.00 per 1M tokens
                "cache_write_per_1k": 0.00375,  # $3.75 per 1M tokens
                "cache_read_per_1k": 0.0003     # $0.30 per 1M tokens
            },
            "claude-opus-4": {
                "input_per_1k": 0.015,     # $15.00 per 1M tokens (5x Sonnet)
                "output_per_1k": 0.075,    # $75.00 per 1M tokens (5x Sonnet)
                "cache_write_per_1k": 0.01875,  # $18.75 per 1M tokens (5x Sonnet)
                "cache_read_per_1k": 0.0015     # $1.50 per 1M tokens (5x Sonnet)
            }
        }
    
    def get_pricing_for_cloud(self, model, cloud):
        """Get pricing for a model on a specific cloud provider"""
        if model not in self.pricing:
            raise ValueError(f"Model '{model}' not supported")
        
        base_pricing = self.pricing[model].copy()
        
        # Apply 50% markup for Azure
        if cloud.lower() == 'azure':
            for key in base_pricing:
                base_pricing[key] *= 1.5
        
        return base_pricing
    
    def calculate_production_cost(self, model, cloud, tpm_millions, input_tokens_per_request, 
                                output_tokens_per_request, caching_ratio_percent, discount_percent=0):
        """Calculate production cost based on TPM and usage patterns"""
        pricing = self.get_pricing_for_cloud(model, cloud)
        caching_ratio = caching_ratio_percent / 100
        discount_ratio = discount_percent / 100
        
        # Calculate requests per minute
        total_tokens_per_request = input_tokens_per_request + output_tokens_per_request
        tpm_actual = tpm_millions * 1_000_000
        requests_per_minute = tpm_actual / total_tokens_per_request
        
        # Calculate token distribution
        input_tokens_per_minute = requests_per_minute * input_tokens_per_request
        output_tokens_per_minute = requests_per_minute * output_tokens_per_request
        
        # Apply caching logic
        if caching_ratio_percent > 0:
            cache_read_tokens_per_minute = input_tokens_per_minute * caching_ratio
            regular_input_tokens_per_minute = input_tokens_per_minute * (1 - caching_ratio)
            cache_read_cost_per_minute = (cache_read_tokens_per_minute / 1000) * pricing["cache_read_per_1k"]
        else:
            cache_read_tokens_per_minute = 0
            regular_input_tokens_per_minute = input_tokens_per_minute
            cache_read_cost_per_minute = 0
        
        # Calculate costs per minute
        regular_input_cost_per_minute = (regular_input_tokens_per_minute / 1000) * pricing["input_per_1k"]
        output_cost_per_minute = (output_tokens_per_minute / 1000) * pricing["output_per_1k"]
        
        total_cost_per_minute = regular_input_cost_per_minute + output_cost_per_minute + cache_read_cost_per_minute
        
        # Calculate time-based costs
        cost_per_hour = total_cost_per_minute * 60
        cost_per_day = cost_per_hour * 24
        cost_per_month = cost_per_day * 30
        
        # Apply discount
        cost_per_day_after_discount = cost_per_day * (1 - discount_ratio)
        cost_per_month_after_discount = cost_per_month * (1 - discount_ratio)
        
        return {
            "model": model,
            "cloud": cloud,
            "tpm_millions": tpm_millions,
            "requests_per_minute": requests_per_minute,
            "requests_per_day": requests_per_minute * 60 * 24,
            "requests_per_month": requests_per_minute * 60 * 24 * 30,
            "regular_input_cost_per_minute": regular_input_cost_per_minute,
            "output_cost_per_minute": output_cost_per_minute,
            "cache_read_cost_per_minute": cache_read_cost_per_minute,
            "total_cost_per_minute": total_cost_per_minute,
            "cost_per_hour": cost_per_hour,
            "cost_per_day": cost_per_day,
            "cost_per_month": cost_per_month,
            "cost_per_day_after_discount": cost_per_day_after_discount,
            "cost_per_month_after_discount": cost_per_month_after_discount,
            "input_tokens_per_minute": input_tokens_per_minute,
            "output_tokens_per_minute": output_tokens_per_minute,
            "cache_read_tokens_per_minute": cache_read_tokens_per_minute
        }

# COMMAND ----------

# MAGIC %md
# MAGIC ## Calculate Costs

# COMMAND ----------

# Get parameters from widgets
model = dbutils.widgets.get("model")
cloud = dbutils.widgets.get("cloud")
tpm_millions = float(dbutils.widgets.get("tpm_millions"))
input_tokens_per_request = int(dbutils.widgets.get("input_tokens_per_request"))
output_tokens_per_request = int(dbutils.widgets.get("output_tokens_per_request"))
caching_ratio_percent = float(dbutils.widgets.get("caching_ratio_percent"))
discount_percent = float(dbutils.widgets.get("discount_percent"))

# Initialize calculator and compute results
calculator = ClaudeBedrockPricing()
result = calculator.calculate_production_cost(
    model, cloud, tpm_millions, input_tokens_per_request,
    output_tokens_per_request, caching_ratio_percent, discount_percent
)

# Display key metrics
print("=" * 60)
print("🎯 CLAUDE USAGE CALCULATOR RESULTS")
print("=" * 60)
print(f"Model: {result['model']}")
print(f"Cloud: {result['cloud'].upper()}")
print(f"TPM: {result['tpm_millions']:.1f}M tokens")
print()
print("📊 COST PROJECTIONS:")
print(f"  Daily Cost:   ${result['cost_per_day_after_discount']:,.2f}")
print(f"  Monthly Cost: ${result['cost_per_month_after_discount']:,.2f}")
print()
print("📈 USAGE METRICS:")
print(f"  Requests/Day:   {result['requests_per_day']:,.0f}")
print(f"  Requests/Month: {result['requests_per_month']:,.0f}")
print("=" * 60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cost Breakdown Visualization

# COMMAND ----------

# Create cost breakdown pie chart
cost_components = []
cost_values = []

if result['regular_input_cost_per_minute'] > 0:
    cost_components.append("Regular Input")
    cost_values.append(result['regular_input_cost_per_minute'] * 60)

if result['output_cost_per_minute'] > 0:
    cost_components.append("Output")
    cost_values.append(result['output_cost_per_minute'] * 60)

if result['cache_read_cost_per_minute'] > 0:
    cost_components.append("Cache Reads")
    cost_values.append(result['cache_read_cost_per_minute'] * 60)

if cost_values:
    fig_pie = px.pie(
        values=cost_values,
        names=cost_components,
        title="Hourly Cost Distribution by Component"
    )
    fig_pie.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Token Usage Analysis

# COMMAND ----------

# Create token usage bar chart
token_types = []
token_values = []

if result['input_tokens_per_minute'] - result['cache_read_tokens_per_minute'] > 0:
    token_types.append("Regular Input")
    token_values.append((result['input_tokens_per_minute'] - result['cache_read_tokens_per_minute']) * 60)

if result['cache_read_tokens_per_minute'] > 0:
    token_types.append("Cache Reads") 
    token_values.append(result['cache_read_tokens_per_minute'] * 60)

if result['output_tokens_per_minute'] > 0:
    token_types.append("Output")
    token_values.append(result['output_tokens_per_minute'] * 60)

if token_values:
    fig_bar = px.bar(
        x=token_types,
        y=token_values,
        title="Hourly Token Consumption by Type",
        labels={"y": "Tokens per Hour", "x": "Token Type"}
    )
    fig_bar.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Detailed Results Table

# COMMAND ----------

# Create detailed results DataFrame
details_data = {
    "Metric": [
        "Model",
        "Cloud Provider", 
        "TPM (Millions)",
        "Requests per Minute",
        "Cost per Minute",
        "Cost per Hour",
        "Cost per Day (before discount)",
        "Cost per Day (after discount)",
        "Cost per Month (after discount)",
        "Caching Ratio",
        "Volume Discount"
    ],
    "Value": [
        result['model'],
        result['cloud'].upper(),
        f"{result['tpm_millions']:.1f}M",
        f"{result['requests_per_minute']:,.1f}",
        f"${result['total_cost_per_minute']:,.4f}",
        f"${result['cost_per_hour']:,.2f}",
        f"${result['cost_per_day']:,.2f}",
        f"${result['cost_per_day_after_discount']:,.2f}",
        f"${result['cost_per_month_after_discount']:,.2f}",
        f"{caching_ratio_percent:.1f}%",
        f"{discount_percent:.1f}%"
    ]
}

df_details = pd.DataFrame(details_data)
display(df_details)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pricing Reference

# COMMAND ----------

# Show pricing details for current configuration
pricing_info = calculator.get_pricing_for_cloud(model, cloud)

print(f"💰 PRICING REFERENCE - {model} on {cloud.upper()}")
print("=" * 50)
print(f"Input tokens:     ${pricing_info['input_per_1k']:.6f} per 1K")
print(f"Output tokens:    ${pricing_info['output_per_1k']:.6f} per 1K") 
print(f"Cache Write:      ${pricing_info['cache_write_per_1k']:.6f} per 1K")
print(f"Cache Read:       ${pricing_info['cache_read_per_1k']:.6f} per 1K")

if cloud.lower() == 'azure':
    print("\n⚠️  Azure pricing includes 50% markup over AWS/GCP rates")

print("=" * 50)