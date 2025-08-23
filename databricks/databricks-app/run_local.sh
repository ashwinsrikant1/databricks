#!/bin/bash

# Activate virtual environment and run Streamlit app
echo "🚀 Starting FMAPI Pricing Calculator..."
echo "📍 Local URL: http://localhost:8000"
echo "🛑 Press Ctrl+C to stop"
echo ""

source venv/bin/activate
streamlit run app.py --server.port 8000 --server.headless true