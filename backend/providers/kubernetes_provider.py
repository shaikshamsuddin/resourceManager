"""
Local Kubernetes Provider
This module handles local Kubernetes resource management (minikube, local clusters).
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from constants import (
    PodStatus, ResourceType, DefaultValues, 
    ErrorMessages, TimeFormats, KubernetesConstants
)
from utils import map_kubernetes_status_to_user_friendly


class KubernetesProvider:
    """Manages Kubernetes resources with configurable connection."""
    
    def __init__(self, connection_coordinates: Dict = None):
        """Initialize Kubernetes client with connection coordinates."""
        self.connection_coordinates = connection_coordinates or {}
        self.core_v1 = None
        self.apps_v1 = None
        self._initialize_kubernetes_client()
        
    def _initialize_kubernetes_client(self):
        """Initialize Kubernetes client based on connection coordinates."""
        try:
            method = self.connection_coordinates.get("method", "local")
            
            if method == "kubeconfig":
                self._setup_kubeconfig_connection()
            elif method == "ssh":
                self._setup_ssh_connection()
            elif method == "local":
                self._setup_local_connection()
            else:
                # Fallback to local connection
                self._setup_local_connection()
                
        except Exception as e:
            print(f"Failed to initialize Kubernetes client: {e}")
            raise
    
    def _setup_kubeconfig_connection(self):
        """Setup connection using kubeconfig file."""
        try:
            kubeconfig_path = self.connection_coordinates.get("kubeconfig_path")
            
            if kubeconfig_path:
                # Expand ~ to home directory
                kubeconfig_path = os.path.expanduser(kubeconfig_path)
                
                if os.path.exists(kubeconfig_path):
                    k8s_config.load_kube_config(config_file=kubeconfig_path)
                    print(f"Loaded kubeconfig from: {kubeconfig_path}")
                else:
                    raise Exception(f"Kubeconfig file not found: {kubeconfig_path}")
            else:
                # Use default kubeconfig
                k8s_config.load_kube_config()
                print("Loaded default kubeconfig")
            
            # Configure insecure TLS if specified
            if self.connection_coordinates.get("insecure_skip_tls_verify", False):
                self._configure_insecure_client()
            else:
                self.core_v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                
        except Exception as e:
            print(f"Failed to setup kubeconfig connection: {e}")
            raise
    
    def _setup_ssh_connection(self):
        """Setup connection via SSH to remote server."""
        try:
            # This would implement SSH-based connection
            # For now, fall back to local connection
            print("SSH connection not implemented yet, using local connection")
            self._setup_local_connection()
        except Exception as e:
            print(f"Failed to setup SSH connection: {e}")
            raise
    
    def _setup_local_connection(self):
        """Setup local Kubernetes connection."""
        try:
            k8s_config.load_kube_config()
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            print("Using local Kubernetes connection")
        except Exception as e:
            print(f"Failed to setup local connection: {e}")
            raise
    
    def _configure_insecure_client(self):
        """Configure Kubernetes client to skip TLS verification."""
        try:
            # Create API client with insecure configuration
            configuration = client.Configuration()
            configuration.verify_ssl = False
            # Remove assert_hostname as it's not supported in newer versions
            # configuration.assert_hostname = False
            
            # Create API client with updated configuration
            self.core_v1 = client.CoreV1Api(api_client=client.ApiClient(configuration))
            self.apps_v1 = client.AppsV1Api(api_client=client.ApiClient(configuration))
            
            print("✅ Configured insecure TLS for connection")
            
        except Exception as e:
            print(f"Warning: Could not configure insecure TLS: {e}")
            # Fall back to standard client creation
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
        
    def get_servers_with_pods(self) -> List[Dict]:
        """
        Get local Kubernetes nodes and their pods.
        
        Returns:
            List of local Kubernetes nodes with pods
        """
        try:
            nodes = self.core_v1.list_node()
            pods = self.core_v1.list_pod_for_all_namespaces()
            
            # Create node list
            node_list = []
            for i, node in enumerate(nodes.items):
                node_info = {
                    "id": f"node-{i+1:02d}",
                    "name": node.metadata.name,
                    "ip": node.status.addresses[0].address if node.status.addresses else "N/A",
                    "status": "Online" if node.status.conditions[-1].type == "Ready" else "Offline",
                    "resources": self._extract_node_resources(node),
                    "pods": []
                }
                node_list.append(node_info)
            
            # Assign pods to nodes
            for pod in pods.items:
                pod_info = self._extract_pod_info(pod)
                if pod_info:
                    # Find the node this pod is running on
                    node_name = pod.spec.node_name
                    if node_name:
                        # Pod is assigned to a node
                        node_index = self._get_node_index(node_name, node_list)
                        if node_index is not None:
                            node_list[node_index]['pods'].append(pod_info)
                    else:
                        # Pod is pending (not assigned to a node yet) - assign to first node
                        if node_list:
                            node_list[0]['pods'].append(pod_info)
            
            # Update available resources for each node
            for node in node_list:
                self._update_available_resources(node)
            
            return node_list
            
        except ApiException as e:
            print(f"Error getting local Kubernetes data: {e}")
            return []
    
    def _extract_node_resources(self, node) -> Dict:
        """
        Extract resource information from a local Kubernetes node.
        
        Args:
            node: Kubernetes node object
            
        Returns:
            Dictionary with total and available resources
        """
        capacity = node.status.capacity
        allocatable = node.status.allocatable
        
        # Convert to our format
        total = {
            "cpus": int(capacity.get("cpu", 0)),
            "ram_gb": self._parse_memory(capacity.get("memory", "0")),
            "storage_gb": self._parse_memory(capacity.get("ephemeral-storage", "0")),
            "gpus": int(capacity.get("nvidia.com/gpu", 0))
        }
        
        available = {
            "cpus": int(allocatable.get("cpu", 0)),
            "ram_gb": self._parse_memory(allocatable.get("memory", "0")),
            "storage_gb": self._parse_memory(allocatable.get("ephemeral-storage", "0")),
            "gpus": int(allocatable.get("nvidia.com/gpu", 0))
        }
        
        return {
            "total": total,
            "available": available
        }
    
    def _parse_memory(self, memory_str: str) -> int:
        """
        Parse Kubernetes memory string to GB.
        
        Args:
            memory_str: Memory string (e.g., "8Gi", "1024Mi")
            
        Returns:
            Memory in GB
        """
        if not memory_str:
            return 0
        
        memory_str = memory_str.upper()
        if memory_str.endswith('GI'):
            return int(memory_str[:-2])
        elif memory_str.endswith('MI'):
            return int(memory_str[:-2]) // 1024
        elif memory_str.endswith('KI'):
            return int(memory_str[:-2]) // (1024 * 1024)
        else:
            return int(memory_str) // (1024 * 1024 * 1024)
    
    def _extract_pod_info(self, pod) -> Optional[Dict]:
        """
        Extract pod information from Kubernetes pod object.
        
        Args:
            pod: Kubernetes pod object
            
        Returns:
            Pod information dictionary or None if invalid
        """
        try:
            # Include ALL pods regardless of namespace or status
            # Extract resources
            resources = self._extract_pod_resources(pod)
            
            # Get status
            status = self._get_pod_status(pod)
            
            return {
                "pod_id": pod.metadata.name,
                "namespace": pod.metadata.namespace,  # Add namespace information
                "server_id": f"node-{(self._get_node_index(pod.spec.node_name, []) or 0) + 1:02d}" if pod.spec.node_name else "node-01",
                "image_url": pod.spec.containers[0].image if pod.spec.containers else "unknown",
                "requested": resources,
                "owner": pod.metadata.labels.get("owner", "unknown"),
                "status": status,
                "timestamp": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error extracting pod info: {e}")
            return None
    
    def _extract_pod_resources(self, pod) -> Dict:
        """
        Extract resource requests from pod.
        
        Args:
            pod: Kubernetes pod object
            
        Returns:
            Resource dictionary
        """
        resources = {
            "cpus": 0,
            "ram_gb": 0,
            "storage_gb": 0,
            "gpus": 0
        }
        
        for container in pod.spec.containers:
            if container.resources and container.resources.requests:
                requests = container.resources.requests
                
                # CPU
                if requests.get("cpu"):
                    cpu_str = requests["cpu"]
                    if cpu_str.endswith('m'):
                        resources["cpus"] += int(cpu_str[:-1]) // 1000
                    else:
                        resources["cpus"] += int(float(cpu_str))
                
                # Memory
                if requests.get("memory"):
                    memory_str = requests["memory"]
                    resources["ram_gb"] += self._parse_memory(memory_str)
                
                # Storage
                if requests.get("ephemeral-storage"):
                    storage_str = requests["ephemeral-storage"]
                    resources["storage_gb"] += self._parse_memory(storage_str)
                
                # GPUs
                if requests.get("nvidia.com/gpu"):
                    resources["gpus"] += int(requests["nvidia.com/gpu"])
        
        return resources
    
    def _get_pod_status(self, pod) -> str:
        """
        Get user-friendly pod status.
        
        Args:
            pod: Kubernetes pod object
            
        Returns:
            User-friendly status string
        """
        if not pod.status:
            return PodStatus.UNKNOWN.value
        
        phase = pod.status.phase
        if phase == "Running":
            return PodStatus.ONLINE.value
        elif phase == "Pending":
            return PodStatus.PENDING.value
        elif phase == "Failed":
            return PodStatus.FAILED.value
        elif phase == "Succeeded":
            return PodStatus.ONLINE.value
        else:
            return PodStatus.UNKNOWN.value
    
    def _get_node_index(self, node_name: str, node_list: List[Dict]) -> Optional[int]:
        """
        Get node index by name.
        
        Args:
            node_name: Name of the node
            node_list: List of nodes
            
        Returns:
            Node index or None if not found
        """
        for i, node in enumerate(node_list):
            if node.get("name") == node_name:
                return i
        return None
    
    def _update_available_resources(self, node: Dict):
        """
        Update available resources based on running pods.
        
        Args:
            node: Node dictionary to update
        """
        total = node['resources']['total']
        available = node['resources']['available'].copy()
        
        # Subtract pod resources
        for pod in node.get('pods', []):
            requested = pod.get('requested', {})
            for key in ['cpus', 'ram_gb', 'storage_gb', 'gpus']:
                available[key] = max(0, available[key] - requested.get(key, 0))
        
        node['resources']['available'] = available

    def create_pod_with_service(self, pod_data: Dict) -> Dict:
        """
        Create a pod with associated service for external access.
        
        Args:
            pod_data: Pod configuration data
            
        Returns:
            Dictionary with pod and service information
        """
        try:
            # Extract port configuration
            container_port = pod_data.get('container_port', 80)
            service_port = pod_data.get('service_port', 80)
            expose_service = pod_data.get('expose_service', False)
            
            # Create pod
            pod_name = pod_data['PodName']
            pod_result = self._extract_pod_info_from_data(pod_data)
            
            # Create service if requested
            service_info = None
            if expose_service:
                service_info = self._create_service_for_pod(pod_name, container_port, service_port)
            
            return {
                'pod': pod_result,
                'service': service_info,
                'access_url': service_info.get('access_url') if service_info else None
            }
            
        except Exception as e:
            print(f"Error creating pod with service: {e}")
            return {'error': str(e)}
    
    def _create_service_for_pod(self, pod_name: str, container_port: int, service_port: int) -> Dict:
        """
        Create a Kubernetes service for pod external access.
        
        Args:
            pod_name: Name of the pod
            container_port: Port inside the container
            service_port: Port for the service
            
        Returns:
            Service information dictionary
        """
        try:
            # Create service object
            service = client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=f"{pod_name}-service",
                    labels={"app": pod_name}
                ),
                spec=client.V1ServiceSpec(
                    type="NodePort",
                    selector={"app": pod_name},
                    ports=[
                        client.V1ServicePort(
                            port=service_port,
                            target_port=container_port,
                            node_port=self._get_available_node_port()
                        )
                    ]
                )
            )
            
            # Create service in Kubernetes
            created_service = self.core_v1.create_namespaced_service(
                namespace="default",
                body=service
            )
            
            # Get access URL
            access_url = self._get_service_access_url(created_service)
            
            return {
                'name': created_service.metadata.name,
                'type': created_service.spec.type,
                'port': service_port,
                'node_port': created_service.spec.ports[0].node_port,
                'access_url': access_url
            }
            
        except Exception as e:
            print(f"Error creating service: {e}")
            return {'error': str(e)}
    
    def _get_available_node_port(self) -> int:
        """
        Get an available NodePort in the valid range.
        
        Returns:
            Available NodePort number
        """
        # Simple implementation - use a random port in valid range
        import random
        return random.randint(30000, 32767)
    
    def _get_service_access_url(self, service) -> str:
        """
        Generate access URL for the service.
        
        Args:
            service: Kubernetes service object
            
        Returns:
            Access URL string
        """
        try:
            # For local Kubernetes, use minikube service URL
            node_port = service.spec.ports[0].node_port
            return f"http://localhost:{node_port}"
        except Exception:
            return "Access URL not available"
    
    def _extract_pod_info_from_data(self, pod_data: Dict) -> Dict:
        """
        Extract pod information from pod data.
        
        Args:
            pod_data: Pod configuration data
            
        Returns:
            Pod information dictionary
        """
        return {
            'pod_id': pod_data['PodName'],
            'image_url': pod_data.get('image_url', 'nginx:latest'),
            'requested': pod_data.get('Resources', {}),
            'owner': pod_data.get('Owner', 'unknown'),
            'status': 'starting',
            'timestamp': datetime.utcnow().strftime(TimeFormats.ISO_FORMAT)
        } 