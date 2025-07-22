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
    create_pod_k8s,
    delete_pod_k8s,
    create_pod_mdem as create_pod_mdem_util,  # Use alias to avoid conflict with endpoint
    update_pod_mdem
)
from providers.mock_data_provider import mock_data_provider
from providers.kubernetes_provider import local_kubernetes_provider
from providers.cloud_kubernetes_provider import cloud_kubernetes_provider
from health_monitor import health_monitor
from constants import Ports, PodStatus, Environment, Mode, ModeConfig, ConfigKeys

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
LAST_MODE_JSON = os.path.join(os.path.dirname(__file__), 'data', 'last_mode.json')

# Add at module level
BACKEND_VERSION = "1.0.0"
BACKEND_START_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_data():
    """Load data from mock database JSON file."""
    with open(MOCK_DB_JSON, 'r') as f:
        return json.load(f)


def save_data(data):
    """Save data to mock database JSON file."""
    with open(MOCK_DB_JSON, 'w') as f:
        json.dump(data, f, indent=2)


def load_last_mode():
    """Load last selected mode from JSON file."""
    try:
        with open(LAST_MODE_JSON, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_mode": None, "last_updated": None}


def save_last_mode(mode):
    """Save last selected mode to JSON file."""
    data = {
        "last_mode": mode,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(LAST_MODE_JSON, 'w') as f:
        json.dump(data, f, indent=2)

# --- API Endpoints ---
@app.route('/')
def index():
    # Get current mode and environment
    from constants import ModeConfig
    env = Config.get_environment_value()
    
    if env is None:
        # No environment set - show no mode selected
        mode = None
        display_name = "No Mode Selected"
        description = "Please select a mode to continue"
        capabilities = {}
    else:
        mode = ModeConfig.get_mode_for_environment(env)
        display_name = ModeConfig.get_display_name(mode)
        description = ModeConfig.get_description(mode)
        capabilities = ModeConfig.get_capabilities(mode)
    
    # Try to get a quick cluster/server summary
    try:
        if env == 'local-mock-db':
            servers = mock_data_provider.get_servers_with_pods_mdem()
        elif env == 'development':
            servers = local_kubernetes_provider.get_servers_with_pods()
        elif env == 'production':
            servers = cloud_kubernetes_provider.get_servers_with_pods()
        else:
            servers = []
        total_servers = len(servers)
        total_pods = sum(len(s.get('pods', [])) for s in servers)
    except Exception:
        total_servers = 'N/A'
        total_pods = 'N/A'
    
    # Capabilities as badges
    cap_html = ''.join([
        f'<span style="display:inline-block;background:#eef;border-radius:8px;padding:2px 8px;margin:2px 4px;font-size:0.95em;">{k.replace('_',' ').title()}: <b>{"Yes" if v else "No"}</b></span>'
        for k,v in capabilities.items()
    ])
    return f'''
    <html>
    <head>
        <title>Resource Manager Backend</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; color: #222; margin: 0; padding: 0; }}
            .container {{ max-width: 800px; margin: 32px auto; background: #fff; border-radius: 16px; box-shadow: 0 4px 24px #0001; padding: 32px; }}
            h1 {{ font-size: 2.2rem; margin-bottom: 0.5em; }}
            .info-row {{ margin-bottom: 1.2em; }}
            .badge {{ display: inline-block; background: #e0e7ff; color: #3730a3; border-radius: 8px; padding: 2px 10px; margin: 0 4px; font-size: 0.95em; }}
            .section-title {{ font-size: 1.2rem; margin-top: 2em; margin-bottom: 0.5em; color: #2563eb; }}
            ul {{ margin-top: 0.2em; }}
            .capabilities {{ margin: 0.5em 0 1em 0; }}
            .summary-table td {{ padding: 4px 12px; }}
            a {{ color: #2563eb; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
    <div class="container">
        <h1>🎉 Resource Manager Backend is Running! 🎉</h1>
        <div class="info-row">
            <b>Backend Version:</b> <span class="badge">{BACKEND_VERSION}</span>
            <b>Started:</b> <span class="badge">{BACKEND_START_TIME}</span>
        </div>
        <div class="info-row">
            <b>Current Mode:</b> <span class="badge">{display_name}</span>
            <b>Environment:</b> <span class="badge">{env}</span>
        </div>
        <div class="info-row">
            <b>Description:</b> {description}
        </div>
        <div class="capabilities">
            <b>Capabilities:</b> {cap_html}
        </div>
        <div class="info-row">
            <b>Cluster/Server Summary:</b>
            <table class="summary-table">
                <tr><td>Total Servers:</td><td><b>{total_servers}</b></td></tr>
                <tr><td>Total Pods:</td><td><b>{total_pods}</b></td></tr>
            </table>
        </div>
        <div class="section-title">API Endpoints</div>
        <ul>
            <li><b>GET /servers</b> - List all servers and pods</li>
            <li><b>POST /create</b> - Create a new pod (JSON body required)</li>
            <li><b>POST /delete</b> - Delete a pod (JSON body required)</li>
            <li><b>POST /update</b> - Update a pod (JSON body required)</li>
            <li><b>GET /consistency-check</b> - Check for data consistency</li>
            <li><b>GET /mode</b> - Get or set backend mode</li>
            <li><b>GET /health</b> - Basic health check</li>
            <li><b>GET /health/detailed</b> - Detailed health check</li>
            <li><b>GET /cluster-status</b> - Cluster status</li>
        </ul>
        <div class="section-title">API Testing &amp; Documentation</div>
        <p>Access <a href="/apidocs/" target="_blank">Swagger UI</a> to view, send, and test API calls interactively.</p>
        <div class="section-title">Frontend UI</div>
        <p>Access the <a href="http://localhost:4200/" target="_blank">Resource Manager Frontend</a> for a modern, user-friendly web interface.</p>
    </div>
    </body>
    </html>
    '''

@app.route('/servers', methods=['GET'])
def get_servers_mdem():
    """
    List all servers and pods (real Kubernetes data or mock data, depending on mode or query param)
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
        # Accept ?mode=demo|local-k8s|cloud-k8s
        mode_param = request.args.get('mode')
        if mode_param:
            mode = mode_param
        else:
            # Use current mode from config
            env = Config.get_environment_value()
            if env is None:
                # No environment set - return empty response
                return jsonify([]), 200
            mode = ModeConfig.get_mode_for_environment(env)

        # Validate mode
        valid_modes = [Mode.DEMO.value, Mode.LOCAL_KUBERNETES.value, Mode.CLOUD_KUBERNETES.value]
        if mode not in valid_modes:
            return jsonify({'type': 'error', 'message': f'Invalid mode: {mode}'}), 400

        if mode == Mode.DEMO.value:
            servers = mock_data_provider.get_servers_with_pods_mdem()
        elif mode == Mode.LOCAL_KUBERNETES.value:
            servers = local_kubernetes_provider.get_servers_with_pods()
        elif mode == Mode.CLOUD_KUBERNETES.value:
            servers = cloud_kubernetes_provider.get_servers_with_pods()
        else:
            servers = []
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
        if Config.get_environment_value() == Environment.LOCAL_MOCK_DB.value:
            servers = mock_data_provider.get_servers_with_pods_mdem()
        elif Config.get_environment_value() == Environment.DEVELOPMENT.value:
            servers = local_kubernetes_provider.get_servers_with_pods()
        elif Config.get_environment_value() == Environment.PRODUCTION.value:
            servers = cloud_kubernetes_provider.get_servers_with_pods()
        else:
            servers = mock_data_provider.get_servers_with_pods_mdem()
        
        server = next((s for s in servers if s['id'] == server_id), None)
        if not server:
            return jsonify({'error': f"Server '{server_id}' not found."}), 404

        if not isinstance(resources, dict):
            return jsonify({'error': 'Resources must be a dictionary/object'}), 400

        ok, err = validate_resource_request(server, resources)
        if not ok:
            errors.append(err)
            return jsonify({'type': 'error', 'message': "\n".join(errors)}), 400
            
        # Validate resources against real Kubernetes node
        if not isinstance(server.get('resources'), dict):
            errors.append('Server resources not available')
            return jsonify({'type': 'error', 'message': "\n".join(errors)}), 400
            
        # Check if resources are available
        available = server['resources'].get('available', {})
        for key in ['gpus', 'ram_gb', 'storage_gb']:
            if resources.get(key, 0) > available.get(key, 0):
                errors.append(f"Insufficient {key}: requested {resources.get(key, 0)}, available {available.get(key, 0)}")
                return jsonify({'type': 'error', 'message': "\n".join(errors)}), 400
        
        # Create pod object with port configuration
        pod = create_pod_mdem_util({
            'PodName': pod_name,
            'Resources': resources,
            'Owner': owner,
            'container_port': req.get('container_port', 80),
            'service_port': req.get('service_port', 80),
            'expose_service': req.get('expose_service', False)
        }, server_id)
        
        try:
            if Config.get_environment_value() == Environment.LOCAL_MOCK_DB.value:
                # Add to mock data
                if mock_data_provider.add_pod_mdem(server_id, pod):
                    return jsonify({'type': 'success', 'message': 'Pod created', 'pod': pod}), 200
                else:
                    return jsonify({'error': 'Failed to add pod to mock data'}), 500
            else:
                # Create real Kubernetes resources
                create_pod_k8s(pod)
                return jsonify({'type': 'success', 'message': 'Pod created', 'pod': pod}), 200
            
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
        if Config.get_environment_value() == Environment.LOCAL_MOCK_DB.value:
            # Delete from mock data
            if mock_data_provider.remove_pod_mdem(pod_name):
                return jsonify({'type': 'success', 'message': 'Pod deleted'}), 200
            else:
                return jsonify({'error': f"Pod '{pod_name}' not found on any server."}), 404
        else:
            # Delete from real Kubernetes
            try:
                # Try to find the pod in the cluster to get its namespace
                current_env = Config.get_environment_value()
                if current_env == Environment.DEVELOPMENT.value:
                    servers = local_kubernetes_provider.get_servers_with_pods()
                elif current_env == Environment.PRODUCTION.value:
                    servers = cloud_kubernetes_provider.get_servers_with_pods()
                else:
                    servers = []
                
                # Find the pod and its namespace
                pod_found = False
                pod_namespace = 'default'  # Default namespace
                
                for server in servers:
                    for pod in server.get('pods', []):
                        if pod.get('pod_id') == pod_name:
                            pod_found = True
                            # Use the namespace from pod data if available
                            pod_namespace = pod.get('namespace', 'default')
                            break
                    if pod_found:
                        break
                
                if not pod_found:
                    return jsonify({'type': 'error', 'message': f"Pod '{pod_name}' not found in cluster."}), 404
                
                # Delete the pod with the correct namespace
                delete_pod_k8s({
                    'pod_id': pod_name,
                    'namespace': pod_namespace
                })
                return jsonify({'type': 'success', 'message': f'Pod {pod_name} deleted from namespace {pod_namespace}\n\tStatus: Success'}), 200
            except Exception as e:
                error_msg = str(e)
                if "not found" in error_msg.lower():
                    return jsonify({'type': 'error', 'message': f"Pod '{pod_name}' not found in cluster."}), 404
                elif "pending" in error_msg.lower() or "terminating" in error_msg.lower():
                    return jsonify({'type': 'error', 'message': f"Pod '{pod_name}' is in a state that prevents deletion. Please wait for it to stabilize or try again later."}), 400
                else:
                    return jsonify({'type': 'error', 'message': f'Kubernetes deletion error: {error_msg}'}), 500
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
                return jsonify({'type': 'error', 'message': err.replace(' | ', '\n')}), 400
            
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
        updated_pod = update_pod_mdem({
            'PodName': pod_name,
            'Resources': pod['requested'],
            'image_url': pod['image_url'],
            'Owner': pod['owner']
        }, server_id)
        pod['timestamp'] = updated_pod['timestamp']

        save_data(data)
        return jsonify({'type': 'success', 'message': 'Pod updated', 'pod': pod}), 200

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
        if Config.get_environment_value() == Environment.LOCAL_MOCK_DB.value:
            # Use mock data for demo mode
            servers = mock_data_provider.get_servers_with_pods_mdem()
        elif Config.get_environment_value() == Environment.DEVELOPMENT.value:
            # Use local Kubernetes provider
            servers = local_kubernetes_provider.get_servers_with_pods()
        elif Config.get_environment_value() == Environment.PRODUCTION.value:
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
            return jsonify({
                'type': 'error',
                'message': 'Data inconsistency detected. See details below.',
                'details': errors
            }), 400
        else:
            return jsonify({'type': 'success', 'message': 'all data seems consistent'}), 200
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
def mode_management():
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
              enum: [demo, local-k8s, cloud-k8s]
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
            if new_mode == 'cloud-k8s':
                return jsonify({'type': 'info', 'message': 'Mode not enabled yet.'}), 501
            
            # Use ModeConfig to map mode to environment
            environment = ModeConfig.get_environment_for_mode(new_mode)
            
            # Set environment variable
            os.environ['ENVIRONMENT'] = environment
            
            # Reload configuration to pick up the new environment
            import importlib
            import config
            importlib.reload(config)
            # Re-import Config after reload
            from config import Config
            # Environment variable is already set, Config will pick it up dynamically
            
            # Save the last selected mode
            save_last_mode(new_mode)
            
            return jsonify({
                'type': 'success',
                'current_mode': new_mode,
                'backend_env': environment,
                'display_name': ModeConfig.get_display_name(new_mode),
                'description': ModeConfig.get_description(new_mode),
                'message': f'Mode changed to {ModeConfig.get_display_name(new_mode)}'
            }), 200
        else:
            # GET request - return current mode info
            # Re-import Config to ensure we have the latest
            import importlib
            import config
            importlib.reload(config)
            from config import Config
            # Get current environment dynamically
            current_env = Config.get_environment_value()
            
            if current_env is None:
                # No environment set - return no mode selected
                return jsonify({
                    'type': 'info',
                    'current_mode': None,
                    'backend_env': None,
                    'display_name': 'No Mode Selected',
                    'description': 'Please select a mode to continue',
                    'capabilities': {}
                }), 200
            
            current_mode = ModeConfig.get_mode_for_environment(current_env)
            
            return jsonify({
                'type': 'success',
                'current_mode': current_mode,
                'backend_env': current_env,
                'display_name': ModeConfig.get_display_name(current_mode),
                'description': ModeConfig.get_description(current_mode),
                'capabilities': ModeConfig.get_capabilities(current_mode)
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/last-mode', methods=['GET'])
def get_last_mode():
    """
    Get the last selected mode from persistent storage.
    ---
    tags:
      - Mode
    responses:
      200:
        description: Last selected mode
        examples:
          application/json:
            last_mode: "demo"
            last_updated: "2025-07-21 21:30:00"
      500:
        description: Server error
    """
    try:
        last_mode_data = load_last_mode()
        return jsonify(last_mode_data), 200
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/reset-last-mode', methods=['POST'])
def reset_last_mode():
    """
    Reset the last selected mode (set to null).
    ---
    tags:
      - Mode
    responses:
      200:
        description: Last mode reset successfully
        examples:
          application/json:
            type: "success"
            message: "Last mode reset successfully"
      500:
        description: Server error
    """
    try:
        # Clear the last saved mode
        save_last_mode(None)
        
        # Also clear the environment variable to ensure no mode is active
        if 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']
        
        return jsonify({
            'type': 'success',
            'message': 'Last mode reset successfully'
        }), 200
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/reset-mode', methods=['POST'])
def reset_mode():
    """
    Reset the selected mode's data (pods/resources) to initial state.
    Query param: mode=demo or mode=local-k8s
    """
    mode = request.args.get('mode')
    if not mode:
        return jsonify({'type': 'error', 'message': 'Missing mode parameter'}), 400
    if mode == 'demo':
        # Reset mock DB: remove all pods, reset resources
        try:
            data = load_data()
            for server in data:
                server['pods'] = []
                if 'resources' in server and 'total' in server['resources']:
                    server['resources']['available'] = dict(server['resources']['total'])
            save_data(data)
            # Also reset in-memory mock data
            from providers.mock_data_provider import mock_data_provider
            mock_data_provider.reset_demo_data()
            return jsonify({'type': 'success', 'message': 'Mock Demo mode reset successfully.\n\tAll pods deleted and resources reset.'}), 200
        except Exception as e:
            return jsonify({'type': 'error', 'message': f'Error: Reset failed.\n\t{str(e)}'}), 500
    elif mode == 'local-k8s':
        # Delete all pods from local Kubernetes cluster
        try:
            servers = local_kubernetes_provider.get_servers_with_pods()
            pod_names = []
            for server in servers:
                for pod in server.get('pods', []):
                    pod_names.append((pod.get('pod_id'), pod.get('namespace', 'default')))
            errors = []
            for pod_name, namespace in pod_names:
                try:
                    delete_pod_k8s({'pod_id': pod_name, 'namespace': namespace})
                except Exception as e:
                    errors.append(f"Pod {pod_name}: {str(e)}")
            if errors:
                details = "\n".join(f"\t{err}" for err in errors)
                return jsonify({'type': 'error', 'message': f'Error: Local Kubernetes reset completed with errors.\n{details}'}), 207
            else:
                return jsonify({'type': 'success', 'message': 'Local Kubernetes mode reset successfully.\n\tAll pods deleted.'}), 200
        except Exception as e:
            return jsonify({'type': 'error', 'message': f'Error: Failed to reset local Kubernetes mode.\n\t{str(e)}'}), 500
    elif mode == 'cloud-k8s':
        return jsonify({'type': 'error', 'message': 'Reset not allowed. Mode not enabled yet.'}), 501
    else:
        return jsonify({'type': 'error', 'message': 'Invalid mode parameter. Use "demo" or "local-k8s".'}), 400


if __name__ == '__main__':
    # Start health monitoring
    health_monitor.start_monitoring()
    
    # Get port from configuration
    port = Ports.get_backend_port()
    
    # Start Flask app
    app.run(debug=True, port=port)
