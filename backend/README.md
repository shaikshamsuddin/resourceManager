# Resource Manager Backend

A Flask-based backend for managing Kubernetes resources with a simplified approach.

## Features

- **Pod Management**: Create, update, and delete Kubernetes pods
- **Resource Tracking**: Track GPU, RAM, and storage usage across servers
- **Simplified K8s Integration**: Uses local kubeconfig instead of SSH authentication

## Setup

### Prerequisites

1. **Python 3.8+**
2. **Kubernetes cluster** (local or remote)
3. **kubeconfig** file accessible to the backend

### Installation

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Kubernetes access:**
   
   **Option A: Local kubeconfig (Recommended)**
   ```bash
   # Copy your kubeconfig to ~/.kube/config
   cp /path/to/your/kubeconfig ~/.kube/config
   ```

   **Option B: Environment variable**
   ```bash
   export KUBECONFIG=/path/to/your/kubeconfig
   ```

   **Option C: In-cluster (if running inside a pod)**
   ```bash
   # No additional setup needed - will auto-detect
   ```

### Running the Backend

```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### GET `/servers`
List all servers and their pods

### POST `/create`
Create a new pod

**Required fields:**
- `ServerName`: Target server ID
- `PodName`: Name for the new pod
- `Resources`: Resource requirements (gpus, ram_gb, storage_gb)
- `image_url`: Container image URL

**Example:**
```json
{
  "ServerName": "server-01",
  "PodName": "my-pod",
  "Resources": {
    "gpus": 1,
    "ram_gb": 64,
    "storage_gb": 100
  },
  "image_url": "nginx:latest",
  "Owner": "my-team"
}
```

### POST `/delete`
Delete a pod

**Required fields:**
- `PodName`: Name of pod to delete

### POST `/update`
Update a pod's configuration

### GET `/consistency-check`
Check data consistency across servers

## Architecture

### File Structure

```
backend/
├── app.py              # Main Flask application and API endpoints
├── utils.py            # Utility functions and Kubernetes operations
├── mock_db.json        # Mock database for server/pod data
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

### Key Components

1. **`app.py`**: Flask application with API endpoints
2. **`utils.py`**: Kubernetes operations and utility functions
3. **Mock Database**: JSON-based storage for development

### Kubernetes Integration

The backend uses a **simplified approach** that eliminates the need for:
- ❌ SSH authentication
- ❌ Machine IP addresses
- ❌ Username/password credentials

Instead, it uses:
- ✅ Local kubeconfig file
- ✅ Environment variables
- ✅ In-cluster configuration (when running inside pods)

## Development

### Adding New Features

1. **API Endpoints**: Add to `app.py`
2. **Kubernetes Operations**: Add to `utils.py`
3. **Utility Functions**: Add to `utils.py`

### Testing

Use the Swagger UI at `http://localhost:5000/apidocs/` to test API endpoints interactively.

## Troubleshooting

### Common Issues

1. **"Could not load Kubernetes configuration"**
   - Ensure kubeconfig is available at `~/.kube/config`
   - Or set `KUBECONFIG` environment variable
   - Or run inside a Kubernetes pod

2. **Permission denied errors**
   - Check if your kubeconfig has proper permissions
   - Verify cluster access with `kubectl get nodes`

3. **Resource allocation errors**
   - Check if requested resources are available on the server
   - Verify resource limits in the cluster

## Security Notes

- This is a development setup
- For production, consider:
  - Service accounts with RBAC
  - Network policies
  - Proper authentication/authorization
  - HTTPS endpoints 