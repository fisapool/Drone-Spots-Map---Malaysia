#!/bin/bash
# Quick start script for Drone Spots API

echo "Installing dependencies..."
pip install -r requirements_api.txt

echo ""
echo "Starting API server..."
echo "API will be available at http://localhost:8000"
echo "Documentation at http://localhost:8000/docs"
echo ""
python drone_spots_api.py

