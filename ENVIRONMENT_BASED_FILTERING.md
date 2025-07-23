# Environment-Based Server Filtering Solution

## **Problem Solved**

You wanted to work with local demo data without mixing mock servers with real servers. The solution provides **clean separation** between demo and production environments.

## **How It Works**

### **1. Environment Tags in master.json**

Each server in `master.json` now has an `environment` tag:

```json
{
  "servers": [
    {
      "id": "azure-vm-01",
      "name": "Azure VM MicroK8s", 
      "type": "kubernetes",
      "environment": "live",  // ← Real server
      "connection_coordinates": { ... }
    },
    {
      "id": "demo-server-01",
      "name": "Demo Server Alpha",
      "type": "mock", 
      "environment": "demo",     // ← Demo server
      "connection_coordinates": { ... }
    }
  ]
}
```

### **2. Environment-Based Filtering**

The backend filters servers based on the current mode:

- **Demo Mode** (`environment: "demo"`) → Shows only demo servers
- **Live Mode** (`environment: "live"`) → Shows only real servers

### **3. Separate Data Providers**

- **Demo Data Provider**: Generates realistic mock data for demo servers
- **Kubernetes Provider**: Handles real Kubernetes clusters

## **User Experience**

### **Demo Mode**
- ✅ Shows only demo servers (Demo Server Alpha, Demo Server Beta)
- ✅ Realistic mock data with pre-populated pods
- ✅ Full UI functionality
- ✅ No real Kubernetes required
- ✅ Perfect for demos and testing

### **Live Mode (Local/Cloud K8s)**
- ✅ Shows only real servers (Azure VM, Local Minikube)
- ✅ Real Kubernetes operations
- ✅ Live cluster data
- ✅ Production-ready features

## **Benefits**

### **Clean Separation**
- **No mixing**: Demo and real servers never appear together
- **Clear boundaries**: Each mode has its own data source
- **Predictable behavior**: Users know exactly what they're working with

### **Flexible Architecture**
- **Easy to add**: New demo servers via `master.json`
- **Scalable**: Multiple real clusters supported
- **Maintainable**: Clear separation of concerns

### **User-Friendly**
- **Familiar UI**: Same interface for both modes
- **Clear selection**: Server selection only in "Choose a Server" card
- **Visual feedback**: Selected server highlighted

## **Technical Implementation**

### **Backend Changes**

1. **ServerManager**: Added environment filtering
2. **Demo Data Provider**: New provider for realistic mock data
3. **API Endpoints**: Filter servers by environment
4. **master.json**: Added environment tags to all servers

### **Frontend Changes**

1. **Mode Configuration**: Updated to use new environment values
2. **Server Selection**: Exclusive to "Choose a Server" card
3. **Visual Feedback**: Clear indication of selected server

## **Usage Examples**

### **For Demos**
1. Select "Demo Mode" from header
2. See only demo servers in selection card
3. Work with realistic mock data
4. No real infrastructure needed

### **For Development/Production**
1. Select "Live Mode" from header  
2. See only real servers (minikube, Azure VM, etc.)
3. Work with actual Kubernetes clusters
4. Real pod operations

## **Configuration**

### **Adding Demo Servers**
```json
{
  "id": "new-demo-server",
  "name": "New Demo Server",
  "type": "mock",
  "environment": "demo",
  "connection_coordinates": {
    "method": "mock"
  }
}
```

### **Adding Real Servers**
```json
{
  "id": "new-k8s-server", 
  "name": "New Kubernetes Server",
  "type": "kubernetes",
  "environment": "live",
  "connection_coordinates": {
    "method": "kubeconfig",
    "host": "your-server.com"
  }
}
```

## **Result**

✅ **Perfect Solution**: You can now work with local demo data without any mixing
✅ **Clean Separation**: Demo and real servers are completely isolated
✅ **Familiar Interface**: Same UI, different data sources
✅ **Scalable**: Easy to add more servers to either environment
✅ **Maintainable**: Clear architecture with environment-based filtering

The system now provides exactly what you wanted: **clean separation between demo and real environments** while maintaining the familiar mode-based UI! 🎉 