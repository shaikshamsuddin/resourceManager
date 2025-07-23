#!/bin/bash

# Resource Manager - Complete Startup Script
# This script starts all required services for the Resource Manager application

set -e  # Exit on any error

echo "🚀 Starting Resource Manager - Complete Setup"
echo "=============================================="

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

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for service at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "Service at $url is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Service at $url failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if kubectl is installed
if ! command_exists kubectl; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

print_success "All prerequisites are installed"

# Step 1: Verify Azure VM Kubernetes Cluster Connection
print_status "Step 1: Verifying Azure VM Kubernetes Cluster Connection..."
if [ -z "$AZURE_VM_IP" ] || [ -z "$AZURE_VM_KUBECONFIG" ]; then
    print_warning "Azure VM environment variables not set. Using default kubeconfig."
    print_status "To use Azure VM cluster, set:"
    print_status "  export AZURE_VM_IP=your_azure_vm_ip"
    print_status "  export AZURE_VM_KUBECONFIG=./azure_vm_kubeconfig_updated"
else
    print_success "Azure VM environment variables detected:"
    print_status "  AZURE_VM_IP: $AZURE_VM_IP"
    print_status "  AZURE_VM_KUBECONFIG: $AZURE_VM_KUBECONFIG"
fi

# Step 2: Start Backend
print_status "Step 2: Starting Backend Service..."
cd backend

# Check if backend port is already in use
if port_in_use 5005; then
    print_warning "Port 5005 is already in use. Backend might already be running."
else
    print_status "Starting backend on port 5005..."
    # Start backend in background with environment variables
    AZURE_VM_IP=${AZURE_VM_IP:-4.246.178.26} \
    AZURE_VM_KUBECONFIG=${AZURE_VM_KUBECONFIG:-./azure_vm_kubeconfig_updated} \
    ENVIRONMENT=${ENVIRONMENT:-live} \
    python app.py > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../backend.pid
    
    # Wait for backend to be ready
    if wait_for_service "http://localhost:5005/health"; then
        print_success "Backend started successfully (PID: $BACKEND_PID)"
    else
        print_error "Backend failed to start"
        exit 1
    fi
fi

cd ..

# Step 3: Start Frontend
print_status "Step 3: Starting Frontend Service..."
cd frontend

# Check if frontend port is already in use
if port_in_use 4200; then
    print_warning "Port 4200 is already in use. Frontend might already be running."
else
    print_status "Starting frontend on port 4200..."
    # Start frontend in background
    npm start > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    
    # Wait for frontend to be ready
    if wait_for_service "http://localhost:4200"; then
        print_success "Frontend started successfully (PID: $FRONTEND_PID)"
    else
        print_error "Frontend failed to start"
        exit 1
    fi
fi

cd ..

# Step 4: Display final status
echo ""
echo "🎉 Resource Manager Startup Complete!"
echo "====================================="
print_success "Azure VM Kubernetes Cluster: Connected"
print_success "Backend: http://localhost:5005"
print_success "Frontend: http://localhost:4200"
echo ""
print_status "You can now access the Resource Manager at: http://localhost:4200"
echo ""
print_status "To stop all services, run: ./stop_all.sh"
print_status "To view logs:"
print_status "  Backend logs: tail -f backend.log"
print_status "  Frontend logs: tail -f frontend.log"
echo ""

# Save PIDs for later use
echo "BACKEND_PID=$BACKEND_PID" > .service_pids
echo "FRONTEND_PID=$FRONTEND_PID" >> .service_pids

print_success "All services started successfully! 🚀" 