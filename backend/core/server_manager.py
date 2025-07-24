"""
Server Manager Module
Handles server and pod management operations.
"""

import os
import json
from typing import Dict, List, Optional
from kubernetes import client, config
from providers.cloud_kubernetes_provider import CloudKubernetesProvider
from providers.kubernetes_provider import LocalKubernetesProvider


class ServerManager:
    """Manages server configurations and Kubernetes providers."""
    
    def __init__(self):
        """Initialize the server manager."""
        self.master_config = self._load_master_config()
        self.server_providers = {}
        self._initialize_providers()
    
    def _load_master_config(self) -> Dict:
        """Load master configuration from data/master.json."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load master config: {e}")
            return {"servers": []}
    
    def _initialize_providers(self):
        """Initialize providers for all configured servers."""
        for server in self.master_config.get("servers", []):
            server_id = server.get("id")
            if server_id:
                try:
                    provider = self._create_provider(server)
                    if provider:
                        self.server_providers[server_id] = {
                            "provider": provider,
                            "config": server
                        }
                        print(f"✅ Created provider for server: {server_id} (lazy initialization)")
                    else:
                        print(f"⚠️  No provider created for server: {server_id}")
                except Exception as e:
                    print(f"❌ Failed to create provider for {server_id}: {e}")
                    import traceback
                    traceback.print_exc()
    
    def _create_provider(self, server_config: Dict):
        """Create appropriate provider based on server type and connection method."""
        server_type = server_config.get("type")
        connection_coords = server_config.get("connection_coordinates", {})
        connection_method = connection_coords.get("method")
        
        if server_type == "kubernetes":
            # Use CloudKubernetesProvider for Azure VM or cloud connections
            if connection_method == "kubeconfig" and connection_coords.get("host"):
                print(f"Using CloudKubernetesProvider for {server_config.get('id')} with kubeconfig")
                return CloudKubernetesProvider(server_config)
            else:
                # Use LocalKubernetesProvider for local connections
                print(f"Using LocalKubernetesProvider for {server_config.get('id')}")
                return LocalKubernetesProvider()
        else:
            print(f"Unknown server type: {server_type}")
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
        if server_id not in self.server_providers:
            return {"error": f"Server {server_id} not found"}
        
        try:
            provider = self.server_providers[server_id]["provider"]
            return provider.create_pod(pod_data)
        except Exception as e:
            return {"error": f"Failed to create pod: {e}"}
    
    def delete_pod(self, server_id: str, pod_name: str) -> Dict:
        """Delete a pod from the specified server."""
        if server_id not in self.server_providers:
            return {"error": f"Server {server_id} not found"}
        
        try:
            provider = self.server_providers[server_id]["provider"]
            return provider.delete_pod(pod_name)
        except Exception as e:
            return {"error": f"Failed to delete pod: {e}"}
    
    def update_pod(self, server_id: str, pod_data: Dict) -> Dict:
        """Update a pod on the specified server."""
        if server_id not in self.server_providers:
            return {"error": f"Server {server_id} not found"}
        
        try:
            provider = self.server_providers[server_id]["provider"]
            return provider.update_pod(pod_data)
        except Exception as e:
            return {"error": f"Failed to update pod: {e}"}
    
    def get_default_server_id(self) -> str:
        """Get the default server ID."""
        server_ids = self.get_server_ids()
        return server_ids[0] if server_ids else ""
    
    def reload_config(self):
        """Reload the master configuration."""
        self.master_config = self._load_master_config()
        self.server_providers = {}
        self._initialize_providers()


# Create a global instance
server_manager = ServerManager() 