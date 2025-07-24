# Resource Manager

A comprehensive Kubernetes resource management system with independent Frontend and Backend components.

## 🏗️ Architecture

This project is designed with **complete independence** between Frontend (FE) and Backend (BE) components, preparing for future project splits.

### **🎯 Independent Components**

**✅ BACKEND (Flask API)**
- Complete REST API for Kubernetes management
- Server configuration and health monitoring
- Pod lifecycle management
- Independent startup/shutdown/deployment scripts
- Own documentation, tests, and development tools

**✅ FRONTEND (Angular UI)**
- Modern web interface for resource management
- Real-time server status monitoring
- Pod creation, editing, and deletion
- Independent startup/shutdown/deployment scripts
- Own documentation, tests, and development tools

**✅ COMPLETE INDEPENDENCE**
- Each component has its own API contracts
- No shared dependencies
- Independent development and deployment

## 🚀 Quick Start

### **Start Components Independently**

**Backend Only:**
```bash
cd backend
./deploy.sh
# Backend available at: http://localhost:5005
```

**Frontend Only:**
```bash
cd frontend
./deploy.sh
# Frontend available at: http://localhost:4200
```

## 📁 Project Structure

```
rm1/
├── README.md                    # Main project overview

├── backend/                     # Completely independent backend
│   ├── app.py                  # Main Flask app
│   ├── server_configuration_api.py
│   ├── server_manager.py
│   ├── k8s_client.py, health_monitor.py
│   ├── kubernetes_resource_manager.py
│   ├── config.py, constants.py, utils.py
│   ├── data/, providers/, apipayloads/
│   ├── requirements.txt, env.example
│   ├── README.md               # Backend-specific docs
│   ├── start.sh, stop.sh, deploy.sh
│   ├── tests/, docs/, scripts/
│   ├── dev/, logs/
│   └── .gitignore
├── frontend/                    # Completely independent frontend
│   ├── main.ts                 # Main entry point
│   ├── core/                   # Core application files
│   ├── components/             # Angular components
│   ├── config/                 # Configuration files (including angular.json, tsconfig)
│   ├── styles/                 # Style files
│   ├── assets/                 # Assets
│   ├── package.json            # Node.js dependencies
│   ├── docs/                   # Documentation (README.md, STRUCTURE.md)
│   ├── start.sh, stop.sh, deploy.sh  # Root scripts (call scripts/ directory)
│   ├── scripts/
│   └── .gitignore

```

## 🔧 Development

### **Backend Development**
```bash
cd backend
./start.sh          # Start backend
./stop.sh           # Stop backend
./deploy.sh         # Deploy backend
tail -f logs/backend.log  # View logs
```

### **Frontend Development**
```bash
cd frontend
./start.sh          # Start frontend
./stop.sh           # Stop frontend
./deploy.sh         # Deploy frontend
tail -f logs/frontend.log  # View logs
```

### **Testing**
```bash
# Backend tests
cd backend/tests
python -m pytest

# Frontend tests
cd frontend/tests
npm test
```

## 📋 Features

### **Server Management**
- Configure Kubernetes clusters via Azure VMs
- Real-time server health monitoring
- Server templates for quick setup
- Automatic kubeconfig retrieval

### **Pod Management**
- Create, edit, and delete Kubernetes pods
- Resource allocation (GPU, RAM, Storage)
- Multi-cluster pod deployment
- Resource usage tracking

### **User Interface**
- Modern Angular Material design
- Real-time status updates
- Comprehensive error handling
- Responsive mobile-friendly interface

## 🔗 API Integration

### **Backend API Endpoints**
- `GET /api/server-config/servers` - List servers
- `POST /api/server-config/configure` - Configure server
- `GET /api/k8s/pods` - List pods
- `POST /api/k8s/pods` - Create pod
- `PUT /api/k8s/pods/<id>` - Update pod
- `DELETE /api/k8s/pods/<id>` - Delete pod

### **Frontend-Backend Communication**
- RESTful API calls
- JSON request/response format
- Error handling and retry logic
- Real-time status updates

## 🛠️ Configuration

### **Backend Configuration**
- Environment variables in `backend/env.example`
- Server configurations in `backend/data/master.json`
- API documentation at `http://localhost:5005/apidocs`

### **Frontend Configuration**
- API endpoint in `frontend/src/config/api.config.ts`
- Environment files in `frontend/src/environments/`
- Angular configuration in `frontend/angular.json`

## 🔍 Troubleshooting

### **Common Issues**

1. **Port conflicts:**
   ```bash
   # Backend port 5005
   lsof -i :5005 && kill -9 <PID>
   
   # Frontend port 4200
   lsof -i :4200 && kill -9 <PID>
   ```

2. **Backend connection issues:**
   - Verify Azure VM credentials in `backend/data/master.json`
   - Check SSH connectivity to VMs
   - Ensure MicroK8s is running on VMs

3. **Frontend-Backend communication:**
   - Verify backend is running on port 5005
   - Check API configuration in frontend
   - Ensure CORS is properly configured

### **Logs**
- **Backend logs:** `backend/logs/backend.log`
- **Frontend logs:** `frontend/logs/frontend.log`
- **Application logs:** Check respective component directories

## 📚 Documentation

### **Component-Specific Docs**
- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)
- [API Documentation](http://localhost:5005/apidocs) (when backend is running)

### **Architecture Docs**
- [Backend Architecture](backend/docs/)
- [Frontend Architecture](frontend/docs/)
- [Backend API Contracts](backend/api-contracts/)
- [Frontend API Contracts](frontend/api-contracts/)

## 🚀 Deployment

### **Independent Deployment**
Each component can be deployed independently:

**Backend Deployment:**
```bash
cd backend
./deploy.sh
```

**Frontend Deployment:**
```bash
cd frontend
./deploy.sh
```

### **Production Considerations**
- Use environment-specific configurations
- Implement proper security measures
- Set up monitoring and logging
- Configure load balancing if needed

## 🤝 Contributing

1. **Backend contributions:** Follow Python/Flask best practices
2. **Frontend contributions:** Follow Angular style guide
3. **Documentation:** Update relevant README files
4. **Testing:** Add tests for new features
5. **Scripts:** Ensure all scripts are executable

## 📄 License

On-premise application - internal use only.

---

## 🎯 Future Project Split

This architecture is designed to facilitate easy separation into independent projects:

- **Backend** can become a standalone Kubernetes management API with its own API contracts
- **Frontend** can become a standalone web interface with its own API contracts
- **Zero shared dependencies** - each component is completely self-contained
- **Independent deployment** and scaling capabilities
- **Contract-driven development** ensures compatibility even after split 