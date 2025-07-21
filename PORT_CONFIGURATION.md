# Port Configuration Strategy

## 🎯 **Overview**

This document explains our **hybrid port configuration strategy** that balances reliability with flexibility for both backend and Kubernetes connectivity.

## 🏗️ **Architecture**

### **Backend Port Configuration**
```
Environment Variable → Dynamic Detection → Hardcoded Default
       ↓                      ↓                ↓
   BACKEND_PORT=5005    (Not applicable)    Ports.BACKEND_DEFAULT = 5005
```

### **Kubernetes Port Configuration**
```
Environment Variable → Dynamic Detection → Hardcoded Default
       ↓                      ↓                ↓
KUBERNETES_API_PORT=53492  kubectl config    Ports.MINIKUBE_DEFAULT = 53492
```

## 📋 **Configuration Options**

### **1. Environment Variables (Recommended for Production)**

```bash
# Backend port
export BACKEND_PORT=5005

# Kubernetes API port
export KUBERNETES_API_PORT=53492
```

### **2. Dynamic Detection (Automatic)**

The system automatically detects minikube ports using:
```bash
kubectl config view --minify --output jsonpath={.clusters[0].cluster.server}
```

### **3. Hardcoded Defaults (Fallback)**

If neither environment variables nor dynamic detection work, the system falls back to:
- **Backend**: `5005`
- **Kubernetes**: `53492`

## 🔧 **Implementation Details**

### **Backend (`backend/constants.py`)**

```python
class Ports:
    BACKEND_DEFAULT = 5001
    KUBERNETES_API_DEFAULT = 8443
    MINIKUBE_DEFAULT = 53492
    
    @classmethod
    def get_backend_port(cls) -> int:
        return int(os.getenv(cls.BACKEND_PORT_ENV, cls.BACKEND_DEFAULT))
    
    @classmethod
    def get_kubernetes_port(cls) -> int:
        # Try environment variable first
        env_port = os.getenv(cls.KUBERNETES_API_PORT_ENV)
        if env_port:
            return int(env_port)
        
        # Try dynamic detection
        detected_port = cls.detect_minikube_port()
        if detected_port:
            return detected_port
        
        # Fallback to default
        return cls.MINIKUBE_DEFAULT
```

### **Frontend (`frontend/src/environments/environment.ts`)**

```typescript
export const environment = {
  production: false,
  api: {
    host: '127.0.0.1',
    port: 5001,  // Can be overridden by environment variable BACKEND_PORT
    protocol: 'http'
  }
};
```

## 🚀 **Usage Examples**

### **Development (Default)**
```bash
# No environment variables needed - uses defaults
cd backend && python app.py
cd frontend && npm start
```

### **Custom Backend Port**
```bash
# Set custom backend port
export BACKEND_PORT=8080
cd backend && python app.py

# Update frontend environment.ts to match
# port: 8080
```

### **Custom Kubernetes Port**
```bash
# Set custom Kubernetes port
export KUBERNETES_API_PORT=6443
cd backend && python app.py
```

### **Production Deployment**
```bash
# Production environment
export BACKEND_PORT=80
export KUBERNETES_API_PORT=6443
export NODE_ENV=production
```

## 🔍 **Troubleshooting**

### **Port Conflicts**
```bash
# Check what's using a port
lsof -i :5001

# Kill process using port
kill -9 $(lsof -t -i:5001)
```

### **Minikube Port Detection**
```bash
# Check current minikube port
kubectl config view --minify --output jsonpath={.clusters[0].cluster.server}

# Restart minikube if needed
minikube stop && minikube start
```

### **Frontend-Backend Mismatch**
```bash
# Check backend is running on expected port
curl http://127.0.0.1:5005/health

# Check frontend environment configuration
cat frontend/src/environments/environment.ts
```

## 📊 **Why This Strategy?**

### **✅ Advantages**

1. **Flexibility**: Environment variables allow easy port changes
2. **Reliability**: Dynamic detection handles minikube port changes
3. **Simplicity**: Defaults work out-of-the-box for development
4. **Production Ready**: Environment variables for deployment
5. **No Hardcoding**: Ports can be changed without code modifications

### **🔄 Fallback Chain**

1. **Environment Variable** (Highest Priority)
2. **Dynamic Detection** (Automatic)
3. **Hardcoded Default** (Safety Net)

### **🎯 Use Cases**

- **Development**: Uses defaults automatically
- **Testing**: Environment variables for different ports
- **Production**: Environment variables for deployment
- **CI/CD**: Dynamic detection for automated environments

## 🔧 **Migration Guide**

### **From Hardcoded Ports**
```python
# Old way
app.run(debug=True, port=5001)

# New way
port = Ports.get_backend_port()
app.run(debug=True, port=port)
```

### **From Frontend Hardcoded URLs**
```typescript
// Old way
const apiUrl = 'http://127.0.0.1:5001/api';

// New way
import { ApiConfig } from './config/api.config';
const apiUrl = ApiConfig.getBaseUrl() + '/api';
```

## 📝 **Best Practices**

1. **Use Environment Variables** for production deployments
2. **Keep Defaults Sensible** for development
3. **Document Port Changes** in deployment guides
4. **Test Port Detection** after minikube restarts
5. **Monitor Port Conflicts** during development

## 🎉 **Benefits Achieved**

- ✅ **No More Port Conflicts**: Easy to change ports
- ✅ **Environment Aware**: Different ports for dev/staging/prod
- ✅ **Minikube Compatible**: Handles dynamic port changes
- ✅ **Production Ready**: Environment variable support
- ✅ **Developer Friendly**: Works out-of-the-box
- ✅ **Maintainable**: Centralized port configuration 