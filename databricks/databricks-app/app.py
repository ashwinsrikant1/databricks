import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configure Streamlit page
st.set_page_config(
    page_title="Claude Usage Calculator",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Handle Databricks Apps environment
import os
if 'DATABRICKS_RUNTIME_VERSION' in os.environ:
    st.write("🏢 Running on Databricks Apps")

class ClaudeBedrockPricing:
    def __init__(self):
        # Pricing per 1K tokens (as of January 2025)
        # Source: https://aws.amazon.com/bedrock/pricing/
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
            raise ValueError(f"Model '{model}' not supported. Available models: {list(self.pricing.keys())}")
        
        if cloud.lower() not in ['aws', 'gcp', 'azure']:
            raise ValueError(f"Cloud '{cloud}' not supported. Available clouds: aws, gcp, azure")
        
        base_pricing = self.pricing[model].copy()
        
        # Apply 50% markup for Azure
        if cloud.lower() == 'azure':
            for key in base_pricing:
                base_pricing[key] *= 1.5  # 50% markup
        
        return base_pricing
    
    def calculate_production_cost(self, model, cloud, tpm_millions, input_tokens_per_request, 
                                output_tokens_per_request, caching_ratio_percent, discount_percent=0):
        """Calculate production cost based on TPM and usage patterns"""
        pricing = self.get_pricing_for_cloud(model, cloud)
        caching_ratio = caching_ratio_percent / 100
        discount_ratio = discount_percent / 100
        
        # Calculate requests per minute
        total_tokens_per_request = input_tokens_per_request + output_tokens_per_request
        tpm_actual = tpm_millions * 1_000_000  # Convert to actual tokens
        requests_per_minute = tpm_actual / total_tokens_per_request
        
        # Calculate token distribution
        input_tokens_per_minute = requests_per_minute * input_tokens_per_request
        output_tokens_per_minute = requests_per_minute * output_tokens_per_request
        
        # Apply caching logic - only if caching_ratio_percent > 0
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
        
        # Calculate time-based costs (before discount)
        cost_per_hour = total_cost_per_minute * 60
        cost_per_day = cost_per_hour * 24
        cost_per_month = cost_per_day * 30  # 30 days
        cost_per_year = cost_per_day * 365
        
        # Apply discount to monthly and daily costs
        cost_per_day_after_discount = cost_per_day * (1 - discount_ratio)
        cost_per_month_after_discount = cost_per_month * (1 - discount_ratio)
        
        # Calculate monthly token volumes
        monthly_total_tokens = tpm_actual * 60 * 24 * 30  # 30 days
        monthly_input_tokens = input_tokens_per_minute * 60 * 24 * 30
        monthly_output_tokens = output_tokens_per_minute * 60 * 24 * 30
        monthly_cache_read_tokens = cache_read_tokens_per_minute * 60 * 24 * 30
        monthly_regular_input_tokens = regular_input_tokens_per_minute * 60 * 24 * 30
        
        return {
            "model": model,
            "cloud": cloud,
            "tpm_millions": tpm_millions,
            "input_tokens_per_request": input_tokens_per_request,
            "output_tokens_per_request": output_tokens_per_request,
            "caching_ratio_percent": caching_ratio_percent,
            "discount_percent": discount_percent,
            "requests_per_minute": requests_per_minute,
            "requests_per_day": requests_per_minute * 60 * 24,
            "requests_per_month": requests_per_minute * 60 * 24 * 30,
            # Token breakdown per minute
            "input_tokens_per_minute": input_tokens_per_minute,
            "output_tokens_per_minute": output_tokens_per_minute,
            "cache_read_tokens_per_minute": cache_read_tokens_per_minute,
            "regular_input_tokens_per_minute": regular_input_tokens_per_minute,
            # Cost breakdown per minute
            "regular_input_cost_per_minute": regular_input_cost_per_minute,
            "output_cost_per_minute": output_cost_per_minute,
            "cache_read_cost_per_minute": cache_read_cost_per_minute,
            "total_cost_per_minute": total_cost_per_minute,
            # Time-based costs (before discount)
            "cost_per_hour": cost_per_hour,
            "cost_per_day": cost_per_day,
            "cost_per_month": cost_per_month,
            "cost_per_year": cost_per_year,
            # Time-based costs (after discount)
            "cost_per_day_after_discount": cost_per_day_after_discount,
            "cost_per_month_after_discount": cost_per_month_after_discount,
            # Monthly token volumes
            "monthly_total_tokens": monthly_total_tokens,
            "monthly_input_tokens": monthly_input_tokens,
            "monthly_output_tokens": monthly_output_tokens,
            "monthly_cache_read_tokens": monthly_cache_read_tokens,
            "monthly_regular_input_tokens": monthly_regular_input_tokens
        }

def main():
    # Header
    st.title("💰 Claude Usage Calculator")
    st.markdown("### Estimate costs for Claude models on Bedrock based on TPM and usage patterns")
    
    # Initialize calculator
    calculator = ClaudeBedrockPricing()
    
    # Sidebar for inputs
    st.sidebar.header("📊 Configuration")
    
    # Model selection
    model = st.sidebar.selectbox(
        "Model",
        options=list(calculator.pricing.keys()),
        index=0,
        help="Select the Claude model you want to analyze"
    )
    
    # Cloud provider
    cloud = st.sidebar.selectbox(
        "Cloud Provider",
        options=["aws", "gcp", "azure"],
        index=0,
        help="Azure has 50% markup over AWS/GCP pricing"
    )
    
    # TPM input
    tpm_millions = st.sidebar.number_input(
        "Tokens Per Minute (Millions)",
        min_value=0.1,
        max_value=1000.0,
        value=8.0,
        step=0.1,
        help="Total tokens processed per minute (24/7 usage)"
    )
    
    # Request configuration
    st.sidebar.subheader("Request Configuration")
    input_tokens_per_request = st.sidebar.number_input(
        "Input Tokens per Request",
        min_value=1,
        max_value=200000,
        value=30000,
        step=1000,
        help="Average number of input tokens per API request"
    )
    
    output_tokens_per_request = st.sidebar.number_input(
        "Output Tokens per Request",
        min_value=1,
        max_value=200000,
        value=1200,
        step=100,
        help="Average number of output tokens per API request"
    )
    
    # Caching configuration
    st.sidebar.subheader("Cost Optimization")
    caching_ratio_percent = st.sidebar.slider(
        "Cache Hit Ratio (%)",
        min_value=0.0,
        max_value=100.0,
        value=80.0,
        step=5.0,
        help="Percentage of input tokens that benefit from caching"
    )
    
    discount_percent = st.sidebar.slider(
        "Volume Discount (%)",
        min_value=0.0,
        max_value=50.0,
        value=0.0,
        step=1.0,
        help="Negotiated discount percentage on total bill"
    )
    
    # Calculate costs
    try:
        result = calculator.calculate_production_cost(
            model, cloud, tpm_millions, input_tokens_per_request,
            output_tokens_per_request, caching_ratio_percent, discount_percent
        )
        
        # Main content area
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Daily Cost", 
                f"${result['cost_per_day_after_discount']:,.2f}",
                help="Total cost per day after discounts"
            )
        
        with col2:
            st.metric(
                "Monthly Cost", 
                f"${result['cost_per_month_after_discount']:,.2f}",
                help="Total cost per month after discounts"
            )
        
        with col3:
            st.metric(
                "Requests/Day", 
                f"{result['requests_per_day']:,.0f}",
                help="Total API requests processed per day"
            )
        
        # Detailed breakdown
        st.subheader("📈 Cost Breakdown")
        
        # Create cost breakdown chart
        cost_data = {
            "Component": ["Regular Input", "Output", "Cache Reads"],
            "Cost per Hour": [
                result['regular_input_cost_per_minute'] * 60,
                result['output_cost_per_minute'] * 60,
                result['cache_read_cost_per_minute'] * 60
            ]
        }
        
        df_costs = pd.DataFrame(cost_data)
        df_costs = df_costs[df_costs["Cost per Hour"] > 0]  # Filter out zero costs
        
        if not df_costs.empty:
            fig_costs = px.pie(
                df_costs, 
                values="Cost per Hour", 
                names="Component",
                title="Hourly Cost Distribution"
            )
            st.plotly_chart(fig_costs, use_container_width=True)
        
        # Token usage visualization
        st.subheader("🔢 Token Usage Analysis")
        
        token_data = {
            "Type": ["Regular Input", "Cache Reads", "Output"],
            "Tokens per Hour": [
                result['regular_input_tokens_per_minute'] * 60,
                result['cache_read_tokens_per_minute'] * 60,
                result['output_tokens_per_minute'] * 60
            ]
        }
        
        df_tokens = pd.DataFrame(token_data)
        df_tokens = df_tokens[df_tokens["Tokens per Hour"] > 0]
        
        if not df_tokens.empty:
            fig_tokens = px.bar(
                df_tokens,
                x="Type",
                y="Tokens per Hour",
                title="Hourly Token Consumption"
            )
            st.plotly_chart(fig_tokens, use_container_width=True)
        
        # Detailed results table
        st.subheader("📋 Detailed Results")
        
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
                f"{result['caching_ratio_percent']:.1f}%",
                f"{result['discount_percent']:.1f}%"
            ]
        }
        
        df_details = pd.DataFrame(details_data)
        st.dataframe(df_details, use_container_width=True, hide_index=True)
        
        # Pricing reference
        with st.expander("💡 Pricing Reference"):
            pricing_info = calculator.get_pricing_for_cloud(model, cloud)
            st.write(f"**{model}** on **{cloud.upper()}** (per 1K tokens):")
            st.write(f"- Input: ${pricing_info['input_per_1k']:.6f}")
            st.write(f"- Output: ${pricing_info['output_per_1k']:.6f}")
            st.write(f"- Cache Write: ${pricing_info['cache_write_per_1k']:.6f}")
            st.write(f"- Cache Read: ${pricing_info['cache_read_per_1k']:.6f}")
            
            if cloud.lower() == 'azure':
                st.info("Azure pricing includes 50% markup over AWS/GCP rates")
        
    except Exception as e:
        st.error(f"Error calculating costs: {str(e)}")
        st.stop()

if __name__ == "__main__":
    main()