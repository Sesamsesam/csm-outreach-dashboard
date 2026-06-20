#!/bin/bash
# CSM Dashboard launcher
# Run this once to install Flask, then it starts the server.

echo "Installing Flask (one-time)..."
pip3 install flask --quiet

echo ""
echo "Starting dashboard at http://localhost:5001 ..."
echo "Press Ctrl+C to stop."
echo ""

cd "$(dirname "$0")"
python3 app.py
