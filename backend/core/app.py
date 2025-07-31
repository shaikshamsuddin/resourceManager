"""
Resource Manager Backend API
This module contains the Flask application and API endpoints for managing Kubernetes resources.
"""

import warnings
# Suppress SSL/TLS warnings for development environments
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', category=Warning, module='urllib3')

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
from flasgger import Swagger

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")
except Exception as e:
    print(f"⚠️  Failed to load .env file: {e}")

# Import configuration and utility functions
from config.config import Config
from config.utils import (
    get_available_resources,
    validate_resource_request,
    create_pod_k8s,
    delete_pod_k8s
)

from core.server_manager import server_manager
from core.health_monitor import health_monitor
from config.constants import Ports, PodStatus, ConfigKeys, APP_CONFIG
from core.k8s_client import k8s_client

# Import server configuration API
from core.server_configuration_api import server_config_bp

# Import background refresh service
from core.background_refresh_service import background_refresh_service

# Import enhanced pod manager
from core.enhanced_pod_manager import enhanced_pod_manager

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

# Register server configuration blueprint
app.register_blueprint(server_config_bp)



# Add at module level
BACKEND_VERSION = "1.0.0"
BACKEND_START_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")




# --- API Endpoints ---
@app.route('/')
def index():
    # Get application configuration
    display_name = APP_CONFIG["display_name"]
    description = APP_CONFIG["description"]
    capabilities = APP_CONFIG["capabilities"]
    
    # Try to get a quick cluster/server summary
    try:
        servers = server_manager.get_all_servers_static()
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
            <b>Application:</b> <span class="badge">{display_name}</span>
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
        
        <div class="section-title">Current Server Status</div>
        <div class="info-row">
            <b>Azure VM Connection:</b> 
            <span class="badge" style="background: #dcfce7; color: #166534;">✅ Connected</span>
            <br><small>Server: kubernetes-4-246-178-26 (4.246.178.26:16443)</small>
        </div>
        <div class="info-row">
            <b>Background Services:</b>
            <span class="badge" style="background: #dcfce7; color: #166534;">✅ Active</span>
            <br><small>Live data refresh, UI polling, health monitoring</small>
        </div>
        <div class="section-title">API Endpoints</div>
    <ul>
      <li><b>GET /servers</b> - List all servers and pods</li>
      <li><b>POST /create</b> - Create a new pod (JSON body required)</li>
      <li><b>POST /delete</b> - Delete a pod (JSON body required)</li>
      <li><b>GET /resource-validation</b> - Validate Azure VM resource integrity</li>
      <li><b>GET /health</b> - Basic health check</li>
      <li><b>GET /health/detailed</b> - Detailed health check</li>
    </ul>
    
    <div class="section-title">Server Configuration API</div>
    <ul>
      <li><b>GET /api/server-config/health</b> - Server config health check</li>
      <li><b>POST /api/server-config/reconnect</b> - Reconnect all servers</li>
      <li><b>GET /api/server-config/config</b> - Get server configuration</li>
      <li><b>GET /api/server-config/config/refresh</b> - Get refresh configuration</li>
      <li><b>POST /api/server-config/config/refresh</b> - Update refresh configuration</li>
      <li><b>POST /api/server-config/configure</b> - Configure a new server</li>
      <li><b>GET /api/server-config/servers</b> - Get all configured servers</li>
      <li><b>POST /api/server-config/servers/&lt;server_id&gt;/kubeconfig</b> - Update server kubeconfig</li>
      <li><b>POST /api/server-config/servers/&lt;server_id&gt;/test-connection</b> - Test server connection</li>
      <li><b>DELETE /api/server-config/deconfigure/&lt;server_id&gt;</b> - Deconfigure a server</li>
      <li><b>POST /api/server-config/servers/&lt;server_id&gt;/refresh</b> - Refresh specific server data</li>
      <li><b>POST /api/server-config/servers/refresh-all</b> - Refresh all servers data</li>
      <li><b>GET /api/server-config/background-refresh/status</b> - Get background refresh status</li>
      <li><b>POST /api/server-config/background-refresh/start</b> - Start background refresh service</li>
      <li><b>POST /api/server-config/background-refresh/stop</b> - Stop background refresh service</li>
    </ul>
        <div class="section-title">Recent Features</div>
        <ul>
            <li><b>✅ Type Safety:</b> Implemented proper TypedDict definitions for all data structures</li>
            <li><b>✅ Server Configuration:</b> Complete API for server setup and management</li>
            <li><b>✅ Background Services:</b> Automatic live data refresh and health monitoring</li>
            <li><b>✅ Azure VM Integration:</b> Full Kubernetes cluster management</li>
            <li><b>✅ Pod Management:</b> Create, delete pods with proper validation</li>
            <li><b>✅ Real-time Updates:</b> Live data fetching with configurable intervals</li>
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
def get_servers():
    """
    List all servers and pods from all configured clusters
    ---
    tags:
      - Servers
    parameters:
      - in: query
        name: server_id
        type: string
        required: false
        description: Specific server ID to get data for
    responses:
      200:
        description: List of all servers and their pods
        examples:
          application/json:
            - server_id: azure-vm-01
              server_name: Azure VM MicroK8s
              server_type: kubernetes
              status: Online
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
        # Check if specific server is requested
        server_id = request.args.get('server_id')
        
        if server_id:
            # Get specific server data
            server_data = server_manager.get_server_with_pods(server_id)
            if server_data:
                return jsonify([server_data]), 200
            else:
                return jsonify({'error': f'Server {server_id} not found'}), 404
        else:
            # Get all servers data from master.json only (fast, no live sync)
            servers = server_manager.get_all_servers_static()
            return jsonify(servers), 200
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/create', methods=['POST'])
def create_pod():
    """
    Create a new pod on a specific server with enhanced status tracking
    
    Enhanced workflow:
    1. Add pod to master.json with "pending" status
    2. Deploy to Kubernetes server in background
    3. Update status to "online" or "failed"
    
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
            server_id:
              type: string
              description: Server ID to create pod on
            namespace:
              type: string
              description: Namespace to create pod in (optional, defaults to 'default')
            replicas:
              type: integer
              description: Number of pod replicas to create (optional, defaults to 1)
            Resources:
              type: object
              description: Resource requirements (RAM, CPU, GPU, Storage)
            image_url:
              type: string
              description: Container image URL (optional, defaults to 'nginx:latest')
    responses:
      200:
        description: Pod deployment started
      400:
        description: Validation error
      404:
        description: Server not found
      500:
        description: Server error
    """
    try:
        req = request.json
        if req is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # Get server_id from request
        server_id = req.get('server_id')
        if not server_id:
            return jsonify({'error': 'server_id is required'}), 400
        
        # Validate replica count
        replicas = req.get('replicas', 1)
        if not isinstance(replicas, int) or replicas < 1 or replicas > 100:
            return jsonify({'error': 'Replica count must be an integer between 1 and 100'}), 400
        
        # Validate resources
        resources = req.get('Resources', {})
        if not isinstance(resources, dict):
            return jsonify({'error': 'Resources must be a dictionary/object'}), 400
        
        # Validate server exists
        servers = server_manager.get_all_servers_static()
        server_data = next((s for s in servers if s.get('server_id') == server_id), None)
        
        if not server_data:
            return jsonify({'error': f"Server '{server_id}' not found"}), 404
        
        # Validate resources against server capacity
        ok, err = validate_resource_request(server_data, resources)
        if not ok:
            return jsonify({'error': err}), 400
        
        # Use enhanced pod manager for deployment
        print(f"🚀 Starting enhanced pod deployment on server {server_id}")
        result = enhanced_pod_manager.create_pod_with_status_tracking(server_id, req)
        
        if 'error' in result:
            print(f"❌ Enhanced pod deployment failed: {result['error']}")
            return jsonify(result), 500
        else:
            print(f"✅ Enhanced pod deployment started: {result}")
            return jsonify({
                'type': 'success', 
                'message': 'Pod deployment started successfully',
                'deployment_id': result.get('deployment_id'),
                'pod_id': result.get('pod_id'),
                'status': result.get('status')
            }), 200
            
    except Exception as e:
        print(f"❌ Enhanced pod creation error: {e}")
        return jsonify({'error': 'Server error', 'details': str(e)}), 500


@app.route('/deployment-status/<server_id>/<pod_id>', methods=['GET'])
def get_deployment_status(server_id: str, pod_id: str):
    """
    Get deployment status for a specific pod
    
    ---
    tags:
      - Pods
    parameters:
      - in: path
        name: server_id
        type: string
        required: true
        description: Server ID
      - in: path
        name: pod_id
        type: string
        required: true
        description: Pod ID
    responses:
      200:
        description: Deployment status
      404:
        description: Pod not found
    """
    try:
        result = enhanced_pod_manager.get_deployment_status(server_id, pod_id)
        
        if 'error' in result:
            return jsonify(result), 404
        else:
            return jsonify(result), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get deployment status: {e}'}), 500


@app.route('/ensure-servers-connected', methods=['POST'])
def ensure_servers_connected():
    """
    Ensure all servers in master.json are properly connected
    
    ---
    tags:
      - Servers
    responses:
      200:
        description: Server connection status
    """
    try:
        result = server_manager.ensure_all_servers_connected()
        return jsonify({
            'type': 'success',
            'message': f'Server connection check completed',
            'summary': result
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to ensure servers connected: {e}'}), 500


@app.route('/server-connection-status', methods=['GET'])
def get_server_connection_status():
    """
    Get connection status for all servers
    
    ---
    tags:
      - Servers
    responses:
      200:
        description: Server connection status
    """
    try:
        status = server_manager.get_server_connection_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get server connection status: {e}'}), 500


@app.route('/delete', methods=['POST'])
def delete_pod():
    """
    Delete a pod from a specific server
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
            server_id:
              type: string
              description: Server ID to delete pod from
            PodName:
              type: string
    responses:
      200:
        description: Pod deleted successfully
      400:
        description: Validation error
      404:
        description: Pod not found
      500:
        description: Server error
    """
    try:
        req = request.json
        if req is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # Get server_id and pod_name from request
        server_id = req.get('server_id')
        pod_name = req.get('PodName')
        
        if not server_id:
            return jsonify({'error': 'server_id is required'}), 400
        
        if not pod_name:
            return jsonify({'error': 'PodName is required'}), 400
        
        # Delete pod using server manager
        result = server_manager.delete_pod(server_id, pod_name)
        
        if 'error' in result:
            if 'not found' in result['error'].lower():
                return jsonify(result), 404
            else:
                return jsonify(result), 500
        else:
            return jsonify({'type': 'success', 'message': 'Pod deleted'}), 200
            
    except Exception as e:
        return jsonify({'error': 'Server error', 'details': str(e)}), 500



@app.route('/resource-validation', methods=['GET'])
def resource_validation():
    """
    Validate Azure VM resource allocation integrity
    ---
    tags:
      - Utility
    responses:
      200:
        description: Resource validation result
        examples:
          application/json:
            status: ok
            message: Azure VM resource allocation is valid
      400:
        description: Resource validation error
        examples:
          application/json:
            status: error
            message: Resource validation failed
            details:
              - "Azure VM: Available CPUs exceeds total"
              - "Azure VM: Pods requesting more RAM than available"
      500:
        description: Server error
        examples:
          application/json:
            error: "Server error"
            details: "<details>"
    """
    try:
        # Use server manager for all environments (static data only)
        servers = server_manager.get_all_servers_static()
        
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
                'message': 'Resource validation failed. See details below.',
                'details': errors
            }), 400
        else:
            return jsonify({'type': 'success', 'message': 'Azure VM resource allocation is valid'}), 200
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


@app.route('/delete-namespace', methods=['POST'])
def delete_namespace():
    """
    Delete a Kubernetes namespace and all its pods/resources
    ---
    tags:
      - Namespace
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            namespace:
              type: string
              description: Namespace to delete
            server_id:
              type: string
              description: Server ID to delete namespace from
    responses:
      200:
        description: Namespace deleted
        examples:
          application/json:
            type: success
            code: 200
            message: Namespace deleted successfully
      400:
        description: Bad request
        examples:
          application/json:
            type: error
            code: 400
            message: Namespace not provided
      500:
        description: Server error
        examples:
          application/json:
            type: error
            code: 500
            message: Failed to delete namespace
    """
    data = request.get_json(force=True)
    namespace = data.get('namespace')
    server_id = data.get('server_id', 'kubernetes-4-246-178-26')  # Default to our Azure VM
    
    if not namespace:
        return jsonify({'type': 'error', 'code': 400, 'message': 'Namespace not provided'}), 400
    
    try:
        # Use server manager to delete namespace
        provider = server_manager.get_server_provider(server_id)
        if not provider:
            return jsonify({'type': 'error', 'code': 404, 'message': f'Server {server_id} not found'}), 404
        
        # Ensure provider is initialized
        if not provider.core_v1:
            print(f"Provider for server {server_id} not initialized, initializing now...")
            provider._ensure_initialized()
        
        if not provider.core_v1:
            return jsonify({'type': 'error', 'code': 500, 'message': f'Failed to initialize provider for server {server_id}'}), 500
        
        # Delete namespace using the provider
        provider.core_v1.delete_namespace(name=namespace)
        return jsonify({'type': 'success', 'code': 200, 'message': f'Namespace "{namespace}" deleted successfully'}), 200
    except Exception as e:
        error_message = str(e)
        
        # Provide more user-friendly error messages
        if "not found" in error_message.lower():
            return jsonify({
                'type': 'error', 
                'code': 404, 
                'message': f'Namespace "{namespace}" not found on server {server_id}',
                'details': error_message
            }), 404
        elif "forbidden" in error_message.lower() or "unauthorized" in error_message.lower():
            return jsonify({
                'type': 'error', 
                'code': 403, 
                'message': f'Permission denied: Cannot delete namespace "{namespace}"',
                'details': error_message
            }), 403
        elif "timeout" in error_message.lower():
            return jsonify({
                'type': 'error', 
                'code': 408, 
                'message': f'Request timeout: Unable to delete namespace "{namespace}"',
                'details': error_message
            }), 408
        else:
            return jsonify({
                'type': 'error', 
                'code': 500, 
                'message': f'Failed to delete namespace "{namespace}": {error_message}',
                'details': error_message
            }), 500















if __name__ == '__main__':
    # Start health monitoring
    health_monitor.start_monitoring()
    
    # Ensure all servers are connected
    print("🔧 Ensuring all servers are connected on startup...")
    server_manager.ensure_all_servers_connected()
    
    # Start background refresh service
    background_refresh_service.start()
    
    # Get port from configuration
    port = Ports.get_backend_port()
    
    # Start Flask app
    app.run(debug=True, port=port)
