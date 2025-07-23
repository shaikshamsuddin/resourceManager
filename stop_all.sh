#!/bin/bash

# Resource Manager - Complete Shutdown Script
# This script stops all services started by start_all.sh

echo "🛑 Stopping Resource Manager - Complete Shutdown"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a process is running
process_running() {
    ps -p $1 >/dev/null 2>&1
}

# Step 1: Stop Frontend
print_status "Step 1: Stopping Frontend Service..."
if [ -f "frontend.pid" ]; then
    FRONTEND_PID=$(cat frontend.pid)
    if process_running $FRONTEND_PID; then
        print_status "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        sleep 2
        if process_running $FRONTEND_PID; then
            print_warning "Frontend didn't stop gracefully, force killing..."
            kill -9 $FRONTEND_PID
        fi
        print_success "Frontend stopped"
    else
        print_warning "Frontend process not running"
    fi
    rm -f frontend.pid
else
    print_warning "Frontend PID file not found"
fi

# Step 2: Stop Backend
print_status "Step 2: Stopping Backend Service..."
if [ -f "backend.pid" ]; then
    BACKEND_PID=$(cat backend.pid)
    if process_running $BACKEND_PID; then
        print_status "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        sleep 2
        if process_running $BACKEND_PID; then
            print_warning "Backend didn't stop gracefully, force killing..."
            kill -9 $BACKEND_PID
        fi
        print_success "Backend stopped"
    else
        print_warning "Backend process not running"
    fi
    rm -f backend.pid
else
    print_warning "Backend PID file not found"
fi

# Clean up
print_status "Cleaning up..."
rm -f .service_pids
print_success "Cleanup completed"

echo ""
echo "🎉 Resource Manager Shutdown Complete!"
echo "======================================"
print_success "All services stopped successfully!"
echo ""
print_status "Note: Azure VM Kubernetes cluster remains running."
print_status "To stop the cluster, you would need to stop the Azure VM itself." 