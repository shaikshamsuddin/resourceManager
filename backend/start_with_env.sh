#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
    echo "Environment variables loaded:"
    echo "  ENVIRONMENT: $ENVIRONMENT"
    echo "  AZURE_VM_IP: $AZURE_VM_IP"
    echo "  AZURE_VM_KUBECONFIG: $AZURE_VM_KUBECONFIG"
else
    echo "Warning: .env file not found"
fi

# Start the backend application
echo "Starting Resource Manager backend..."
python app.py 