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

from config import Config
from k8s_client import k8s_client
from constants import (
    ResourceType, PodStatus, DefaultValues, ErrorMessages,
    SuccessMessages, TimeFormats
)


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
            ResourceType.GPUS.value: 0,
            ResourceType.RAM_GB.value: 0,
            ResourceType.STORAGE_GB.value: 0
        }
    total = server.get('resources', {}).get('total', {})
    available = server.get('resources', {}).get('available', {})
    return {
        ResourceType.GPUS.value: available.get(ResourceType.GPUS.value, 0),
        ResourceType.RAM_GB.value: available.get(ResourceType.RAM_GB.value, 0),
        ResourceType.STORAGE_GB.value: available.get(ResourceType.STORAGE_GB.value, 0)
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
    resource_types = [ResourceType.GPUS, ResourceType.RAM_GB, ResourceType.STORAGE_GB]
    
    for resource_type in resource_types:
        key = resource_type.value
        if requested.get(key, 0) > available.get(key, 0):
            return False, ErrorMessages.INSUFFICIENT_RESOURCES.format(
                resource=key,
                requested=requested.get(key, 0),
                available=available.get(key, 0)
            )
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
    Create Kubernetes resources using environment-aware client.
    
    Args:
        pod_data (dict): Pod configuration data
    """
    namespace = pod_data['pod_id']
    image_url = pod_data['image_url']
    resources = pod_data['requested']
    
    # Use the new Kubernetes client
    k8s_client.create_namespace(namespace)
    k8s_client.create_deployment(namespace, namespace, image_url, resources)
    k8s_client.create_service(namespace, namespace)


def delete_k8s_resources_simple(pod_data):
    """
    Delete Kubernetes resources using environment-aware client.
    
    Args:
        pod_data (dict): Pod configuration data
    """
    namespace = pod_data['pod_id']
    
    # Use the new Kubernetes client
    k8s_client.delete_service(namespace, namespace)
    k8s_client.delete_deployment(namespace, namespace)
    k8s_client.delete_namespace(namespace)


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
        'image_url': pod_data.get('image_url', Config.get_default_image()),
        'requested': pod_data['Resources'],
        'owner': pod_data.get('Owner', DefaultValues.DEFAULT_OWNER),
        'status': PodStatus.IN_PROGRESS.value,  # Start with in-progress status
        'timestamp': datetime.utcnow().strftime(TimeFormats.ISO_FORMAT)
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
        'image_url': pod_data.get('image_url', Config.get_default_image()),
        'requested': pod_data['Resources'],
        'owner': pod_data.get('Owner', DefaultValues.DEFAULT_OWNER),
        'status': PodStatus.RUNNING.value,
        'timestamp': datetime.utcnow().strftime(TimeFormats.ISO_FORMAT)
    } 

def map_kubernetes_status_to_user_friendly(kubernetes_status: str) -> str:
    """
    Map Kubernetes pod status to user-friendly status.
    
    Args:
        kubernetes_status: Raw Kubernetes pod status
        
    Returns:
        User-friendly status string
    """
    status_mapping = {
        # Kubernetes states to user-friendly states
        'Running': 'online',
        'Pending': 'starting',
        'Failed': 'failed',
        'Succeeded': 'online',
        'Unknown': 'unknown',
        'Terminated': 'failed',
        'CrashLoopBackOff': 'error',
        'ImagePullBackOff': 'error',
        'ErrImagePull': 'error',
        'CreateContainerError': 'error',
        'CreateContainerConfigError': 'error',
        'InvalidImageName': 'error',
        'ContainerCreating': 'starting',
        'PodInitializing': 'starting',
        'Terminating': 'updating',
        
        # User-friendly states (pass through)
        'online': 'online',
        'starting': 'starting',
        'in-progress': 'in-progress',
        'updating': 'updating',
        'failed': 'failed',
        'error': 'error',
        'unknown': 'unknown',
        'timeout': 'timeout'
    }
    
    return status_mapping.get(kubernetes_status, 'unknown')

def get_status_color(status: str) -> str:
    """
    Get CSS color class for pod status.
    
    Args:
        status: Pod status string
        
    Returns:
        CSS color class name
    """
    color_mapping = {
        # Success states - Green
        'online': 'status-success',
        'starting': 'status-success',
        
        # Progress states - Blue
        'in-progress': 'status-progress',
        'updating': 'status-progress',
        
        # Failure states - Red
        'failed': 'status-error',
        'error': 'status-error',
        'timeout': 'status-error',
        
        # Unknown states - Grey
        'unknown': 'status-unknown'
    }
    
    return color_mapping.get(status, 'status-unknown')

def get_status_icon(status: str) -> str:
    """
    Get Material Design icon name for pod status.
    
    Args:
        status: Pod status string
        
    Returns:
        Material Design icon name
    """
    icon_mapping = {
        # Success states
        'online': 'check_circle',
        'starting': 'hourglass_empty',
        
        # Progress states
        'in-progress': 'sync',
        'updating': 'update',
        
        # Failure states
        'failed': 'error',
        'error': 'error_outline',
        'timeout': 'schedule',
        
        # Unknown states
        'unknown': 'help_outline'
    }
    
    return icon_mapping.get(status, 'help_outline') 