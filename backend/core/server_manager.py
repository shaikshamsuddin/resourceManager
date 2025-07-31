"""
Server Manager Module
Handles server and pod management operations.
"""

import warnings
# Suppress SSL/TLS warnings for development environments
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', category=Warning, module='urllib3')

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
        
        print(f"📊 Total providers initialized: {len(self.server_providers)}")
        print(f"📊 Provider IDs: {list(self.server_providers.keys())}")
    
    def _create_provider(self, server_config: Dict):
        """Create appropriate provider based on server type and connection method."""
        server_type = server_config.get("type")
        connection_coords = server_config.get("connection_coordinates", {})
        connection_method = connection_coords.get("method")
        server_id = server_config.get('id', 'unknown')
        
        print(f"🔧 Creating provider for server {server_id}:")
        print(f"   - Type: {server_type}")
        print(f"   - Connection method: {connection_method}")
        print(f"   - Host: {connection_coords.get('host')}")
        
        if server_type == "kubernetes":
            # Use CloudKubernetesProvider for Azure VM or cloud connections
            if connection_method == "kubeconfig" and connection_coords.get("host"):
                print(f"✅ Using CloudKubernetesProvider for {server_id} with kubeconfig")
                try:
                    provider = CloudKubernetesProvider(server_config)
                    print(f"✅ CloudKubernetesProvider created successfully for {server_id}")
                    return provider
                except Exception as e:
                    print(f"❌ Failed to create CloudKubernetesProvider for {server_id}: {e}")
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
    
    def get_all_servers_static(self) -> List[Dict]:
        """
        Get all servers and pods from master.json only (no live sync).
        This method is optimized for fast API responses.
        
        Returns:
            List of servers with their data from master.json
        """
        all_servers = []
        
        # Read directly from master.json without any provider initialization
        for server_config in self.master_config.get("servers", []):
            server_id = server_config.get("id")
            server_name = server_config.get("name", server_id)
            server_type = server_config.get("type", "unknown")
            environment = server_config.get("environment", "unknown")
            metadata = server_config.get("metadata", {})
            
            # Create server object from master.json data only
            server_data = {
                "id": server_id,  # Add id field for frontend compatibility
                "server_id": server_id,
                "name": server_name,  # Add name field for frontend compatibility
                "server_name": server_name,
                "server_type": server_type,
                "metadata": metadata,
                "environment": environment,
                "status": server_config.get("status", "offline"),
                "pods": server_config.get("pods", []),
                "resources": server_config.get("resources", {
                    "total": {}, 
                    "allocated": {}, 
                    "available": {}, 
                    "actual_usage": {}
                })
            }
            
            all_servers.append(server_data)
        
        return all_servers

    def get_all_servers_with_pods(self) -> List[Dict]:
        """Get all servers with their pods data."""
        all_servers = []
        
        # Get all servers from master config, not just those with providers
        for server_config in self.master_config.get("servers", []):
            server_id = server_config.get("id")
            server_name = server_config.get("name", server_id)
            server_type = server_config.get("type", "unknown")
            environment = server_config.get("environment", "unknown")
            metadata = server_config.get("metadata", {})
            
            # Check if we have a provider for this server
            if server_id in self.server_providers:
                try:
                    provider = self.server_providers[server_id]["provider"]
                    
                    # Get live data from provider
                    servers_data = provider.get_servers_with_pods()
                    
                    # Add server metadata
                    for server_data in servers_data:
                        server_data["server_id"] = server_id
                        server_data["server_name"] = server_name
                        server_data["server_type"] = server_type
                        server_data["metadata"] = metadata
                        server_data["environment"] = environment
                    
                    all_servers.extend(servers_data)
                    
                except Exception as e:
                    print(f"Error getting live data for server {server_id}: {e}")
                    # Add server with error state but include static data
                    error_server = {
                        "server_id": server_id,
                        "server_name": server_name,
                        "server_type": server_type,
                        "metadata": metadata,
                        "environment": environment,
                        "status": "error",
                        "pods": server_config.get("pods", []),
                        "resources": server_config.get("resources", {"total": {}, "allocated": {}, "available": {}, "actual_usage": {}})
                    }
                    all_servers.append(error_server)
            else:
                # Server doesn't have a provider (like dummy servers), use static data
                static_server = {
                    "server_id": server_id,
                    "server_name": server_name,
                    "server_type": server_type,
                    "metadata": metadata,
                    "environment": environment,
                    "status": "offline",  # or "static" to indicate it's not live
                    "pods": server_config.get("pods", []),
                    "resources": server_config.get("resources", {"total": {}, "allocated": {}, "available": {}, "actual_usage": {}})
                }
                all_servers.append(static_server)
        
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
        print(f"🔧 Creating pod on server: {server_id}")
        
        # OPTIMIZATION: Only reload config if provider doesn't exist
        if server_id not in self.server_providers:
            print(f"🔧 Reloading config for server: {server_id}")
            self.reload_config()
            if server_id not in self.server_providers:
                error_msg = f"Server {server_id} not found"
                print(f"❌ {error_msg}")
                return {"error": error_msg}
        
        try:
            provider = self.server_providers[server_id]["provider"]
            print(f"🔧 Using provider for server: {server_id}")
            result = provider.create_pod(pod_data)
            
            # OPTIMIZATION: Sync pods synchronously after successful creation
            if result.get('status') == 'success':
                try:
                    # Add a small delay to allow pod to start transitioning from Pending to Running
                    import time
                    time.sleep(2)
                    print(f"🔄 Syncing pods from Kubernetes for server: {server_id}")
                    self.sync_pods_from_kubernetes(server_id)
                except Exception as e:
                    print(f"⚠️  Sync failed but pod was created: {e}")
            
            return result
        except Exception as e:
            error_msg = f"Failed to create pod: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}

    def delete_pod(self, server_id: str, pod_name: str, pod_data: Dict = None) -> Dict:
        """Delete a pod from the specified server and update master.json only if successful."""
        print(f"🗑️  ServerManager: Deleting pod {pod_name} from server {server_id}")
        
        self.reload_config()
        if server_id not in self.server_providers:
            error_msg = f"Server {server_id} not found"
            print(f"❌ ServerManager: {error_msg}")
            return {"error": error_msg}
        
        try:
            # Find the pod in master.json to get its namespace
            pod_namespace = None
            for server in self.master_config.get('servers', []):
                if server.get('id') == server_id:
                    for pod in server.get('pods', []):
                        if pod.get('pod_id') == pod_name or pod.get('name') == pod_name:
                            pod_namespace = pod.get('namespace', 'default')
                            print(f"✅ ServerManager: Found pod {pod_name} in namespace {pod_namespace}")
                            break
                    break
            
            if not pod_namespace:
                print(f"⚠️  ServerManager: Pod {pod_name} not found in master.json, using default namespace")
                pod_namespace = 'default'
            
            provider = self.server_providers[server_id]["provider"]
            # Pass pod_data with namespace information
            pod_data = pod_data or {"PodName": pod_name, "namespace": pod_namespace}
            print(f"🔧 ServerManager: Calling provider delete_pod with data: {pod_data}")
            
            result = provider.delete_pod(pod_data)
            print(f"📊 ServerManager: Provider delete result: {result}")
            
            if result.get('status') == 'success':
                print(f"🔄 ServerManager: Pod deletion successful, syncing pods from Kubernetes")
                # Sync pods from Kubernetes to update master.json with fresh data
                try:
                    import time
                    time.sleep(2)  # Small delay to allow deletion to complete
                    sync_result = self.sync_pods_from_kubernetes(server_id)
                    print(f"📊 ServerManager: Sync result: {sync_result}")
                except Exception as e:
                    print(f"⚠️  ServerManager: Sync failed but pod was deleted: {e}")
                    # Fallback: manually remove from master.json
                    self.master_config = self._load_master_config()
                    for server in self.master_config.get('servers', []):
                        if server.get('id') == server_id:
                            original_count = len(server.get('pods', []))
                            server['pods'] = [p for p in server.get('pods', []) if p.get('pod_id') != pod_name and p.get('name') != pod_name]
                            new_count = len(server.get('pods', []))
                            print(f"📝 ServerManager: Removed {original_count - new_count} pods from master.json")
                    config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
                    with open(config_path, 'w') as f:
                        json.dump(self.master_config, f, indent=2)
            else:
                print(f"❌ ServerManager: Pod deletion failed: {result}")
            
            return result
        except Exception as e:
            error_msg = f"Failed to delete pod: {e}"
            print(f"❌ ServerManager: Exception during pod deletion: {e}")
            return {"error": error_msg}
    

    
    def reload_config(self):
        """Reload the master configuration."""
        print("🔄 Reloading server configuration...")
        self.master_config = self._load_master_config()
        self.server_providers = {}
        self._initialize_providers()
        print("✅ Server configuration reloaded successfully")

    def sync_pods_from_kubernetes(self, server_id: str) -> Dict:
        """Fetch live pod data from the provider and update the pods field in master.json for the given server."""
        if server_id not in self.server_providers:
            error_msg = f"Server {server_id} not found"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
        try:
            print(f"🔄 Syncing pods from Kubernetes for server: {server_id}")
            provider = self.server_providers[server_id]["provider"]
            # Fetch live pods from provider
            servers_data = provider.get_servers_with_pods()
            
            # Flatten all pods from all nodes (if node-based)
            live_pods = []
            for node in servers_data:
                if "pods" in node:
                    for pod in node["pods"]:
                        live_pods.append(pod)
            
            print(f"📊 Found {len(live_pods)} pods from Kubernetes")
            
            # Update master.json
            self.master_config = self._load_master_config()
            for server in self.master_config.get("servers", []):
                if server.get("id") == server_id:
                    server["pods"] = live_pods
            
            # Write back to master.json
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'w') as f:
                json.dump(self.master_config, f, indent=2)
            
            print(f"✅ Successfully synced {len(live_pods)} pods to master.json")
            return {"status": "success", "pods": live_pods}
        except Exception as e:
            error_msg = f"Failed to sync pods: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}

    def ensure_all_servers_connected(self):
        """Ensure all servers in master.json are properly connected and managed."""
        print("🔧 Ensuring all servers in master.json are connected...")
        
        # Reload configuration
        self.reload_config()
        
        # Get all servers from master.json
        all_servers = self.master_config.get("servers", [])
        connected_count = 0
        failed_count = 0
        
        for server in all_servers:
            server_id = server.get("id")
            if not server_id:
                continue
                
            try:
                # Check if server has a provider
                if server_id not in self.server_providers:
                    print(f"🔧 Creating provider for server: {server_id}")
                    provider = self._create_provider(server)
                    if provider:
                        self.server_providers[server_id] = {
                            "provider": provider,
                            "config": server
                        }
                        connected_count += 1
                        print(f"✅ Connected server: {server_id}")
                    else:
                        failed_count += 1
                        print(f"❌ Failed to connect server: {server_id}")
                else:
                    # Test existing provider connection
                    provider = self.server_providers[server_id]["provider"]
                    try:
                        # Test connection by getting server data
                        servers_data = provider.get_servers_with_pods()
                        if servers_data:
                            connected_count += 1
                            print(f"✅ Server {server_id} connection verified")
                        else:
                            failed_count += 1
                            print(f"❌ Server {server_id} connection failed")
                    except Exception as e:
                        failed_count += 1
                        print(f"❌ Server {server_id} connection error: {e}")
                        
            except Exception as e:
                failed_count += 1
                print(f"❌ Error processing server {server_id}: {e}")
        
        print(f"📊 Server connection summary: {connected_count} connected, {failed_count} failed")
        return {
            "connected": connected_count,
            "failed": failed_count,
            "total": len(all_servers)
        }

    def get_server_connection_status(self) -> Dict:
        """Get connection status for all servers."""
        status = {}
        
        for server_id, provider_info in self.server_providers.items():
            try:
                provider = provider_info["provider"]
                # Test connection
                servers_data = provider.get_servers_with_pods()
                status[server_id] = {
                    "connected": True,
                    "status": "online" if servers_data else "offline",
                    "last_check": datetime.now().isoformat()
                }
            except Exception as e:
                status[server_id] = {
                    "connected": False,
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
        
        return status


# Create a global instance
server_manager = ServerManager() 