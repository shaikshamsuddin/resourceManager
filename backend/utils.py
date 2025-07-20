"""
Utility functions and Kubernetes operations for Resource Manager backend.
This module contains helper functions and Kubernetes resource management logic.
"""

import json
import os
import tempfile
import uuid
import yaml
from datetime import datetime
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException
import paramiko


def get_available_resources(server):
    """
    Get available resources for a server.
    
    Args:
        server (dict): Server data containing resources information
        
    Returns:
        dict: Available resources (gpus, ram_gb, storage_gb)
    """
    if not server:
        return {
            'gpus': 0,
            'ram_gb': 0,
            'storage_gb': 0
        }
    total = server.get('resources', {}).get('total', {})
    available = server.get('resources', {}).get('available', {})
    return {
        'gpus': available.get('gpus', 0),
        'ram_gb': available.get('ram_gb', 0),
        'storage_gb': available.get('storage_gb', 0)
    }


def validate_resource_request(server, requested):
    """
    Validate if requested resources are available on the server.
    
    Args:
        server (dict): Server data
        requested (dict): Requested resources
        
    Returns:
        tuple: (is_valid, error_message)
    """
    available = get_available_resources(server)
    for key in ['gpus', 'ram_gb', 'storage_gb']:
        if requested.get(key, 0) > available.get(key, 0):
            return False, f"Not enough {key} available. Requested: {requested.get(key, 0)}, Available: {available.get(key, 0)}"
    return True, None


def fetch_kubeconfig(machine_ip, username, password):
    """
    SSH to VM and fetch kubeconfig file.
    
    Args:
        machine_ip (str): IP address of the machine
        username (str): SSH username
        password (str): SSH password
        
    Returns:
        str: Path to the modified kubeconfig file
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=machine_ip, username=username, password=password, timeout=60)
    
    stdin, stdout, _ = ssh.exec_command("sudo microk8s config")
    config_data = stdout.read().decode()
    ssh.close()
    
    config_dict = yaml.safe_load(config_data)
    public_ip = machine_ip
    
    # Modify kubeconfig for external access
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


def get_kubeconfig():
    """
    Get kubeconfig for local Kubernetes cluster.
    This function tries multiple approaches to connect to Kubernetes.
    
    Returns:
        str: Path to kubeconfig file or None if using in-cluster config
    """
    # Try to load from default kubeconfig locations
    try:
        # This will automatically load from ~/.kube/config or KUBECONFIG env var
        k8s_config.load_kube_config()
        return None  # Using default config
    except Exception:
        pass
    
    # Try in-cluster configuration (if running inside a pod)
    try:
        k8s_config.load_incluster_config()
        return None  # Using in-cluster config
    except Exception:
        pass
    
    # If neither works, raise an error
    raise Exception("Could not load Kubernetes configuration. Please ensure kubeconfig is available.")


def create_k8s_resources_simple(pod_data):
    """
    Create Kubernetes resources using local kubeconfig.
    
    Args:
        pod_data (dict): Pod configuration data
    """
    # Load kubeconfig (local or in-cluster)
    get_kubeconfig()
    
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    
    namespace = pod_data['pod_id']
    image_url = pod_data['image_url']
    resources = pod_data['requested']
    
    # 1. Create Namespace
    ns_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
    try:
        core_v1.create_namespace(ns_body)
    except ApiException as e:
        if e.status != 409:  # 409 = AlreadyExists
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
    except ApiException as e:
        if e.status != 409:  # 409 = AlreadyExists
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
    except ApiException as e:
        if e.status != 409:  # 409 = AlreadyExists
            raise


def delete_k8s_resources_simple(pod_data):
    """
    Delete Kubernetes resources using local kubeconfig.
    
    Args:
        pod_data (dict): Pod configuration data
    """
    # Load kubeconfig (local or in-cluster)
    get_kubeconfig()
    
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    
    namespace = pod_data['pod_id']
    
    # 1. Delete Service
    try:
        core_v1.delete_namespaced_service(name=namespace, namespace=namespace)
    except ApiException as e:
        if e.status != 404:  # 404 = NotFound
            raise
    
    # 2. Delete Deployment
    try:
        apps_v1.delete_namespaced_deployment(name=namespace, namespace=namespace)
    except ApiException as e:
        if e.status != 404:  # 404 = NotFound
            raise
    
    # 3. Delete Namespace
    try:
        core_v1.delete_namespace(name=namespace)
    except ApiException as e:
        if e.status != 404:  # 404 = NotFound
            raise


def create_pod_object(pod_data, server_id):
    """
    Create a pod object for storage in the mock database.
    
    Args:
        pod_data (dict): Pod configuration data
        server_id (str): Server ID where pod will be deployed
        
    Returns:
        dict: Pod object with all required fields
    """
    return {
        'pod_id': pod_data['PodName'],
        'server_id': server_id,
        'image_url': pod_data['image_url'],
        'requested': pod_data['Resources'],
        'owner': pod_data.get('Owner', 'unknown'),
        'status': 'Running',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }


def update_pod_object(pod_data, server_id):
    """
    Update a pod object with new data.
    
    Args:
        pod_data (dict): Updated pod configuration data
        server_id (str): Server ID
        
    Returns:
        dict: Updated pod object
    """
    return {
        'pod_id': pod_data['PodName'],
        'server_id': server_id,
        'image_url': pod_data['image_url'],
        'requested': pod_data['Resources'],
        'owner': pod_data.get('Owner', 'unknown'),
        'status': 'Running',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    } 