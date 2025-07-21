"""
Resource Manager Backend API
This module contains the Flask application and API endpoints for managing Kubernetes resources.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
from flasgger import Swagger

# Import configuration and utility functions
from config import Config
from utils import (
    get_available_resources,
    validate_resource_request,
    create_k8s_resources_simple,
    delete_k8s_resources_simple,
    create_pod_object,
    update_pod_object
)
from providers.mock_data_provider import mock_data_provider
from providers.kubernetes_provider import local_kubernetes_provider
from providers.cloud_kubernetes_provider import cloud_kubernetes_provider
from health_monitor import health_monitor
from constants import Ports, PodStatus, Environment

app = Flask(__name__)

# Configure CORS based on environment
cors_origins = Config.get_cors_origins()
if cors_origins:
    CORS(app, origins=cors_origins)
else:
    CORS(app)

# Configure Swagger based on environment
if Config.get_api_config()['enable_swagger']:
    swagger = Swagger(app)

MOCK_DB_JSON = os.path.join(os.path.dirname(__file__), 'data', 'mock_db.json')


def load_data():
    """Load data from mock database JSON file."""
    with open(MOCK_DB_JSON, 'r') as f:
        return json.load(f)


def save_data(data):
    """Save data to mock database JSON file."""
    with open(MOCK_DB_JSON, 'w') as f:
        json.dump(data, f, indent=2)

# --- API Endpoints ---
@app.route('/')
def index():
    return '''
    <h1>🎉 Resource Manager Backend is Running! 🎉</h1>
    <p>Welcome! Available API endpoints:</p>
    <ul>
      <li><b>GET /servers</b> - List all servers and pods</li>
      <li><b>POST /create</b> - Create a new pod (JSON body required)</li>
      <li><b>POST /delete</b> - Delete a pod (JSON body required)</li>
      <li><b>POST /update</b> - Update a pod (JSON body required)</li>
      <li><b>GET /consistency-check</b> - Check for data consistency</li>
    </ul>
    <p><b>API Testing & Documentation:</b></p>
    <p>Access <a href="http://127.0.0.1:5000/apidocs/" target="_blank">Swagger UI</a> to view, send, and test API calls interactively.</p>
    <p>Swagger provides a user-friendly interface for exploring and trying out all backend endpoints.</p>
    <p><b>Frontend UI:</b></p>
    <p>Access the <a href="http://127.0.0.1:4200/" target="_blank">Resource Manager Frontend</a> for a modern, user-friendly web interface.</p>
    '''

@app.route('/servers', methods=['GET'])
def get_servers_mdem():
    """
    List all servers and pods (real Kubernetes data)
    ---
    tags:
      - Servers
    responses:
      200:
        description: List of all servers and their pods from Kubernetes
        examples:
          application/json:
            - id: node-01
              name: minikube
              resources:
                total: { gpus: 0, ram_gb: 8, storage_gb: 60 }
                available: { gpus: 0, ram_gb: 6, storage_gb: 58 }
              pods: []
      500:
        description: Server error
        examples:
          application/json:
            error: "Server error"
            details: "<details>"
    """
    try:
        # Use appropriate provider based on environment
        if Config.ENVIRONMENT.value == Environment.LOCAL_MOCK_DB.value:
            # Use mock data provider for demo mode
            servers = mock_data_provider.get_servers_with_pods_mdem()
        elif Config.ENVIRONMENT.value == Environment.DEVELOPMENT.value:
            # Use local Kubernetes provider
            servers = local_kubernetes_provider.get_servers_with_pods()
        elif Config.ENVIRONMENT.value == Environment.PRODUCTION.value:
            # Use cloud Kubernetes provider
            servers = cloud_kubernetes_provider.get_servers_with_pods()
        else:
            # Fallback to mock data
            servers = mock_data_provider.get_servers_with_pods_mdem()
        
        return jsonify(servers), 200
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/create', methods=['POST'])
def create_pod_mdem():
    try:
        req = request.json
        if req is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        # Get required fields based on environment
        required_fields = ["ServerName", "PodName", "Resources"]
        if Config.require_image_url():
            required_fields.append("image_url")
        errors = []
        missing = [f for f in required_fields if f not in req or not req[f]]
        if missing:
            errors.append(f"Missing required field: {', '.join(missing)}")
        pod_name = req.get('PodName', '')
        if not isinstance(pod_name, str) or not pod_name:
            errors.append("Pod name is required.")
        else:
            if not pod_name.islower():
                errors.append("Pod name must be lowercase.")
            if "_" in pod_name:
                errors.append("Pod name must not contain underscores.")
        
        server_id = req.get('ServerName')
        resources = req.get('Resources', {})
        owner = req.get('Owner', 'unknown')
        
        # Get data based on environment
        if Config.ENVIRONMENT.value == Environment.LOCAL_MOCK_DB.value:
            servers = mock_data_provider.get_servers_with_pods_mdem()
        elif Config.ENVIRONMENT.value == Environment.DEVELOPMENT.value:
            servers = local_kubernetes_provider.get_servers_with_pods()
        elif Config.ENVIRONMENT.value == Environment.PRODUCTION.value:
            servers = cloud_kubernetes_provider.get_servers_with_pods()
        else:
            servers = mock_data_provider.get_servers_with_pods_mdem()
        
        server = next((s for s in servers if s['id'] == server_id), None)
        if not server:
            errors.append(f"Server '{server_id}' not found.")
            return jsonify({'error': " | ".join(errors)}), 404
            
        if not isinstance(resources, dict):
            errors.append('Resources must be a dictionary/object')
            return jsonify({'error': " | ".join(errors)}), 400
            
        ok, err = validate_resource_request(server, resources)
        if not ok:
            errors.append(err)
            return jsonify({'error': " | ".join(errors)}), 400
            
        # Validate resources against real Kubernetes node
        if not isinstance(server.get('resources'), dict):
            errors.append('Server resources not available')
            return jsonify({'error': " | ".join(errors)}), 400
            
        # Check if resources are available
        available = server['resources'].get('available', {})
        for key in ['gpus', 'ram_gb', 'storage_gb']:
            if resources.get(key, 0) > available.get(key, 0):
                errors.append(f"Insufficient {key}: requested {resources.get(key, 0)}, available {available.get(key, 0)}")
                return jsonify({'error': " | ".join(errors)}), 400
        
        # Create pod object
        pod = create_pod_object({
            'PodName': pod_name,
            'Resources': resources,
            'Owner': owner
        }, server_id)
        
        try:
            if Config.ENVIRONMENT.value == Environment.LOCAL_MOCK_DB.value:
                # Add to mock data
                if mock_data_provider.add_pod_mdem(server_id, pod):
                    return jsonify({'message': 'Pod created', 'pod': pod}), 200
                else:
                    return jsonify({'error': 'Failed to add pod to mock data'}), 500
            else:
                # Create real Kubernetes resources
                create_k8s_resources_simple(pod)
                return jsonify({'message': 'Pod created', 'pod': pod}), 200
            
        except Exception as e:
            return jsonify({'error': f'Pod creation error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': 'Server error', 'details': str(e)}), 500

@app.route('/delete', methods=['POST'])
def delete_pod_mdem():
    """
    Delete a pod
    ---
    tags:
      - Pods
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            PodName:
              type: string
    responses:
      200:
        description: Pod deleted
        examples:
          application/json:
            message: Pod deleted
      400:
        description: Missing fields
        examples:
          application/json:
            error: "Missing required field: PodName"
      404:
        description: Pod not found
        examples:
          application/json:
            error: "Pod 'testpod123' not found on any server."
      500:
        description: Server error
        examples:
          application/json:
            error: "Server error"
            details: "<details>"
    """
    try:
        req = request.json
        if req is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        required_fields = ["PodName"]
        missing = [f for f in required_fields if f not in req or not req[f]]
        if missing:
            return jsonify({'error': f"Missing required field: {', '.join(missing)}"}), 400
        pod_name = req['PodName']
        
        # Handle deletion based on environment
        if Config.ENVIRONMENT.value == Environment.LOCAL_MOCK_DB.value:
            # Delete from mock data
            if mock_data_provider.remove_pod(pod_name):
                return jsonify({'message': 'Pod deleted'}), 200
            else:
                return jsonify({'error': f"Pod '{pod_name}' not found on any server."}), 404
        else:
            # Delete from real Kubernetes
            try:
                delete_k8s_resources_simple({'pod_id': pod_name})
                return jsonify({'message': 'Pod deleted'}), 200
            except Exception as e:
                return jsonify({'error': f'Kubernetes deletion error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': 'Server error', 'details': str(e)}), 500

@app.route('/update', methods=['POST'])
def update_pod_mdem():
    """
    Update a pod
    ---
    tags:
      - Pods
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            ServerName:
              type: string
            PodName:
              type: string
            Resources:
              type: object
              properties:
                gpus:
                  type: integer
                ram_gb:
                  type: integer
                storage_gb:
                  type: integer
            image_url:
              type: string
            machine_ip:
              type: string
            Owner:
              type: string
    responses:
      200:
        description: Pod updated
        examples:
          application/json:
            message: Pod updated
            pod:
              pod_id: testpod123
              owner: test-team
              status: running
              timestamp: 2024-07-01T12:00:00Z
              requested:
                gpus: 1
                ram_gb: 64
                storage_gb: 100
              image_url: https://docker.io/library/nginx:latest
              registery_url: docker.io
              image_name: library/nginx
              image_tag: latest
      400:
        description: Missing fields or validation error
        examples:
          application/json:
            error: "Missing required field: PodName"
      404:
        description: Server or Pod not found
        examples:
          application/json:
            error: "Pod 'testpod123' not found on server 'server-01'."
      500:
        description: Server error
        examples:
          application/json:
            error: "Server error"
            details: "<details>"
    """
    try:
        req = request.json
        if req is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        required_fields = ["ServerName", "PodName"]
        missing = [f for f in required_fields if f not in req or not req[f]]
        if missing:
            return jsonify({'error': f"Missing required field: {', '.join(missing)}"}), 400

        server_id = req['ServerName']
        pod_name = req['PodName']
        data = load_data()
        
        # Find server and pod
        server = next((s for s in data if s['id'] == server_id), None)
        if not server:
            return jsonify({'error': f"Server '{server_id}' not found."}), 404
        
        pod = next((p for p in server['pods'] if p['pod_id'] == pod_name), None)
        if not pod:
            return jsonify({'error': f"Pod '{pod_name}' not found on server '{server_id}'."}), 404

        # Handle resource updates
        if 'Resources' in req and isinstance(req['Resources'], dict):
            old_resources = pod.get('requested', {})
            new_resources = req['Resources']
            
            # Return old resources to available pool
            for key in ['gpus', 'ram_gb', 'storage_gb']:
                server['resources']['available'][key] += old_resources.get(key, 0)
            
            # Validate new resource request
            ok, err = validate_resource_request(server, new_resources)
            if not ok:
                # Restore old resources if validation fails
                for key in ['gpus', 'ram_gb', 'storage_gb']:
                    server['resources']['available'][key] -= old_resources.get(key, 0)
                return jsonify({'error': err}), 400
            
            # Allocate new resources
            for key in ['gpus', 'ram_gb', 'storage_gb']:
                server['resources']['available'][key] -= new_resources.get(key, 0)
            
            # Update pod's requested resources
            pod['requested'] = new_resources

        # Update other fields
        if 'Owner' in req:
            pod['owner'] = req['Owner']
        
        # Image URL handling removed - using default nginx:latest

        # Update timestamp using utility function
        updated_pod = update_pod_object({
            'PodName': pod_name,
            'Resources': pod['requested'],
            'image_url': pod['image_url'],
            'Owner': pod['owner']
        }, server_id)
        pod['timestamp'] = updated_pod['timestamp']

        save_data(data)
        return jsonify({'message': 'Pod updated', 'pod': pod}), 200

    except Exception as e:
        return jsonify({'error': 'Server error', 'details': str(e)}), 500

@app.route('/consistency-check', methods=['GET'])
def consistency_check_mdem():
    """
    Check for data consistency
    ---
    tags:
      - Utility
    responses:
      200:
        description: Consistency check result
        examples:
          application/json:
            status: ok
            message: all data seems consistent
      400:
        description: Data inconsistency error
        examples:
          application/json:
            status: error
            message: data inconsistency error
            details:
              - "Pod 'pod-101' not found on server 'server-01'"
      500:
        description: Server error
        examples:
          application/json:
            error: "Server error"
            details: "<details>"
    """
    try:
        # Use appropriate provider based on environment
        if Config.ENVIRONMENT.value == Environment.LOCAL_MOCK_DB.value:
            # Use mock data for demo mode
            servers = mock_data_provider.get_servers_with_pods_mdem()
        elif Config.ENVIRONMENT.value == Environment.DEVELOPMENT.value:
            # Use local Kubernetes provider
            servers = local_kubernetes_provider.get_servers_with_pods()
        elif Config.ENVIRONMENT.value == Environment.PRODUCTION.value:
            # Use cloud Kubernetes provider
            servers = cloud_kubernetes_provider.get_servers_with_pods()
        else:
            # Fallback to mock data
            servers = mock_data_provider.get_servers_with_pods_mdem()
        
        errors = []
        for server in servers:
            total = server['resources']['total']
            available = server['resources']['available']
            # Check available <= total for each resource
            for key in total:
                if available.get(key, 0) > total.get(key, 0):
                    errors.append(f"Server {server['name']}: available {key} > total {key}")
            # Check sum of pod resources <= total for each resource
            pod_sums = {}
            for pod in server.get('pods', []):
                requested = pod.get('requested') if isinstance(pod, dict) else None
                if isinstance(requested, dict):
                    for k, v in requested.items():
                        pod_sums[k] = pod_sums.get(k, 0) + v
            for key in total:
                if pod_sums.get(key, 0) > total.get(key, 0):
                    errors.append(f"Server {server['name']}: sum of pod {key} > total {key}")
        if errors:
            return jsonify({"status": "error", "message": "data inconsistency error", "details": errors}), 400
        else:
            return jsonify({"status": "ok", "message": "all data seems consistent"}), 200
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint
    ---
    tags:
      - Health
    responses:
      200:
        description: Health check result
        examples:
          application/json:
            status: "healthy"
            timestamp: "2024-01-01T00:00:00Z"
      500:
        description: Health check failed
        examples:
          application/json:
            status: "unhealthy"
            error: "Health check failed"
    """
    try:
        # Force a health check
        health_data = health_monitor.force_health_check()
        cluster_status = health_data['cluster_status']['status']
        
        if health_monitor.is_healthy():
            return jsonify({
                'status': 'healthy',
                'cluster_status': cluster_status,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'cluster_status': cluster_status,
                'error': 'Kubernetes cluster health check failed',
                'timestamp': datetime.now().isoformat()
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': f'Health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/health/detailed', methods=['GET'])
def detailed_health_check():
    """
    Detailed health check endpoint with all health metrics
    ---
    tags:
      - Health
    responses:
      200:
        description: Detailed health check result
        examples:
          application/json:
            cluster_status:
              status: "healthy"
              last_check: "2024-01-01T00:00:00Z"
            health_checks:
              cluster_connectivity:
                status: "pass"
                details: "Kubernetes cluster is healthy"
    """
    try:
        health_data = health_monitor.get_detailed_health()
        return jsonify(health_data), 200
    except Exception as e:
        return jsonify({
            'error': f'Detailed health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/cluster-status', methods=['GET'])
def cluster_status():
    """
    Get current cluster status
    ---
    tags:
      - Health
    responses:
      200:
        description: Cluster status information
        examples:
          application/json:
            status: "healthy"
            last_check: "2024-01-01T00:00:00Z"
            monitoring_active: true
    """
    try:
        status_data = health_monitor.get_cluster_status()
        return jsonify(status_data), 200
    except Exception as e:
        return jsonify({
            'error': f'Failed to get cluster status: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/mode', methods=['GET', 'POST'])
def mode_management_mdem():
    """
    Get or set current mode
    ---
    tags:
      - Configuration
    parameters:
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            mode:
              type: string
              enum: [demo, local-k8s, cloud-k8s, dev]
    responses:
      200:
        description: Current mode information
        examples:
          application/json:
            current_mode: demo
            backend_env: local-mock-db
            description: Demo mode with mock data
      500:
        description: Server error
    """
    try:
        if request.method == 'POST':
            data = request.json or {}
            new_mode = data.get('mode', 'demo')
            
            # Map frontend modes to backend environments
            mode_mapping = {
                'demo': 'local-mock-db',
                'local-k8s': 'development', 
                'cloud-k8s': 'production'
            }
            
            # Set environment variable
            os.environ['ENVIRONMENT'] = mode_mapping.get(new_mode, 'local-mock-db')
            
            # Reload configuration to pick up the new environment
            import importlib
            import config
            importlib.reload(config)
            # Re-import Config after reload
            from config import Config
            
            return jsonify({
                'current_mode': new_mode,
                'backend_env': mode_mapping.get(new_mode, 'local-mock-db'),
                'message': f'Mode changed to {new_mode}'
            }), 200
        else:
            # GET request - return current mode info
            # Re-import Config to ensure we have the latest
            import importlib
            import config
            importlib.reload(config)
            from config import Config
            
            current_env = Config.ENVIRONMENT.value
            mode_mapping_reverse = {
                'local-mock-db': 'demo',
                'development': 'local-k8s',
                'production': 'cloud-k8s'
            }
            
            return jsonify({
                'current_mode': mode_mapping_reverse.get(current_env, 'demo'),
                'backend_env': current_env,
                'description': f'Current backend environment: {current_env}'
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


if __name__ == '__main__':
    # Start health monitoring
    health_monitor.start_monitoring()
    
    # Get port from configuration
    port = Ports.get_backend_port()
    
    # Start Flask app
    app.run(debug=True, port=port)
