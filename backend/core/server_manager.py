"""
Server Manager Module
Handles server and pod management operations.
"""

import os
import json
from typing import Dict, List, Optional
from kubernetes import client, config
from providers.cloud_kubernetes_provider import CloudKubernetesProvider
from config.types import MasterConfig, ServerConfig


class ServerManager:
    """Manages server configurations and Kubernetes providers."""
    
    def __init__(self):
        """Initialize the server manager."""
        self.master_config = self._load_master_config()
        self.server_providers = {}
        self._initialize_providers()
    
    def _load_master_config(self) -> MasterConfig:
        """Load master configuration from data/master.json."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                from config.types import validate_master_config
                return validate_master_config(config_data)
        except Exception as e:
            print(f"❌ Failed to load master config: {e}")
            from config.types import create_default_master_config
            return create_default_master_config()
    
    def _initialize_providers(self):
        """Initialize providers for all configured servers."""
        print(f"🔧 Initializing providers for {len(self.master_config.get('servers', []))} servers")
        
        for server in self.master_config.get("servers", []):
            server_id = server.get("id")
            print(f"🔧 Processing server: {server_id}")
            
            if server_id:
                try:
                    provider = self._create_provider(server)
                    if provider:
                        self.server_providers[server_id] = {
                            "provider": provider,
                            "config": server
                        }
                        print(f"✅ Created provider for server: {server_id}")
                    else:
                        print(f"⚠️  No provider created for server: {server_id}")
                except Exception as e:
                    print(f"❌ Failed to create provider for {server_id}: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"🔧 Total providers initialized: {len(self.server_providers)}")
        print(f"🔧 Provider IDs: {list(self.server_providers.keys())}")
    
    def _create_provider(self, server_config: Dict):
        """Create appropriate provider based on server type and connection method."""
        server_type = server_config.get("type")
        connection_coords = server_config.get("connection_coordinates", {})
        connection_method = connection_coords.get("method")
        
        print(f"🔧 Creating provider for server {server_config.get('id')}:")
        print(f"   - Type: {server_type}")
        print(f"   - Connection method: {connection_method}")
        print(f"   - Host: {connection_coords.get('host')}")
        
        if server_type == "kubernetes":
            # Use CloudKubernetesProvider for Azure VM or cloud connections
            if connection_method == "kubeconfig" and connection_coords.get("host"):
                print(f"✅ Using CloudKubernetesProvider for {server_config.get('id')} with kubeconfig")
                try:
                    provider = CloudKubernetesProvider(server_config)
                    print(f"✅ CloudKubernetesProvider created successfully")
                    return provider
                except Exception as e:
                    print(f"❌ Failed to create CloudKubernetesProvider: {e}")
                    return None
            else:
                # No local provider support - only cloud/remote connections
                print(f"❌ Unsupported connection method: {connection_method}")
                print(f"   Only 'kubeconfig' with host is supported for Azure VM connections")
                return None
        else:
            print(f"❌ Unknown server type: {server_type}")
            return None
    
    def get_server_ids(self) -> List[str]:
        """Get list of all server IDs."""
        return list(self.server_providers.keys())
    
    def get_server_config(self, server_id: str) -> Optional[Dict]:
        """Get configuration for a specific server."""
        if server_id in self.server_providers:
            return self.server_providers[server_id]["config"]
        return None
    
    def get_server_provider(self, server_id: str):
        """Get provider instance for a specific server."""
        if server_id in self.server_providers:
            return self.server_providers[server_id]["provider"]
        return None
    
    def get_all_servers_with_pods(self) -> List[Dict]:
        """Get all servers with their pods data."""
        all_servers = []
        
        for server_id, server_info in self.server_providers.items():
            try:
                provider = server_info["provider"]
                config = server_info["config"]
                
                # Get live data from provider
                servers_data = provider.get_servers_with_pods()
                
                # Add server metadata
                for server_data in servers_data:
                    server_data["server_id"] = server_id
                    server_data["server_name"] = config.get("name", server_id)
                    server_data["server_type"] = config.get("type", "unknown")
                    server_data["metadata"] = config.get("metadata", {})
                    server_data["environment"] = config.get("environment", "unknown")
                
                all_servers.extend(servers_data)
                
            except Exception as e:
                print(f"Error getting data for server {server_id}: {e}")
                # Add server with error state
                error_server = {
                    "server_id": server_id,
                    "server_name": config.get("name", server_id),
                    "server_type": config.get("type", "unknown"),
                    "metadata": config.get("metadata", {}),
                    "environment": config.get("environment", "unknown"),
                    "status": "error",
                    "pods": [],
                    "resources": {"total": {}, "allocated": {}, "available": {}}
                }
                all_servers.append(error_server)
        
        return all_servers
    
    def get_server_with_pods(self, server_id: str) -> Optional[Dict]:
        """Get specific server with its pods data."""
        if server_id not in self.server_providers:
            return None
        
        try:
            provider = self.server_providers[server_id]["provider"]
            config = self.server_providers[server_id]["config"]
            
            servers_data = provider.get_servers_with_pods()
            
            if servers_data:
                server_data = servers_data[0]  # Get first server
                server_data["server_id"] = server_id
                server_data["server_name"] = config.get("name", server_id)
                server_data["server_type"] = config.get("type", "unknown")
                server_data["metadata"] = config.get("metadata", {})
                server_data["environment"] = config.get("environment", "unknown")
                return server_data
            
        except Exception as e:
            print(f"Error getting data for server {server_id}: {e}")
        
        return None
    
    def create_pod(self, server_id: str, pod_data: Dict) -> Dict:
        """Create a pod on the specified server."""
        self.reload_config()  # Always reload config before operation
        if server_id not in self.server_providers:
            return {"error": f"Server {server_id} not found"}
        try:
            provider = self.server_providers[server_id]["provider"]
            result = provider.create_pod(pod_data)
            # Optionally, after creation, reload pods from Kubernetes and update master.json
            self.sync_pods_from_kubernetes(server_id)
            return result
        except Exception as e:
            return {"error": f"Failed to create pod: {e}"}

    def delete_pod(self, server_id: str, pod_name: str, pod_data: Dict = None) -> Dict:
        """Delete a pod from the specified server and update master.json only if successful."""
        self.reload_config()
        if server_id not in self.server_providers:
            return {"error": f"Server {server_id} not found"}
        try:
            provider = self.server_providers[server_id]["provider"]
            # Pass pod_data for namespace support
            pod_data = pod_data or {"PodName": pod_name}
            result = provider.delete_pod(pod_data)
            if result.get('status') == 'success':
                # Remove pod from master.json
                self.master_config = self._load_master_config()
                for server in self.master_config.get('servers', []):
                    if server.get('id') == server_id:
                        server['pods'] = [p for p in server.get('pods', []) if p.get('pod_id') != pod_name and p.get('name') != pod_name]
                config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
                with open(config_path, 'w') as f:
                    json.dump(self.master_config, f, indent=2)
            return result
        except Exception as e:
            return {"error": f"Failed to delete pod: {e}"}
    
    def update_pod(self, server_id: str, pod_data: Dict) -> Dict:
        """Update a pod on the specified server and in master.json."""
        self.reload_config()  # Always reload config before operation
        if server_id not in self.server_providers:
            return {"error": f"Server {server_id} not found"}
        try:
            provider = self.server_providers[server_id]["provider"]
            result = provider.update_pod(pod_data)
            # After updating in Kubernetes, update master.json
            pod_name = pod_data.get('PodName') or pod_data.get('pod_id')
            # Reload master config
            self.master_config = self._load_master_config()
            for server in self.master_config.get('servers', []):
                if server.get('id') == server_id:
                    for pod in server.get('pods', []):
                        if pod.get('pod_id') == pod_name or pod.get('name') == pod_name:
                            # Update resource fields
                            resources = pod_data.get('Resources') or pod_data.get('requested') or {}
                            pod['requested'] = resources
                            pod['status'] = pod_data.get('status', pod.get('status', 'online'))
                            pod['image_url'] = pod_data.get('image_url', pod.get('image_url', ''))
                            pod['owner'] = pod_data.get('Owner', pod.get('owner', ''))
            # Save updated master.json
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'w') as f:
                json.dump(self.master_config, f, indent=2)
            return result
        except Exception as e:
            return {"error": f"Failed to update pod: {e}"}
    
    def reload_config(self):
        """Reload the master configuration."""
        self.master_config = self._load_master_config()
        self.server_providers = {}
        self._initialize_providers()

    def sync_pods_from_kubernetes(self, server_id: str) -> Dict:
        """Fetch live pod data from the provider and update the pods field in master.json for the given server."""
        if server_id not in self.server_providers:
            return {"error": f"Server {server_id} not found"}
        try:
            provider = self.server_providers[server_id]["provider"]
            # Fetch live pods from provider
            servers_data = provider.get_servers_with_pods()
            # Flatten all pods from all nodes (if node-based)
            live_pods = []
            for node in servers_data:
                if "pods" in node:
                    for pod in node["pods"]:
                        live_pods.append(pod)
            # Update master.json
            self.master_config = self._load_master_config()
            for server in self.master_config.get("servers", []):
                if server.get("id") == server_id:
                    server["pods"] = live_pods
            # Write back to master.json
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'w') as f:
                json.dump(self.master_config, f, indent=2)
            return {"status": "success", "pods": live_pods}
        except Exception as e:
            return {"error": f"Failed to sync pods: {e}"}


# Create a global instance
server_manager = ServerManager() 