"""
Cloud Kubernetes Provider
This module handles cloud Kubernetes resource management (Azure AKS, GKE, Azure VM, etc.).
"""

import json
import os
import subprocess
import tempfile
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

# Suppress SSL/TLS warnings for development environments
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', category=Warning, module='urllib3')

from config.constants import (
    PodStatus, ResourceType, DefaultValues, 
    ErrorMessages, TimeFormats, KubernetesConstants
)
from config.utils import map_kubernetes_status_to_user_friendly


class CloudKubernetesProvider:
    """Manages cloud Kubernetes resources (Azure AKS, GKE, Azure VM, etc.)."""
    
    def __init__(self, server_config: Dict = None):
        """Initialize cloud Kubernetes client."""
        self.server_config = server_config
        self.core_v1 = None
        self.apps_v1 = None
        self._initialized = False
        
        # Don't initialize immediately - wait until first use
        # This prevents password prompts during startup
    
    def _initialize_with_server_config(self, server_config: Dict):
        """Initialize Kubernetes client using server configuration from master.json."""
        try:
            # Check if this is a dummy server
            connection_coords = server_config.get('connection_coordinates', {})
            if connection_coords.get('is_dummy', False):
                print(f"⏭️  Skipping initialization for dummy server: {server_config.get('id')}")
                return
            
            kubeconfig_data = connection_coords.get('kubeconfig_data')
            
            if kubeconfig_data:
                # Use kubeconfig data from master.json
                print(f"Initializing with kubeconfig data for server: {server_config.get('id')}")
                self._load_kubeconfig_from_data(kubeconfig_data)
            else:
                # Fall back to file path
                kubeconfig_path = connection_coords.get('kubeconfig_path')
                if kubeconfig_path:
                    print(f"Initializing with kubeconfig file: {kubeconfig_path}")
                    self._load_kubeconfig_from_file(kubeconfig_path)
                else:
                    raise Exception("No kubeconfig data or path found in server configuration")
                    
        except Exception as e:
            print(f"Failed to initialize with server config: {e}")
            raise
    
    def _load_kubeconfig_from_data(self, kubeconfig_data: Dict):
        """Load kubeconfig from data dictionary with fallback authentication."""
        try:
            import tempfile
            import os
            
            # First, try certificate-based authentication (primary method)
            users = kubeconfig_data.get('users', [])
            if users and len(users) > 0:
                user = users[0].get('user', {})
                if 'client-certificate-data' in user and 'client-key-data' in user:
                    print("🔐 Attempting certificate-based authentication...")
                    try:
                        # Create temporary kubeconfig file for certificate-based auth
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as temp_file:
                            import yaml
                            yaml.dump(kubeconfig_data, temp_file)
                            temp_file_path = temp_file.name
                        
                        # Load the kubeconfig
                        k8s_config.load_kube_config(config_file=temp_file_path)
                        
                        # Create API clients with the loaded configuration
                        self.core_v1 = client.CoreV1Api()
                        self.apps_v1 = client.AppsV1Api()
                        
                        # Clean up temporary file
                        os.unlink(temp_file_path)
                        
                        print("✅ Certificate-based authentication successful")
                        return
                        
                    except Exception as cert_error:
                        print(f"❌ Certificate-based authentication failed: {cert_error}")
                        # Clean up temp file if it exists
                        if 'temp_file_path' in locals():
                            try:
                                os.unlink(temp_file_path)
                            except:
                                pass
                        # Continue to fallback authentication
            
            # Fallback: Try username/password authentication
            if users and len(users) > 0:
                user = users[0].get('user', {})
                if 'username' in user and 'password' in user:
                    print("🔑 Attempting username/password authentication (fallback)...")
                    try:
                        self._load_kubeconfig_with_credentials(kubeconfig_data)
                        print("✅ Username/password authentication successful")
                        return
                    except Exception as cred_error:
                        print(f"❌ Username/password authentication failed: {cred_error}")
                        raise Exception(f"Both certificate and username/password authentication failed")
            
            # If we get here, no valid authentication method found
            raise Exception("No valid authentication method found in kubeconfig")
            
        except Exception as e:
            print(f"Failed to load kubeconfig from data: {e}")
            raise
    
    def _load_kubeconfig_with_credentials(self, kubeconfig_data: Dict):
        """Load kubeconfig with username/password authentication."""
        try:
            # Extract cluster and user info
            clusters = kubeconfig_data.get('clusters', [])
            users = kubeconfig_data.get('users', [])
            
            if not clusters or not users:
                raise Exception("Invalid kubeconfig: missing clusters or users")
            
            cluster = clusters[0]
            user = users[0]
            
            # Get connection details
            server = cluster['cluster']['server']
            username = user['user']['username']
            password = user['user']['password']
            
            # Create configuration with basic auth
            configuration = client.Configuration()
            configuration.host = server
            configuration.username = username
            configuration.password = password
            configuration.verify_ssl = False  # For Azure VM connections
            
            # Create API clients
            self.core_v1 = client.CoreV1Api(api_client=client.ApiClient(configuration))
            self.apps_v1 = client.AppsV1Api(api_client=client.ApiClient(configuration))
            
            print(f"Successfully loaded kubeconfig with credentials for {username}@{server}")
            
        except Exception as e:
            print(f"Failed to load kubeconfig with credentials: {e}")
            raise
    
    def _load_kubeconfig_from_file(self, kubeconfig_path: str):
        """Load kubeconfig from file path."""
        try:
            from pathlib import Path
            
            # Convert relative path to absolute
            if not os.path.isabs(kubeconfig_path):
                backend_dir = Path(__file__).parent.parent
                kubeconfig_path = str(backend_dir / kubeconfig_path)
            
            if not os.path.exists(kubeconfig_path):
                raise Exception(f"Kubeconfig file not found: {kubeconfig_path}")
            
            # Load the kubeconfig
            k8s_config.load_kube_config(config_file=kubeconfig_path)
            
            # Create API clients with the loaded configuration
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            
            print(f"Successfully loaded kubeconfig from file: {kubeconfig_path}")
            
        except Exception as e:
            print(f"Failed to load kubeconfig from file: {e}")
            raise
        
    def _initialize_kubernetes_client(self):
        """Initialize Kubernetes client with support for Azure VM connections."""
        try:
            # Check if we're connecting to an Azure VM
            azure_vm_ip = os.getenv('AZURE_VM_IP')
            
            if azure_vm_ip:
                # Azure VM connection - create kubeconfig from VM
                print(f"Detected Azure VM connection to: {azure_vm_ip}")
                try:
                    self._setup_azure_vm_connection(azure_vm_ip)
                except Exception as e:
                    print(f"⚠️  Azure VM connection failed (will be configured via API): {e}")
                    # Don't fail startup - let users configure via API
                    self.client = None
                    return
            else:
                # Standard cloud connection (Azure AKS, GKE, etc.)
                print("Using standard cloud Kubernetes connection")
                try:
                    self._setup_standard_cloud_connection()
                except Exception as e:
                    print(f"⚠️  Cloud connection failed: {e}")
                    # Don't fail startup - let users configure via API
                    self.client = None
                    return
                
        except Exception as e:
            print(f"⚠️  Kubernetes client initialization failed: {e}")
            # Don't fail startup - let users configure via API
            self.client = None
    
    def _setup_azure_vm_connection(self, vm_ip: str):
        """Setup connection to Azure VM Kubernetes cluster."""
        try:
            # Get Azure VM connection details
            vm_username = os.getenv('AZURE_VM_USERNAME', 'azureuser')
            vm_ssh_key = os.getenv('AZURE_VM_SSH_KEY_PATH')
            
            # Check if kubeconfig is already provided
            kubeconfig_path = os.getenv('AZURE_VM_KUBECONFIG')
            if kubeconfig_path and os.path.exists(kubeconfig_path):
                print(f"Using provided kubeconfig: {kubeconfig_path}")
                # Load kubeconfig with insecure TLS for Azure VM
                k8s_config.load_kube_config(config_file=kubeconfig_path)
                # Configure client to skip TLS verification
                self._configure_insecure_client()
                return
            
            # Create kubeconfig from Azure VM
            kubeconfig_content = self._generate_kubeconfig_from_vm(vm_ip, vm_username, vm_ssh_key)
            
            # Write to temporary file
            temp_dir = tempfile.gettempdir()
            kubeconfig_path = os.path.join(temp_dir, 'azure_vm_kubeconfig')
            
            with open(kubeconfig_path, 'w') as f:
                f.write(kubeconfig_content)
            
            # Load the kubeconfig
            k8s_config.load_kube_config(config_file=kubeconfig_path)
            # Configure client to skip TLS verification
            self._configure_insecure_client()
            print(f"Created and loaded kubeconfig from Azure VM: {kubeconfig_path}")
            
        except Exception as e:
            print(f"Failed to setup Azure VM connection: {e}")
            raise
    
    def _setup_standard_cloud_connection(self):
        """Setup standard cloud Kubernetes connection."""
        try:
            # Try to load cloud kubeconfig (Azure AKS, GKE, etc.)
            k8s_config.load_kube_config()
        except Exception as e:
            print(f"Failed to load cloud kubeconfig: {e}")
            # Fall back to in-cluster config for cloud deployments
            try:
                k8s_config.load_incluster_config()
            except Exception as e2:
                print(f"Failed to load in-cluster config: {e2}")
                raise
    
    def _generate_kubeconfig_from_vm(self, vm_ip: str, username: str, ssh_key_path: Optional[str] = None) -> str:
        """Generate kubeconfig by connecting to Azure VM."""
        try:
            # Build SSH command
            ssh_cmd = ['ssh']
            if ssh_key_path:
                ssh_cmd.extend(['-i', ssh_key_path])
            else:
                # Use password authentication if no SSH key provided
                ssh_cmd.extend(['-o', 'PubkeyAuthentication=no'])
                ssh_cmd.extend(['-o', 'PasswordAuthentication=yes'])
            
            ssh_cmd.extend(['-o', 'StrictHostKeyChecking=no'])
            ssh_cmd.extend([f'{username}@{vm_ip}'])
            
            # Get kubeconfig from VM
            kubeconfig_cmd = ssh_cmd + ['cat ~/.kube/config']
            result = subprocess.run(kubeconfig_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # If password authentication failed, try with sshpass
                if not ssh_key_path:
                    print("Trying password authentication with sshpass...")
                    return self._generate_kubeconfig_with_password(vm_ip, username)
                else:
                    raise Exception(f"Failed to get kubeconfig from VM: {result.stderr}")
            
            kubeconfig_content = result.stdout
            
            # Update server address to use VM IP
            kubeconfig_data = json.loads(kubeconfig_content)
            for cluster in kubeconfig_data.get('clusters', []):
                if 'cluster' in cluster and 'server' in cluster['cluster']:
                    # Replace localhost/127.0.0.1 with VM IP
                    server = cluster['cluster']['server']
                    if 'localhost' in server or '127.0.0.1' in server:
                        # Extract port from server URL
                        if ':' in server:
                            port = server.split(':')[-1]
                            cluster['cluster']['server'] = f'https://{vm_ip}:{port}'
                        else:
                            cluster['cluster']['server'] = f'https://{vm_ip}:6443'
            
            return json.dumps(kubeconfig_data, indent=2)
            
        except subprocess.TimeoutExpired:
            raise Exception("Timeout connecting to Azure VM")
        except Exception as e:
            raise Exception(f"Failed to generate kubeconfig: {e}")
    
    def _generate_kubeconfig_with_password(self, vm_ip: str, username: str) -> str:
        """Generate kubeconfig using password authentication with sshpass."""
        try:
            # Get password from environment
            password = os.getenv('AZURE_VM_PASSWORD')
            if not password:
                raise Exception("AZURE_VM_PASSWORD environment variable not set")
            
            # Use sshpass for password authentication
            ssh_cmd = ['sshpass', '-p', password, 'ssh']
            ssh_cmd.extend(['-o', 'StrictHostKeyChecking=no'])
            ssh_cmd.extend(['-o', 'PubkeyAuthentication=no'])
            ssh_cmd.extend([f'{username}@{vm_ip}'])
            
            # Get kubeconfig from VM
            kubeconfig_cmd = ssh_cmd + ['cat ~/.kube/config']
            result = subprocess.run(kubeconfig_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Failed to get kubeconfig from VM: {result.stderr}")
            
            kubeconfig_content = result.stdout
            
            # Update server address to use VM IP
            kubeconfig_data = json.loads(kubeconfig_content)
            for cluster in kubeconfig_data.get('clusters', []):
                if 'cluster' in cluster and 'server' in cluster['cluster']:
                    # Replace localhost/127.0.0.1 with VM IP
                    server = cluster['cluster']['server']
                    if 'localhost' in server or '127.0.0.1' in server:
                        # Extract port from server URL
                        if ':' in server:
                            port = server.split(':')[-1]
                            cluster['cluster']['server'] = f'https://{vm_ip}:{port}'
                        else:
                            cluster['cluster']['server'] = f'https://{vm_ip}:6443'
            
            return json.dumps(kubeconfig_data, indent=2)
            
        except subprocess.TimeoutExpired:
            raise Exception("Timeout connecting to Azure VM")
        except Exception as e:
            raise Exception(f"Failed to generate kubeconfig with password: {e}")
    
    def _ensure_initialized(self):
        """Ensure the Kubernetes client is initialized before use."""
        if not self._initialized:
            if self.server_config:
                try:
                    # Initialize with server configuration
                    self._initialize_with_server_config(self.server_config)
                except Exception as e:
                    print(f"Failed to initialize cloud Kubernetes client with server config: {e}")
                    raise
            else:
                try:
                    # Try to load cloud kubeconfig (Azure AKS, GKE, Azure VM, etc.)
                    self._initialize_kubernetes_client()
                except Exception as e:
                    print(f"Failed to initialize cloud Kubernetes client: {e}")
                    raise
            
            if self.core_v1 is None:
                self.core_v1 = client.CoreV1Api()
            if self.apps_v1 is None:
                self.apps_v1 = client.AppsV1Api()
            
            self._initialized = True

    def get_servers_with_pods(self) -> List[Dict]:
        """
        Get cloud Kubernetes nodes and their pods.
        
        Returns:
            List of cloud Kubernetes nodes with pods
        """
        try:
            # Check if this is a dummy server
            if self.server_config and self.server_config.get('connection_coordinates', {}).get('is_dummy', False):
                print(f"⏭️  Returning static data for dummy server: {self.server_config.get('id')}")
                # Return static data from server config
                return [{
                    "id": self.server_config.get('id'),
                    "name": self.server_config.get('name', 'Dummy Server'),
                    "ip": self.server_config.get('connection_coordinates', {}).get('host', '0.0.0.0'),
                    "status": "Offline",  # Dummy servers are offline
                    "resources": self.server_config.get('resources', {
                        "total": {}, "allocated": {}, "available": {}, "actual_usage": {}
                    }),
                    "pods": self.server_config.get('pods', [])
                }]
            
            # Initialize client on first use
            self._ensure_initialized()
            
            nodes = self.core_v1.list_node()
            pods = self.core_v1.list_pod_for_all_namespaces()
            
            # Create node list
            node_list = []
            for i, node in enumerate(nodes.items):
                node_info = {
                    "id": f"cloud-node-{i+1:02d}",
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
            
            # Update available resources and get actual usage for each node
            for node in node_list:
                self._update_available_resources(node)
                
                # Get actual resource usage
                actual_usage = self._get_actual_resource_usage(node['name'])
                node['resources']['actual_usage'] = actual_usage
            
            return node_list
            
        except ApiException as e:
            print(f"Error getting cloud Kubernetes data: {e}")
            return []
    
    def _extract_node_resources(self, node) -> Dict:
        """
        Extract resource information from a cloud Kubernetes node.
        
        Args:
            node: Kubernetes node object
            
        Returns:
            Dictionary with total, allocated, and actual usage resources
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
        
        allocated = {
            "cpus": int(allocatable.get("cpu", 0)),
            "ram_gb": self._parse_memory(allocatable.get("memory", "0")),
            "storage_gb": self._parse_memory(allocatable.get("ephemeral-storage", "0")),
            "gpus": int(allocatable.get("nvidia.com/gpu", 0))
        }
        
        return {
            "total": total,
            "allocated": allocated,
            "available": allocated.copy()  # Will be updated by _update_available_resources
        }
    
    def _parse_memory(self, memory_str: str) -> int:
        """
        Parse Kubernetes memory string to GB.
        
        Args:
            memory_str: Memory string (e.g., "8Gi", "1024Mi", "100u")
            
        Returns:
            Memory in GB
        """
        if not memory_str:
            return 0
        
        memory_str = memory_str.upper()
        
        # Handle various suffixes
        if memory_str.endswith('GI'):
            return int(memory_str[:-2])
        elif memory_str.endswith('MI'):
            return int(memory_str[:-2]) // 1024
        elif memory_str.endswith('KI'):
            return int(memory_str[:-2]) // (1024 * 1024)
        elif memory_str.endswith('U'):
            # Handle micro units (e.g., "100u" = 100 microseconds)
            try:
                return int(memory_str[:-1]) // (1024 * 1024 * 1024 * 1024)  # Convert to GB
            except ValueError:
                return 0
        else:
            try:
                return int(memory_str) // (1024 * 1024 * 1024)
            except ValueError:
                return 0
    
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
                "namespace": pod.metadata.namespace,  # Add namespace information
                "server_id": f"cloud-node-{(self._get_node_index(pod.spec.node_name, []) or 0) + 1:02d}" if pod.spec.node_name else "unknown",
                "image_url": pod.spec.containers[0].image if pod.spec.containers else "unknown",
                "requested": resources,
                "owner": pod.metadata.labels.get("owner", "unknown"),
                "status": status,
                "timestamp": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else datetime.now().isoformat(),
                "pod_ip": pod.status.pod_ip if pod.status and pod.status.pod_ip else None
            }
        except Exception as e:
            print(f"Error extracting pod info: {e}")
            return None
    
    def _extract_pod_resources(self, pod) -> Dict:
        """
        Extract resource requests and limits from pod.
        
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
            if container.resources:
                # Check resource requests first
                if container.resources.requests:
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
                
                # If no requests, check limits
                elif container.resources.limits:
                    limits = container.resources.limits
                    
                    # CPU
                    if limits.get("cpu"):
                        cpu_str = limits["cpu"]
                        if cpu_str.endswith('m'):
                            resources["cpus"] += int(cpu_str[:-1]) // 1000
                        else:
                            resources["cpus"] += int(float(cpu_str))
                    
                    # Memory
                    if limits.get("memory"):
                        memory_str = limits["memory"]
                        resources["ram_gb"] += self._parse_memory(memory_str)
                    
                    # Storage
                    if limits.get("ephemeral-storage"):
                        storage_str = limits["ephemeral-storage"]
                        resources["storage_gb"] += self._parse_memory(storage_str)
                    
                    # GPUs
                    if limits.get("nvidia.com/gpu"):
                        resources["gpus"] += int(limits["nvidia.com/gpu"])
                
                # If no requests or limits, use default estimates based on container type
                else:
                    # Default estimates for common container types
                    image = container.image.lower()
                    if any(keyword in image for keyword in ['nginx', 'httpd', 'apache']):
                        resources["cpus"] += 0.1
                        resources["ram_gb"] += 0.1
                    elif any(keyword in image for keyword in ['python', 'node', 'java', 'golang']):
                        resources["cpus"] += 0.5
                        resources["ram_gb"] += 0.5
                    elif any(keyword in image for keyword in ['database', 'mysql', 'postgres', 'redis']):
                        resources["cpus"] += 1.0
                        resources["ram_gb"] += 1.0
                    else:
                        # Generic default for unknown containers
                        resources["cpus"] += 0.25
                        resources["ram_gb"] += 0.25
        
        return resources
    
    def _get_actual_resource_usage(self, node_name: str) -> Dict:
        """
        Get actual resource usage from Kubernetes metrics API.
        
        Args:
            node_name: Name of the node
            
        Returns:
            Dictionary with actual resource usage
        """
        try:
            # Try to get metrics from metrics.k8s.io API
            # Note: This requires metrics-server to be installed
            from kubernetes.client import CustomObjectsApi
            custom_api = CustomObjectsApi()
            
            # Get pod metrics
            metrics = custom_api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace="",
                plural="pods"
            )
            
            total_usage = {
                "cpus": 0.0,
                "ram_gb": 0.0,
                "storage_gb": 0.0,
                "gpus": 0
            }
            
            for pod_metric in metrics.get('items', []):
                pod_name = pod_metric['metadata']['name']
                namespace = pod_metric['metadata']['namespace']
                
                # Check if this pod is on our target node
                try:
                    pod = self.core_v1.read_namespaced_pod(pod_name, namespace)
                    if pod.spec.node_name == node_name:
                        for container in pod_metric.get('containers', []):
                            # CPU usage (convert from nanocores to cores)
                            cpu_usage = container.get('usage', {}).get('cpu', '0')
                            if cpu_usage.endswith('n'):
                                total_usage["cpus"] += int(cpu_usage[:-1]) / 1000000000
                            else:
                                total_usage["cpus"] += float(cpu_usage)
                            
                            # Memory usage (convert to GB)
                            memory_usage = container.get('usage', {}).get('memory', '0')
                            total_usage["ram_gb"] += self._parse_memory(memory_usage)
                            
                except Exception as e:
                    print(f"Warning: Could not get pod info for {pod_name}: {e}")
                    continue
            
            return total_usage
            
        except Exception as e:
            print(f"Warning: Could not get metrics from Kubernetes API: {e}")
            # Return empty usage if metrics API is not available
            return {
                "cpus": 0.0,
                "ram_gb": 0.0,
                "storage_gb": 0.0,
                "gpus": 0
            }
    
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

    def _configure_insecure_client(self):
        """Configure Kubernetes client to skip TLS verification for Azure VM."""
        try:
            # Create API client with insecure configuration
            configuration = client.Configuration()
            configuration.verify_ssl = False
            # Remove deprecated assert_hostname parameter
            # configuration.assert_hostname = False
            
            # Create API client with updated configuration
            self.core_v1 = client.CoreV1Api(api_client=client.ApiClient(configuration))
            self.apps_v1 = client.AppsV1Api(api_client=client.ApiClient(configuration))
            
            print("✅ Configured insecure TLS for Azure VM connection")
            
        except Exception as e:
            print(f"Warning: Could not configure insecure TLS: {e}")
            # Fall back to standard client creation
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()

    def create_pod(self, pod_data: Dict) -> Dict:
        """Create a pod in a dynamic namespace (from payload or default to 'default')."""
        self._ensure_initialized()
        try:
            pod_name = pod_data.get('PodName') or pod_data.get('pod_id')
            resources = pod_data.get('Resources') or pod_data.get('requested') or {}
            image_url = pod_data.get('image_url', 'nginx:latest')
            namespace = pod_data.get('namespace') or pod_data.get('Namespace') or 'custom-apps'

            # Create namespace if it doesn't exist
            try:
                self.core_v1.read_namespace(namespace)
            except Exception:
                ns_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
                self.core_v1.create_namespace(ns_body)

            # Define resource requirements
            resource_requirements = client.V1ResourceRequirements(
                requests={
                    'cpu': str(resources.get('cpus', 0) or 1),
                    'memory': f"{resources.get('ram_gb', 1)}Gi",
                    'ephemeral-storage': f"{resources.get('storage_gb', 1)}Gi"
                }
            )

            # Define container
            container = client.V1Container(
                name=pod_name,
                image=image_url,
                resources=resource_requirements
            )

            # Define pod spec
            pod_spec = client.V1PodSpec(containers=[container], restart_policy='Always')

            # Define pod metadata
            pod_metadata = client.V1ObjectMeta(
                name=pod_name,
                labels={
                    'app': pod_name,
                    'owner': pod_data.get('Owner', 'unknown')
                }
            )

            # Define pod
            pod = client.V1Pod(
                metadata=pod_metadata,
                spec=pod_spec
            )

            # Create pod
            self.core_v1.create_namespaced_pod(namespace=namespace, body=pod)
            return {'status': 'success', 'message': f'Pod {pod_name} created in namespace {namespace}'}
        except ApiException as e:
            return {'status': 'error', 'message': f'Kubernetes API error: {e}'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to create pod: {e}'}

    def delete_pod(self, pod_data: Dict) -> Dict:
        """Delete a pod by name in the specified or default namespace."""
        self._ensure_initialized()
        try:
            pod_name = pod_data.get('PodName') or pod_data.get('pod_id')
            namespace = pod_data.get('namespace') or pod_data.get('Namespace') or 'custom-apps'
            self.core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            return {'status': 'success', 'message': f'Pod {pod_name} deleted from namespace {namespace}'}
        except ApiException as e:
            return {'status': 'error', 'message': f'Kubernetes API error: {e}'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to delete pod: {e}'}


# Global instance for cloud Kubernetes
cloud_kubernetes_provider = CloudKubernetesProvider() 