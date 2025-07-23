"""
Server Manager
Handles loading and managing server configurations from master.json
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path

from constants import ErrorMessages
from providers.kubernetes_provider import KubernetesProvider
from providers.demo_data_provider import demo_data_provider


class ServerManager:
    """Manages server configurations and connections."""
    
    def __init__(self):
        """Initialize server manager."""
        self.master_config = self._load_master_config()
        self.server_providers = {}
        self._initialize_providers()
    
    def _load_master_config(self) -> Dict:
        """Load master configuration from JSON file."""
        try:
            config_path = Path(__file__).parent / "data" / "master.json"
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: master.json not found at {config_path}")
            return {"servers": [], "config": {}}
        except json.JSONDecodeError as e:
            print(f"Error parsing master.json: {e}")
            return {"servers": [], "config": {}}
    
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
                        print(f"✅ Initialized provider for server: {server_id}")
                except Exception as e:
                    print(f"❌ Failed to initialize provider for {server_id}: {e}")
    
    def _create_provider(self, server_config: Dict):
        """Create appropriate provider based on server type."""
        server_type = server_config.get("type")
        
        if server_type == "kubernetes":
            return KubernetesProvider(server_config.get("connection_coordinates", {}))
        elif server_type == "mock":
            return demo_data_provider
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
    
    def get_all_servers_with_pods(self, environment: str = None) -> List[Dict]:
        """Get all servers with their pods data, optionally filtered by environment."""
        all_servers = []
        
        for server_id, server_info in self.server_providers.items():
            try:
                provider = server_info["provider"]
                config = server_info["config"]
                
                # Filter by environment if specified
                if environment and config.get("environment") != environment:
                    continue
                
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
            
            # Add server metadata
            for server_data in servers_data:
                server_data["server_id"] = server_id
                server_data["server_name"] = config.get("name", server_id)
                server_data["server_type"] = config.get("type", "unknown")
                server_data["metadata"] = config.get("metadata", {})
            
            return servers_data[0] if servers_data else None
            
        except Exception as e:
            print(f"Error getting data for server {server_id}: {e}")
            return {
                "server_id": server_id,
                "server_name": config.get("name", server_id),
                "server_type": config.get("type", "unknown"),
                "status": "error",
                "error": str(e),
                "pods": []
            }
    
    def create_pod(self, server_id: str, pod_data: Dict) -> Dict:
        """Create a pod on a specific server."""
        provider = self.get_server_provider(server_id)
        if not provider:
            return {"error": f"Server {server_id} not found"}
        
        try:
            return provider.create_pod(pod_data)
        except Exception as e:
            return {"error": f"Failed to create pod: {str(e)}"}
    
    def delete_pod(self, server_id: str, pod_name: str) -> Dict:
        """Delete a pod from a specific server."""
        provider = self.get_server_provider(server_id)
        if not provider:
            return {"error": f"Server {server_id} not found"}
        
        try:
            return provider.delete_pod(pod_name)
        except Exception as e:
            return {"error": f"Failed to delete pod: {str(e)}"}
    
    def update_pod(self, server_id: str, pod_data: Dict) -> Dict:
        """Update a pod on a specific server."""
        provider = self.get_server_provider(server_id)
        if not provider:
            return {"error": f"Server {server_id} not found"}
        
        try:
            return provider.update_pod(pod_data)
        except Exception as e:
            return {"error": f"Failed to update pod: {str(e)}"}
    
    def get_default_server_id(self) -> str:
        """Get the default server ID from configuration."""
        return self.master_config.get("config", {}).get("default_server", "")
    
    def reload_config(self):
        """Reload the master configuration."""
        self.master_config = self._load_master_config()
        self.server_providers = {}
        self._initialize_providers()


# Global server manager instance
server_manager = ServerManager() 