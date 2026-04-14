#!/bin/bash
# Start the FastAPI backend on the internal loopback port in the background
echo "Starting Backend..."
uvicorn backend:app --host 127.0.0.1 --port 8000 &

# Start the Streamlit frontend on the external port Render assigns
echo "Starting Frontend..."
streamlit run frontend.py --server.port $PORT --server.address 0.0.0.0
