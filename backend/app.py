from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
from kubernetes import client, config as k8s_config
import tempfile
import paramiko
import yaml
import uuid

app = Flask(__name__)
CORS(app)

MASTER_JSON = os.path.join(os.path.dirname(__file__), 'master.json')

# --- Utility Functions ---
def load_data():
    with open(MASTER_JSON, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(MASTER_JSON, 'w') as f:
        json.dump(data, f, indent=2)

def get_available_resources(server):
    total = server['resources']['total']
    available = server['resources']['available']
    return {
        'gpus': available['gpus'],
        'ram_gb': available['ram_gb'],
        'storage_gb': available['storage_gb']
    }

def validate_resource_request(server, requested):
    available = get_available_resources(server)
    for key in ['gpus', 'ram_gb', 'storage_gb']:
        if requested.get(key, 0) > available.get(key, 0):
            return False, f"Not enough {key} available. Requested: {requested.get(key, 0)}, Available: {available.get(key, 0)}"
    return True, None

def fetch_kubeconfig(machine_ip, username, password):
    # SSH to VM and fetch kubeconfig (as in reference)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=machine_ip, username=username, password=password, timeout=60)
    stdin, stdout, _ = ssh.exec_command("sudo microk8s config")
    config_data = stdout.read().decode()
    ssh.close()
    config_dict = yaml.safe_load(config_data)
    public_ip = machine_ip
    for cluster in config_dict.get("clusters", []):
        server_url = cluster["cluster"]["server"]
        cluster["cluster"]["server"] = server_url.replace("127.0.0.1", public_ip)
        cluster["cluster"]["insecure-skip-tls-verify"] = True
        cluster["cluster"].pop("certificate-authority-data", None)
    config_data_modified = yaml.dump(config_dict)
    kubeconfig_path = os.path.join(tempfile.gettempdir(), f"kubeconfig_{uuid.uuid4()}.yaml")
    with open(kubeconfig_path, "w") as f:
        f.write(config_data_modified)
    return kubeconfig_path

def create_k8s_resources(kubeconfig_path, pod_data):
    k8s_config.load_kube_config(config_file=kubeconfig_path)
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    namespace = pod_data['pod_id']
    image_url = pod_data['image_url']
    resources = pod_data['requested']
    # 1. Create Namespace
    ns_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
    try:
        core_v1.create_namespace(ns_body)
    except client.exceptions.ApiException as e:
        if e.status != 409:
            raise
    # 2. Create Deployment
    container = client.V1Container(
        name=namespace,
        image=image_url,
        resources=client.V1ResourceRequirements(
            requests={
                'cpu': str(resources.get('ram_gb', 1)),
                'memory': f"{resources.get('ram_gb', 1)}Gi",
                'nvidia.com/gpu': str(resources.get('gpus', 0))
            },
            limits={
                'cpu': str(resources.get('ram_gb', 1)),
                'memory': f"{resources.get('ram_gb', 1)}Gi",
                'nvidia.com/gpu': str(resources.get('gpus', 0))
            }
        )
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": namespace}),
        spec=client.V1PodSpec(containers=[container])
    )
    spec = client.V1DeploymentSpec(
        replicas=1,
        selector=client.V1LabelSelector(match_labels={"app": namespace}),
        template=template
    )
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=namespace, namespace=namespace),
        spec=spec
    )
    try:
        apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
    except client.exceptions.ApiException as e:
        if e.status != 409:
            raise
    # 3. Create Service
    service = client.V1Service(
        metadata=client.V1ObjectMeta(name=namespace, namespace=namespace),
        spec=client.V1ServiceSpec(
            selector={"app": namespace},
            ports=[client.V1ServicePort(port=80, target_port=80)],
            type="ClusterIP"
        )
    )
    try:
        core_v1.create_namespaced_service(namespace=namespace, body=service)
    except client.exceptions.ApiException as e:
        if e.status != 409:
            raise


def delete_k8s_resources(kubeconfig_path, pod_data):
    k8s_config.load_kube_config(config_file=kubeconfig_path)
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    namespace = pod_data['pod_id']
    # 1. Delete Service
    try:
        core_v1.delete_namespaced_service(name=namespace, namespace=namespace)
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise
    # 2. Delete Deployment
    try:
        apps_v1.delete_namespaced_deployment(name=namespace, namespace=namespace)
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise
    # 3. Delete Namespace
    try:
        core_v1.delete_namespace(name=namespace)
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise

# --- API Endpoints ---
@app.route('/')
def home():
    return (
        """
        <h2>🎉 Resource Manager Backend is Running! 🎉</h2>
        <p>Welcome! Available API endpoints:</p>
        <ul>
            <li><b>GET /servers</b> - List all servers and pods</li>
            <li><b>POST /create</b> - Create a new pod (JSON body required)</li>
            <li><b>POST /delete</b> - Delete a pod (JSON body required)</li>
        </ul>
        <p>See the frontend UI for a friendly interface.</p>
        """,
        200,
        {"Content-Type": "text/html"}
    )

