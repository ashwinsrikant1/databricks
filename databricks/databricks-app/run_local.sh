#!/bin/bash

# Activate virtual environment and run Streamlit app
echo "🚀 Starting Claude Usage Calculator..."
echo "📍 Local URL: http://localhost:8521"
echo "🛑 Press Ctrl+C to stop"
echo ""

source venv/bin/activate
streamlit run app.py --server.port 8521 --server.headless true