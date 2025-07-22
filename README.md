# Resource Manager

A comprehensive Kubernetes resource management system with support for local development, cloud deployments, and Azure VM integration.

## Overview

The Resource Manager provides a modern web interface for managing Kubernetes resources across different environments:
- **Demo Mode**: Mock data for testing and demonstration
- **Local Kubernetes**: Local development with minikube
- **Cloud Kubernetes**: Production deployments on Azure AKS, GKE, or Azure VMs

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Kubernetes    │
│   (Angular)     │◄──►│   (Flask)       │◄──►│   Clusters      │
│   Port 4200     │    │   Port 5005     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Modes

The backend supports the following modes:

### 1. Demo Mode (`demo`)
- **Environment**: `local-mock-db`
- **Description**: Mock data for testing and demonstration
- **Features**: Realistic mock data, no real Kubernetes connection
- **Use Case**: Development, testing, demonstrations

### 2. Local Kubernetes (`local-k8s`)
- **Environment**: `development`
- **Description**: Local Kubernetes cluster (minikube)
- **Features**: Real Kubernetes operations, port management, service creation
- **Use Case**: Local development and testing

### 3. Cloud Kubernetes (`cloud-k8s`)
- **Environment**: `production`
- **Description**: Cloud Kubernetes clusters (Azure AKS, GKE, Azure VM)
- **Features**: Production-grade Kubernetes management
- **Use Case**: Production deployments, Azure VM integration

## Azure VM Integration

The Resource Manager now supports managing Kubernetes clusters running on Azure VMs using the `cloud-k8s` mode.

### Quick Start

1. **Setup Azure VM Connection**:
   ```bash
   cd backend
   python setup_azure_vm.py
   ```

2. **Configure Environment**:
   ```bash
   export AZURE_VM_IP=your-vm-ip
   export AZURE_VM_USERNAME=azureuser
   export AZURE_VM_SSH_KEY_PATH=/path/to/ssh/key
   export ENVIRONMENT=production
   ```

3. **Test Connection**:
   ```bash
   python setup_azure_vm.py test
   ```

4. **Start the Application**:
   ```bash
   # Backend
   cd backend && python app.py
   
   # Frontend (in another terminal)
   cd frontend && npm start
   ```

### Azure VM Setup Guide

For detailed Azure VM setup instructions, see [AZURE_VM_SETUP.md](backend/AZURE_VM_SETUP.md).

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- Kubernetes cluster (for non-demo modes)
- SSH access to Azure VM (for Azure VM integration)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd rm1
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   ```

### Running the Application

1. **Start Backend**:
   ```bash
   cd backend
   python app.py
   ```

2. **Start Frontend**:
   ```bash
   cd frontend
   npm start
   ```

3. **Access the Application**:
   - Frontend: http://localhost:4200
   - Backend API: http://localhost:5005
   - API Documentation: http://localhost:5005/apidocs/

## API Endpoints

- `GET /` - Application status and information
- `GET /servers` - List all servers and pods
- `POST /create` - Create a new pod
- `POST /delete` - Delete a pod
- `POST /update` - Update a pod
- `GET /mode` - Get or set backend mode
- `GET /health` - Health check
- `GET /consistency-check` - Data consistency check

## Configuration

### Environment Variables

- `ENVIRONMENT`: Set the environment (development, production, local-mock-db)
- `BACKEND_PORT`: Backend server port (default: 5005)
- `CORS_ORIGINS`: Allowed CORS origins

### Azure VM Variables

- `AZURE_VM_IP`: Azure VM IP address
- `AZURE_VM_USERNAME`: VM username (default: azureuser)
- `AZURE_VM_SSH_KEY_PATH`: Path to SSH private key
- `AZURE_VM_KUBECONFIG`: Direct path to kubeconfig file

## Development

### Project Structure

```
rm1/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── config.py              # Configuration management
│   ├── constants.py           # Constants and enums
│   ├── providers/             # Kubernetes providers
│   ├── setup_azure_vm.py      # Azure VM setup script
│   └── AZURE_VM_SETUP.md      # Azure VM setup guide
├── frontend/
│   ├── src/app/               # Angular application
│   └── package.json           # Frontend dependencies
└── README.md                  # This file
```

### Adding New Providers

To add support for new Kubernetes environments:

1. Create a new provider in `backend/providers/`
2. Update `constants.py` with new environment/mode
3. Update `config.py` with configuration
4. Add provider to `app.py`

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure ports 5005 and 4200 are available
2. **Kubernetes Connection**: Verify kubeconfig and cluster accessibility
3. **Azure VM Connection**: Check SSH connectivity and permissions
4. **CORS Issues**: Verify CORS configuration for frontend-backend communication

### Debug Mode

Enable debug logging:
```bash
export DEBUG=true
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here] 