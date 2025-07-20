"""
Resource Manager Backend API
This module contains the Flask application and API endpoints for managing Kubernetes resources.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from flasgger import Swagger

# Import utility functions from utils module
from utils import (
    get_available_resources,
    validate_resource_request,
    create_k8s_resources_simple,
    delete_k8s_resources_simple,
    create_pod_object,
    update_pod_object
)

app = Flask(__name__)
CORS(app)
swagger = Swagger(app)

MOCK_DB_JSON = os.path.join(os.path.dirname(__file__), 'mock_db.json')


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
def get_servers():
    """
    List all servers and pods
    ---
    tags:
      - Servers
    responses:
      200:
        description: List of all servers and their pods
        examples:
          application/json:
            - id: server-01
              name: gpu-node-h100-a
              resources:
                total: { gpus: 8, ram_gb: 512, storage_gb: 2048 }
                available: { gpus: 2, ram_gb: 128, storage_gb: 548 }
              pods: []
      500:
        description: Server error
        examples:
          application/json:
            error: "Server error"
            details: "<details>"
    """
    try:
        data = load_data()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/create', methods=['POST'])
def create_pod():
    try:
        req = request.json
        if req is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        required_fields = ["ServerName", "PodName", "Resources", "image_url"]
        errors = []
        missing = [f for f in required_fields if f not in req or not req[f]]
        if missing:
            errors.append(f"Missing required field: {', '.join(missing)}")
        pod_name = req.get('PodName', '')
        image_url = req.get('image_url', '')
        if not isinstance(pod_name, str) or not pod_name:
            errors.append("Pod name is required.")
        else:
            if not pod_name.islower():
                errors.append("Pod name must be lowercase.")
            if "_" in pod_name:
                errors.append("Pod name must not contain underscores.")
        if not (isinstance(image_url, str) and image_url.strip()):
            errors.append("Image URL must be a non-empty string.")
        
        server_id = req.get('ServerName')
        resources = req.get('Resources', {})
        owner = req.get('Owner', 'unknown')
        
        data = load_data()
        server = next((s for s in data if s['id'] == server_id), None)
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
            
        # Initialize server resources structure if needed
        if not isinstance(server.get('resources'), dict):
            server['resources'] = {'total': {}, 'available': {}}
        if not isinstance(server['resources'].get('available'), dict):
            server['resources']['available'] = {}
            
        # Update available resources
        for key in ['gpus', 'ram_gb', 'storage_gb']:
            current_available = server['resources']['available'].get(key, 0)
            current_total = server['resources'].get('total', {}).get(key, 0)
            if key not in server['resources']['available']:
                server['resources']['available'][key] = current_total
            server['resources']['available'][key] = current_available - resources.get(key, 0)
            
        pod = create_pod_object({
            'PodName': pod_name,
            'Resources': resources,
            'image_url': image_url,
            'Owner': owner
        }, server_id)
        
        # Initialize pods list if needed
        if not isinstance(server.get('pods'), list):
            server['pods'] = []
        server['pods'].append(pod)
        save_data(data)
        
        try:
            create_k8s_resources_simple(pod)
        except Exception as e:
            return jsonify({'error': f'Kubernetes error: {str(e)}'}), 500
            
        return jsonify({'message': 'Pod created', 'pod': pod}), 200
    except Exception as e:
        return jsonify({'error': 'Server error', 'details': str(e)}), 500

@app.route('/delete', methods=['POST'])
def delete_pod():
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
        data = load_data()
        found = False
        for server in data:
            pod = next((p for p in server['pods'] if p['pod_id'] == pod_name), None)
            if pod:
                for key in ['gpus', 'ram_gb', 'storage_gb']:
                    server['resources']['available'][key] += pod['requested'].get(key, 0)
                server['pods'].remove(pod)
                found = True
                break
        if not found:
            return jsonify({'error': f"Pod '{pod_name}' not found on any server."}), 404
        
        # Delete from Kubernetes if pod was found
        try:
            delete_k8s_resources_simple({'pod_id': pod_name})
        except Exception as e:
            return jsonify({'error': f'Kubernetes deletion error: {str(e)}'}), 500
        
        save_data(data)
        return jsonify({'message': 'Pod deleted'}), 200
    except Exception as e:
        return jsonify({'error': 'Server error', 'details': str(e)}), 500

@app.route('/update', methods=['POST'])
def update_pod():
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
        
        if 'image_url' in req:
            pod['image_url'] = req['image_url']
            # Parse and update image details
            if req['image_url'].startswith('https://') and ':' in req['image_url']:
                try:
                    image_url_no_proto = req['image_url'][len('https://'):]
                    registry_and_image, image_tag = image_url_no_proto.rsplit(':', 1)
                    registry_url, image_name = registry_and_image.split('/', 1)
                    pod['registery_url'] = registry_url
                    pod['image_name'] = image_name
                    pod['image_tag'] = image_tag
                except Exception as e:
                    return jsonify({'error': f'Failed to parse image_url: {str(e)}'}), 400

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
def consistency_check():
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
        with open(MOCK_DB_JSON) as f:
            servers = json.load(f)
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

if __name__ == '__main__':
    app.run(debug=True)
