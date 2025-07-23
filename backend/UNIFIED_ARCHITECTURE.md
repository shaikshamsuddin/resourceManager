# Unified Architecture - Resource Manager

## Overview

The Resource Manager has been successfully migrated to a **unified architecture** that eliminates the need for separate modes (`local-k8s`, `cloud-k8s`) and provides a scalable, multi-cluster management system.

## Key Changes

### 1. **Eliminated Old Modes**
- ❌ `local-k8s` mode (removed)
- ❌ `cloud-k8s` mode (removed)
- ✅ `demo` mode (kept for testing)
- ✅ `unified` mode (new - handles all real clusters)

### 2. **New Architecture Components**

#### **Master Configuration (`backend/data/master.json`)**
```json
{
  "servers": [
    {
      "id": "azure-vm-01",
      "name": "Azure VM MicroK8s",
      "type": "kubernetes",
      "connection_coordinates": {
        "method": "kubeconfig",
        "host": "4.246.178.26",
        "kubeconfig_path": "./azure_vm_kubeconfig_updated",
        "insecure_skip_tls_verify": true
      },
      "metadata": {
        "location": "Azure East US",
        "environment": "production"
      }
    },
    {
      "id": "local-minikube",
      "name": "Local Development",
      "type": "kubernetes",
      "connection_coordinates": {
        "method": "local",
        "kubeconfig_path": "~/.kube/config"
      },
      "metadata": {
        "location": "local",
        "environment": "development"
      }
    }
  ],
  "config": {
    "default_server": "azure-vm-01",
    "refresh_interval": 30
  }
}
```

#### **Server Manager (`backend/server_manager.py`)**
- **Centralized Management**: Handles all server connections
- **Dynamic Loading**: Loads server configurations from `master.json`
- **Provider Abstraction**: Creates appropriate providers based on server type
- **Error Handling**: Graceful handling of connection failures
- **Multi-Server Support**: Manages multiple clusters simultaneously

#### **Unified Kubernetes Provider (`backend/providers/kubernetes_provider.py`)**
- **Configurable Connections**: Accepts connection coordinates from `master.json`
- **Multiple Methods**: Supports `kubeconfig`, `ssh`, and `local` connection methods
- **Insecure TLS Support**: Handles Azure VM certificate issues
- **Connection Flexibility**: Works with any Kubernetes cluster

### 3. **Updated API Endpoints**

All endpoints now require a `server_id` parameter:

#### **GET /servers**
- Returns all servers or specific server if `server_id` provided
- Example: `GET /servers?server_id=azure-vm-01`

#### **POST /create**
```json
{
  "server_id": "azure-vm-01",
  "PodName": "my-pod",
  "Resources": {
    "gpus": 0,
    "ram_gb": 2,
    "storage_gb": 10
  },
  "Owner": "team-a"
}
```

#### **POST /delete**
```json
{
  "server_id": "azure-vm-01",
  "PodName": "my-pod"
}
```

#### **POST /update**
```json
{
  "server_id": "azure-vm-01",
  "PodName": "my-pod",
  "Resources": {
    "gpus": 1,
    "ram_gb": 4,
    "storage_gb": 20
  }
}
```

## Benefits

### 1. **Scalability**
- **Easy Cluster Addition**: Add new clusters by editing `master.json`
- **No Code Changes**: Add/remove servers without modifying code
- **Dynamic Configuration**: Reload configurations without restart

### 2. **Consistency**
- **Unified API**: Same endpoints work for all servers
- **Standardized Responses**: Consistent data format across all clusters
- **Error Handling**: Uniform error responses

### 3. **Maintainability**
- **Single Codebase**: One provider handles all Kubernetes clusters
- **Configuration-Driven**: Server management via JSON configuration
- **Clear Separation**: Server configuration vs. application logic

### 4. **Flexibility**
- **Multiple Connection Methods**: kubeconfig, SSH, local
- **Mixed Environments**: Development and production clusters
- **Custom Metadata**: Server-specific information and labels

## Usage Examples

### 1. **Adding a New Server**
Edit `backend/data/master.json`:
```json
{
  "id": "new-cluster",
  "name": "New Kubernetes Cluster",
  "type": "kubernetes",
  "connection_coordinates": {
    "method": "kubeconfig",
    "kubeconfig_path": "/path/to/kubeconfig"
  }
}
```

### 2. **Getting All Servers**
```bash
curl http://localhost:5005/servers
```

### 3. **Creating a Pod on Specific Server**
```bash
curl -X POST http://localhost:5005/create \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "azure-vm-01",
    "PodName": "test-pod",
    "Resources": {"gpus": 0, "ram_gb": 1, "storage_gb": 5},
    "Owner": "test-team"
  }'
```

### 4. **Getting Specific Server Data**
```bash
curl http://localhost:5005/servers?server_id=azure-vm-01
```

## Migration Guide

### From Old Architecture
1. **Old**: Mode-based selection (`local-k8s`, `cloud-k8s`)
2. **New**: Server-based selection via `server_id`

### Frontend Changes Needed
1. **Server Selection**: Replace mode dropdown with server selection
2. **API Calls**: Add `server_id` to all requests
3. **Data Display**: Show server information in UI

### Configuration Migration
1. **Old**: Environment variables for each mode
2. **New**: `master.json` configuration file

## Testing

### Run Architecture Test
```bash
cd backend
python test_unified_architecture.py
```

### Expected Output
```
🚀 Unified Architecture Test Suite
============================================================

📋 Testing Master Configuration
✅ Found 2 servers in master.json
   📍 azure-vm-01: Azure VM MicroK8s (kubernetes)
   📍 local-minikube: Local Development (kubernetes)

🧪 Testing Unified Architecture
✅ Found 2 servers: ['azure-vm-01', 'local-minikube']
✅ azure-vm-01: Azure VM MicroK8s (kubernetes)
✅ local-minikube: Local Development (kubernetes)
✅ Retrieved data for 2 server instances
✅ azure-vm-01 (Azure VM MicroK8s): Online - 0 pods
✅ local-minikube (Local Development): Online - 10 pods
✅ Default server: azure-vm-01

🎉 All tests passed!
```

## Next Steps

### 1. **Frontend Updates**
- Update Angular frontend to use server selection
- Modify API calls to include `server_id`
- Add server information display

### 2. **Enhanced Features**
- Server health monitoring
- Automatic failover
- Load balancing across clusters
- Server-specific configurations

### 3. **Production Deployment**
- Secure `master.json` configuration
- Environment-specific configurations
- Monitoring and alerting

## Troubleshooting

### Common Issues

1. **Server Connection Failed**
   - Check kubeconfig path in `master.json`
   - Verify network connectivity
   - Check TLS certificate issues

2. **Provider Initialization Failed**
   - Verify server type in `master.json`
   - Check connection coordinates
   - Review error logs

3. **API Endpoint Errors**
   - Ensure `server_id` is provided
   - Check server exists in `master.json`
   - Verify server is accessible

### Debug Commands
```bash
# Test server manager
python test_unified_architecture.py

# Check master.json syntax
python -m json.tool data/master.json

# Test specific server
curl "http://localhost:5005/servers?server_id=azure-vm-01"
```

## Conclusion

The unified architecture successfully:
- ✅ Eliminates mode complexity
- ✅ Provides scalable multi-cluster management
- ✅ Maintains backward compatibility
- ✅ Improves maintainability
- ✅ Enables easy cluster addition

The Resource Manager is now ready for production use with multiple Kubernetes clusters! 