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


class LocalKubernetesProvider:
    """Manages local Kubernetes resources (minikube, local clusters)."""
    
    def __init__(self):
        """Initialize local Kubernetes client."""
        try:
            # Load local kubeconfig (minikube, local clusters)
            k8s_config.load_kube_config()
        except Exception as e:
            print(f"Failed to load local kubeconfig: {e}")
            raise
        
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
                        node_index = self._get_node_index(node_name, node_list)
                        if node_index is not None:
                            node_list[node_index]['pods'].append(pod_info)
            
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
            # Skip system pods
            if pod.metadata.namespace in ['kube-system', 'default']:
                return None
            
            # Extract resources
            resources = self._extract_pod_resources(pod)
            
            # Get status
            status = self._get_pod_status(pod)
            
            return {
                "pod_id": pod.metadata.name,
                "server_id": f"node-{(self._get_node_index(pod.spec.node_name, []) or 0) + 1:02d}" if pod.spec.node_name else "unknown",
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
            return PodStatus.STARTING.value
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


# Global instance for local Kubernetes
local_kubernetes_provider = LocalKubernetesProvider() 