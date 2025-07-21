# Kubernetes Health Monitoring System

## Overview

The Resource Manager now includes a comprehensive Kubernetes health monitoring system that continuously monitors cluster health and provides real-time status information. This system is essential for production reliability and helps identify issues before they impact pod deployments.

## Features

### 🔍 **Continuous Health Monitoring**
- **Real-time monitoring** of Kubernetes cluster health
- **Background polling** every 30 seconds for cluster connectivity
- **Automatic status updates** in the frontend UI
- **Detailed health metrics** with latency tracking

### 🎯 **Health Check Types**

#### 1. **Cluster Connectivity Check**
- Verifies connection to Kubernetes API server
- Tests basic API functionality
- Measures connection latency
- **Status**: `pass` | `fail`

#### 2. **API Server Health Check**
- Checks API server responsiveness
- Monitors API server latency
- Warns if latency exceeds 1000ms
- **Status**: `pass` | `warn` | `fail`

#### 3. **Node Status Check**
- Monitors all cluster nodes
- Checks node readiness status
- Identifies failed nodes
- **Status**: `pass` | `warn` | `fail`

#### 4. **Pod Status Check**
- Monitors all pods across namespaces
- Tracks failed and pending pods
- Calculates failure percentages
- **Status**: `pass` | `warn` | `fail`

### 📊 **Cluster Status Levels**

| Status | Description | Color | Action Required |
|--------|-------------|-------|-----------------|
| `healthy` | All checks passing | 🟢 Green | None |
| `degraded` | Some warnings, no failures | 🟡 Yellow | Monitor |
| `unhealthy` | One or more failures | 🔴 Red | Immediate attention |
| `connection_failed` | Cannot connect to cluster | 🔴 Red | Check cluster |
| `auth_failed` | Authentication failed | 🔴 Red | Check credentials |
| `not_running` | Cluster not running | 🔴 Red | Start cluster |

## API Endpoints

### 1. **Basic Health Check**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "cluster_status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 2. **Detailed Health Check**
```http
GET /health/detailed
```

**Response:**
```json
{
  "cluster_status": {
    "status": "healthy",
    "last_check": "2024-01-01T00:00:00Z",
    "check_duration_ms": 245,
    "consecutive_failures": 0,
    "monitoring_active": true
  },
  "health_checks": {
    "cluster_connectivity": {
      "check_type": "cluster_connectivity",
      "status": "pass",
      "details": "Kubernetes cluster is healthy",
      "timestamp": "2024-01-01T00:00:00Z",
      "latency_ms": 45
    },
    "api_server": {
      "check_type": "api_server",
      "status": "pass",
      "details": "API server responding normally",
      "timestamp": "2024-01-01T00:00:00Z",
      "latency_ms": 120
    },
    "node_status": {
      "check_type": "node_status",
      "status": "pass",
      "details": "All 3/3 nodes ready",
      "timestamp": "2024-01-01T00:00:00Z",
      "latency_ms": 89
    },
    "pod_status": {
      "check_type": "pod_status",
      "status": "pass",
      "details": "All 12 pods healthy",
      "timestamp": "2024-01-01T00:00:00Z",
      "latency_ms": 156
    }
  }
}
```

### 3. **Cluster Status**
```http
GET /cluster-status
```

**Response:**
```json
{
  "status": "healthy",
  "last_check": "2024-01-01T00:00:00Z",
  "check_duration_ms": 245,
  "consecutive_failures": 0,
  "monitoring_active": true
}
```

## Frontend Integration

### 🎨 **Visual Indicators**

The frontend displays cluster health status with colored LED indicators:

- **🟢 Green LED**: Cluster is healthy
- **🟡 Yellow LED**: Cluster is degraded (warnings)
- **🔴 Red LED**: Cluster is unhealthy or connection failed

### 📱 **Interactive Features**

- **Click LED for details**: Shows detailed health information
- **Real-time updates**: Status updates every 30 seconds
- **Error handling**: Graceful degradation when health checks fail

### 🔄 **Polling Configuration**

```typescript
// Frontend polls cluster status every 30 seconds
this.clusterStatusInterval = setInterval(() => this.checkClusterStatus(), 30000);
```

## Configuration

### ⚙️ **Health Check Settings**

```python
class HealthCheckConfig:
    # Polling intervals (in seconds)
    CLUSTER_HEALTH_INTERVAL = 30  # Check cluster health every 30 seconds
    NODE_STATUS_INTERVAL = 60     # Check node status every 60 seconds
    POD_STATUS_INTERVAL = 120     # Check pod status every 2 minutes
    
    # Timeout values (in seconds)
    API_SERVER_TIMEOUT = 10       # API server connection timeout
    NODE_READY_TIMEOUT = 30       # Node ready check timeout
    POD_READY_TIMEOUT = 60        # Pod ready check timeout
    
    # Thresholds
    MAX_FAILED_NODES = 1          # Maximum failed nodes before unhealthy
    MAX_FAILED_PODS_PERCENT = 20  # Maximum failed pods percentage
    MAX_API_LATENCY_MS = 1000     # Maximum API server latency
```

