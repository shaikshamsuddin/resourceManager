# Resource Manager - Phase 3 Deployment Guide

This guide explains how to migrate from Phase 2 (development) to Phase 3 (production) deployment on Azure VM.

## Architecture Overview

### Phase 2 (Current - Development)
- **Backend**: Local Flask app with local kubeconfig
- **Frontend**: Angular app with simplified UI
- **Kubernetes**: Local minikube cluster
- **Authentication**: Local kubeconfig file

### Phase 3 (Production - Azure)
- **Backend**: Flask app on Azure VM with Azure AKS integration
- **Frontend**: Angular app with full features
- **Kubernetes**: Azure AKS cluster
- **Authentication**: Azure managed identity

## Migration Steps

### 1. Backend Deployment

#### Prerequisites
- Azure subscription
- Azure AKS cluster
- Azure VM for backend deployment

#### Environment Configuration
```bash
# Copy example environment file
cp backend/env.example backend/.env

# Update .env with production values
ENVIRONMENT=production
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_AKS_CLUSTER_NAME=your-aks-cluster-name
AZURE_USE_MANAGED_IDENTITY=true
CORS_ORIGINS=https://your-frontend-domain.com
```

#### Azure AKS Integration
```python
# Add to requirements.txt for production
azure-identity>=1.12.0
azure-mgmt-containerservice>=20.0.0
```

#### Deploy Backend to Azure VM
```bash
# On Azure VM
git clone <your-repo>
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export ENVIRONMENT=production
export AZURE_SUBSCRIPTION_ID=your-subscription-id
# ... other environment variables

# Run backend
python app.py
```

### 2. Frontend Deployment

#### Environment Detection
The frontend automatically detects the environment:
- **Development**: `localhost` or `127.0.0.1`
- **Production**: Any other domain

#### Build for Production
```bash
# Build Angular app
ng build --configuration production

# Deploy to web server (nginx, Apache, etc.)
```

#### Environment-Specific Features
- **Development**: Simplified UI, no Image URL required
- **Production**: Full UI, Image URL required, advanced features

### 3. Azure AKS Setup

#### Create AKS Cluster
```bash
# Create resource group
az group create --name myResourceGroup --location eastus

# Create AKS cluster
az aks create \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --node-count 1 \
  --enable-addons monitoring \
  --generate-ssh-keys
```

#### Configure Backend Access
```bash
# Get credentials for AKS
az aks get-credentials --resource-group myResourceGroup --name myAKSCluster

# Create service account for backend
kubectl create serviceaccount resource-manager-backend
kubectl create clusterrolebinding resource-manager-backend \
  --clusterrole=cluster-admin \
  --serviceaccount=default:resource-manager-backend
```

### 4. Configuration Files

#### Backend Configuration (`config.py`)
```python
# Automatically switches between environments
if Config.is_production():
    # Use Azure AKS authentication
    k8s_client._init_azure_aks()
else:
    # Use local kubeconfig
    k8s_client._init_local_kubeconfig()
```

#### Frontend Configuration (`environment.config.ts`)
```typescript
// Automatically detects environment
if (environmentService.isProduction()) {
  // Show Image URL field, enable advanced features
  this.requireImageUrl = true;
  this.enableAdvancedFeatures = true;
} else {
  // Hide Image URL field, use defaults
  this.requireImageUrl = false;
  this.enableAdvancedFeatures = false;
}
```

## Environment Variables

### Development
```bash
ENVIRONMENT=development
FLASK_DEBUG=true
```

### Production
```bash
ENVIRONMENT=production
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_AKS_CLUSTER_NAME=your-aks-cluster-name
AZURE_USE_MANAGED_IDENTITY=true
CORS_ORIGINS=https://your-frontend-domain.com
FLASK_DEBUG=false
```

## Testing Migration

### 1. Test Backend
```bash
# Test local development
ENVIRONMENT=development python app.py

# Test production mode
ENVIRONMENT=production python app.py
```

### 2. Test Frontend
```bash
# Development mode (localhost)
ng serve

# Production mode (build and serve)
ng build --configuration production
```

### 3. Test Kubernetes Integration
```bash
# Test pod creation
curl -X POST http://localhost:5000/create \
  -H "Content-Type: application/json" \
  -d '{"ServerName":"server-01","PodName":"testpod","Resources":{"gpus":1,"ram_gb":64,"storage_gb":100}}'

# Verify pod creation
kubectl get pods -A
```

## Troubleshooting

### Common Issues

1. **Kubernetes Connection Failed**
   - Check AKS cluster status: `az aks show --name myAKSCluster --resource-group myResourceGroup`
   - Verify credentials: `kubectl cluster-info`

2. **CORS Errors**
   - Update CORS_ORIGINS in environment variables
   - Check frontend domain configuration

3. **Azure Authentication Failed**
   - Verify managed identity is enabled
   - Check Azure subscription and resource group

4. **Image URL Required in Development**
   - Check ENVIRONMENT variable is set to 'development'
   - Verify frontend environment detection

## Security Considerations

### Production Security
- Use Azure managed identity instead of service principal
- Enable RBAC on AKS cluster
- Use HTTPS for all communications
- Implement proper authentication/authorization
- Use network policies to restrict pod communication

### Environment Isolation
- Separate development and production clusters
- Use different namespaces for different environments
- Implement resource quotas and limits

## Monitoring and Logging

### Azure Monitor Integration
```python
# Add to backend for production monitoring
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=your-key-here')
)
```

### Kubernetes Monitoring
```bash
# Enable Azure Monitor for containers
az aks enable-addons --addons monitoring --name myAKSCluster --resource-group myResourceGroup
```

## Rollback Plan

If issues occur during migration:

1. **Backend Rollback**
   ```bash
   # Switch back to development mode
   export ENVIRONMENT=development
   python app.py
   ```

2. **Frontend Rollback**
   ```bash
   # Revert to development build
   ng serve
   ```

3. **Database Rollback**
   ```bash
   # Restore from backup
   cp backup/mock_db.json backend/mock_db.json
   ```

## Support

For issues during migration:
1. Check logs: `kubectl logs -f deployment/resource-manager-backend`
2. Verify configuration: `python -c "from config import Config; print(Config.get_kubernetes_config())"`
3. Test connectivity: `kubectl cluster-info` 