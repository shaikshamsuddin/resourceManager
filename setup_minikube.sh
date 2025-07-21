#!/bin/bash
set -e

# Minikube setup script for Resource Manager local development
# This script checks for Minikube, starts it if not running, and prints cluster info.

# Function to print a section header
echo_section() {
  echo
  echo "=============================="
  echo "$1"
  echo "=============================="
}

echo_section "Checking for Minikube installation..."
if ! command -v minikube &> /dev/null; then
  echo "Minikube is not installed."
  echo "Please install Minikube first: https://minikube.sigs.k8s.io/docs/start/"
  echo "On macOS: brew install minikube"
  echo "On Linux: curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && sudo install minikube-linux-amd64 /usr/local/bin/minikube"
  exit 1
else
  echo "Minikube found: $(minikube version | head -n 1)"
fi

echo_section "Checking for kubectl installation..."
if ! command -v kubectl &> /dev/null; then
  echo "kubectl is not installed."
  echo "Please install kubectl:"
  echo "  On macOS: brew install kubectl"
  echo "  On Linux: curl -LO \"https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl\" && sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl"
  exit 1
else
  echo "kubectl found: $(kubectl version --client --short)"
fi

echo_section "Checking Minikube status..."
if ! minikube status | grep -q "host: Running"; then
  echo "Minikube is not running. Starting Minikube..."
  minikube start --driver=docker
else
  echo "Minikube is already running."
fi

echo_section "Enabling recommended addons..."
# Uncomment the following lines to enable useful addons by default
# minikube addons enable ingress
# minikube addons enable metrics-server
# minikube addons enable dashboard

echo_section "Cluster Info"
minikube status
kubectl cluster-info
minikube ip

echo_section "Setup complete!"
echo "You can now use kubectl and run the Resource Manager backend/frontend." 