## Error Handling

### 🚨 **Common Error Scenarios**

#### 1. **Cluster Not Running**
```json
{
  "status": "unhealthy",
  "cluster_status": "connection_failed",
  "error": "Kubernetes cluster is not running or accessible."
}
```

#### 2. **Authentication Failed**
```json
{
  "status": "unhealthy",
  "cluster_status": "auth_failed",
  "error": "Failed to authenticate with Kubernetes cluster."
}
```

#### 3. **API Server Issues**
```json
{
  "status": "unhealthy",
  "cluster_status": "unhealthy",
  "error": "Kubernetes API server is not responding."
}
```

#### 4. **Node Failures**
```json
{
  "status": "unhealthy",
  "cluster_status": "unhealthy",
  "error": "One or more Kubernetes nodes are not ready."
}
```

### 🔧 **Troubleshooting Guide**

#### **Cluster Connection Issues**
1. **Check if cluster is running**:
   ```bash
   # For minikube
   minikube status
   
   # For other clusters
   kubectl cluster-info
   ```

2. **Verify kubeconfig**:
   ```bash
   kubectl config view
   ```

3. **Test API connectivity**:
   ```bash
   kubectl get nodes
   ```

#### **Authentication Issues**
1. **Check credentials**:
   ```bash
   kubectl auth can-i get pods
   ```

2. **Verify service account** (if using in-cluster):
   ```bash
   kubectl get serviceaccount
   ```

#### **Performance Issues**
1. **Monitor API server latency**:
   ```bash
   kubectl get nodes --request-timeout=10s
   ```

2. **Check cluster resources**:
   ```bash
   kubectl top nodes
   kubectl top pods
   ```

## Production Considerations

### 🏭 **Production Deployment**

#### **1. Monitoring Frequency**
- **Development**: 30-second intervals (more frequent for debugging)
- **Production**: 60-second intervals (reduced API load)

#### **2. Alerting Integration**
```python
# Example: Send alerts when cluster becomes unhealthy
if cluster_status == ClusterStatus.UNHEALTHY:
    send_alert("Kubernetes cluster is unhealthy", health_data)
```

#### **3. Logging**
```python
# Health check results are logged for monitoring
logger.info(f"Health check completed: {cluster_status}")
logger.warning(f"Cluster degraded: {health_issues}")
logger.error(f"Cluster unhealthy: {health_issues}")
```

#### **4. Metrics Collection**
- **Prometheus metrics** for cluster health
- **Grafana dashboards** for visualization
- **AlertManager** for notifications

### 🔒 **Security Considerations**

1. **RBAC Configuration**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRole
   metadata:
     name: health-monitor
   rules:
   - apiGroups: [""]
     resources: ["nodes", "pods", "namespaces"]
     verbs: ["get", "list"]
   ```

2. **Network Policies**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: health-monitor-policy
   spec:
     podSelector:
       matchLabels:
         app: resource-manager
     policyTypes:
     - Ingress
     - Egress
   ```

## Benefits

### ✅ **Proactive Monitoring**
- **Early detection** of cluster issues
- **Preventive maintenance** based on health trends
- **Reduced downtime** through quick issue identification

### 📈 **Operational Insights**
- **Performance metrics** for API server and nodes
- **Resource utilization** tracking
- **Historical health data** for trend analysis

### 🛡️ **Reliability**
- **Automatic failover** detection
- **Graceful degradation** when cluster is unhealthy
- **User-friendly error messages** and status indicators

### 🔄 **Continuous Improvement**
- **Health trend analysis** for capacity planning
- **Performance optimization** based on latency data
- **Proactive scaling** recommendations

## Future Enhancements

### 🚀 **Planned Features**

1. **Advanced Metrics**
   - CPU/Memory usage per node
   - Network latency between nodes
   - Storage performance metrics

2. **Predictive Analytics**
   - Health trend prediction
   - Capacity planning recommendations
   - Automated scaling suggestions

3. **Integration Enhancements**
   - Slack/Teams notifications
   - PagerDuty integration
   - Custom webhook support

4. **Advanced Monitoring**
   - Custom health check definitions
   - Service-specific health checks
   - Dependency health tracking

---

This health monitoring system ensures that the Resource Manager can reliably manage Kubernetes resources while providing users with clear visibility into cluster health and performance. 