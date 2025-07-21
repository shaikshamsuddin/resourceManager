#!/bin/bash

# Start Resource Manager Backend on port 5001
# This avoids the AirPlay port conflict on macOS

echo "🚀 Starting Resource Manager Backend..."
echo "📍 Backend will be available at: http://127.0.0.1:5001"
echo "🔍 Health check endpoint: http://127.0.0.1:5001/health"
echo "📚 API docs: http://127.0.0.1:5001/apidocs/"
echo ""

cd backend
python app.py 