@app.route('/servers', methods=['GET'])
def get_servers():
    data = load_data()
    return jsonify(data)

@app.route('/create', methods=['POST'])
def create_pod():
    req = request.json
    required_fields = ["ServerName", "PodName", "Resources", "image_url", "machine_ip", "username", "password"]
    missing = [f for f in required_fields if f not in req]
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400
    server_id = req['ServerName']
    pod_name = req['PodName']
    resources = req['Resources']
    image_url = req['image_url']
    machine_ip = req['machine_ip']
    username = req['username']
    password = req['password']
    owner = req.get('Owner', 'unknown')
    # Validate pod name (lowercase, no underscores)
    if not isinstance(pod_name, str) or not pod_name.islower() or "_" in pod_name:
        return jsonify({'error': 'Invalid pod name format. Must be lowercase and no underscores.'}), 400
    # Validate image_url
    if not (isinstance(image_url, str) and image_url.startswith("https://") and ":" in image_url):
        return jsonify({'error': 'Invalid image URL format. Must start with https:// and contain a version tag.'}), 400
    # Parse image_url
    try:
        image_url_no_proto = image_url[len("https://"):] if image_url.startswith("https://") else image_url
        registry_and_image, image_tag = image_url_no_proto.rsplit(":", 1)
        registry_url, image_name = registry_and_image.split("/", 1)
    except Exception as e:
        return jsonify({'error': f'Failed to parse image_url: {str(e)}'}), 400
    data = load_data()
    server = next((s for s in data if s['id'] == server_id), None)
    if not server:
        return jsonify({'error': 'Server not found'}), 404
    # Validate resources
    ok, err = validate_resource_request(server, resources)
    if not ok:
        return jsonify({'error': err}), 400
    # Deduct resources
    for key in ['gpus', 'ram_gb', 'storage_gb']:
        server['resources']['available'][key] -= resources.get(key, 0)
    # Add pod
    pod = {
        'pod_id': pod_name,
        'owner': owner,
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'requested': resources,
        'image_url': image_url,
        'registery_url': registry_url,
        'image_name': image_name,
        'image_tag': image_tag
    }
    server['pods'].append(pod)
    save_data(data)
    # K8s integration
    try:
        kubeconfig_path = fetch_kubeconfig(machine_ip, username, password)
        create_k8s_resources(kubeconfig_path, pod)
    except Exception as e:
        return jsonify({'error': f'Kubernetes error: {str(e)}'}), 500
    return jsonify({'message': 'Pod created', 'pod': pod})

@app.route('/delete', methods=['POST'])
def delete_pod():
    req = request.json
    required_fields = ["PodName"]
    missing = [f for f in required_fields if f not in req]
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400
    pod_name = req['PodName']
    data = load_data()
    found = False
    for server in data:
        pod = next((p for p in server['pods'] if p['pod_id'] == pod_name), None)
        if pod:
            # Release resources
            for key in ['gpus', 'ram_gb', 'storage_gb']:
                server['resources']['available'][key] += pod['requested'].get(key, 0)
            server['pods'].remove(pod)
            found = True
            break
    if not found:
        return jsonify({'error': 'Pod not found'}), 404
    save_data(data)
    return jsonify({'message': 'Pod deleted'})

@app.route('/update', methods=['POST'])
def update_pod():
    req = request.json
    required_fields = ["ServerName", "PodName"]
    missing = [f for f in required_fields if f not in req]
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400
    server_id = req['ServerName']
    pod_name = req['PodName']
    data = load_data()
    server = next((s for s in data if s['id'] == server_id), None)
    if not server:
        return jsonify({'error': 'Server not found'}), 404
    pod = next((p for p in server['pods'] if p['pod_id'] == pod_name), None)
    if not pod:
        return jsonify({'error': 'Pod not found'}), 404
    # Update fields
    updatable_fields = ["owner", "status", "requested", "image_url"]
    for field in updatable_fields:
        if field in req:
            pod[field] = req[field]
    save_data(data)
    return jsonify({'message': 'Pod updated', 'pod': pod})

@app.route('/consistency-check', methods=['GET'])
def consistency_check():
    with open('master.json') as f:
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
            for k, v in pod.get('requested', {}).items():
                pod_sums[k] = pod_sums.get(k, 0) + v
        for key in total:
            if pod_sums.get(key, 0) > total.get(key, 0):
                errors.append(f"Server {server['name']}: sum of pod {key} > total {key}")
    if errors:
        return jsonify({"status": "error", "message": "data inconsistency error", "details": errors}), 400
    else:
        return jsonify({"status": "ok", "message": "all data seems consistent"})

if __name__ == '__main__':
    app.run(debug=True)
