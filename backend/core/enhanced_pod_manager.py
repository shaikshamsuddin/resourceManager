"""
Enhanced Pod Deployment Manager
Implements the required workflow:
1. Add pod to master.json with "pending" status
2. Deploy to Kubernetes server
3. Update status to "online" or "failed"
"""

import json
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from config.constants import PodStatus, DefaultValues, TimeFormats
from core.server_manager import server_manager


class EnhancedPodManager:
    """Enhanced pod deployment manager with proper status tracking."""
    
    def __init__(self):
        """Initialize the enhanced pod manager."""
        self.master_config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
        self.deployment_tracker = {}  # Track ongoing deployments
        self._load_master_config()
    
    def _load_master_config(self):
        """Load master configuration."""
        try:
            with open(self.master_config_path, 'r') as f:
                self.master_config = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load master config: {e}")
            self.master_config = {"servers": [], "config": {}}
    
    def _save_master_config(self):
        """Save master configuration."""
        try:
            with open(self.master_config_path, 'w') as f:
                json.dump(self.master_config, f, indent=2)
        except Exception as e:
            print(f"❌ Failed to save master config: {e}")
    
    def create_pod_with_status_tracking(self, server_id: str, pod_data: Dict) -> Dict:
        """
        Create pod with proper status tracking workflow:
        1. Add to master.json with "pending" status
        2. Deploy to Kubernetes
        3. Update status to "online" or "failed"
        """
        try:
            # Step 1: Validate server exists
            server_config = self._get_server_config(server_id)
            if not server_config:
                return {"error": f"Server '{server_id}' not found"}
            
            # Step 2: Generate unique pod ID and prepare pod entry
            pod_id = self._generate_pod_id(pod_data)
            pod_entry = self._create_pod_entry(pod_data, pod_id, server_id)
            
            # Step 3: Add to master.json with "pending" status
            print(f"📝 Adding pod {pod_id} to master.json with pending status")
            self._add_pod_to_master_json(server_id, pod_entry)
            
            # Step 4: Start deployment in background thread
            deployment_thread = threading.Thread(
                target=self._deploy_pod_background,
                args=(server_id, pod_id, pod_data, pod_entry),
                daemon=True
            )
            deployment_thread.start()
            
            # Step 5: Return immediate response
            return {
                "status": "pending",
                "message": f"Pod {pod_id} deployment started",
                "pod_id": pod_id,
                "deployment_id": f"{server_id}-{pod_id}"
            }
            
        except Exception as e:
            print(f"❌ Pod creation error: {e}")
            return {"error": f"Failed to create pod: {e}"}
    
    def _get_server_config(self, server_id: str) -> Optional[Dict]:
        """Get server configuration from master.json."""
        for server in self.master_config.get("servers", []):
            if server.get("id") == server_id:
                return server
        return None
    
    def _generate_pod_id(self, pod_data: Dict) -> str:
        """Generate unique pod ID."""
        import uuid
        
        # Use provided name or generate one
        base_name = pod_data.get('PodName', '')
        if not base_name:
            base_name = f"deployment-{uuid.uuid4().hex[:8]}"
        
        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{base_name}-{timestamp}"
    
    def _create_pod_entry(self, pod_data: Dict, pod_id: str, server_id: str) -> Dict:
        """Create pod entry for master.json."""
        resources = pod_data.get('Resources', {})
        namespace = pod_data.get('namespace', 'default')
        image_url = pod_data.get('image_url', DefaultValues.DEFAULT_IMAGE)
        replicas = pod_data.get('replicas', DefaultValues.DEFAULT_REPLICAS)
        
        return {
            "pod_id": pod_id,
            "name": pod_id,
            "namespace": namespace,
            "server_id": server_id,
            "image_url": image_url,
            "requested": {
                "cpus": resources.get('cpus', 0),
                "ram_gb": resources.get('ram_gb', 0),
                "storage_gb": resources.get('storage_gb', 0),
                "gpus": resources.get('gpus', 0)
            },
            "owner": pod_data.get('owner', DefaultValues.DEFAULT_OWNER),
            "status": PodStatus.PENDING.value,
            "timestamp": datetime.now().isoformat(),
            "pod_ip": None,
            "replicas": replicas,
            "deployment_status": "pending"
        }
    
    def _add_pod_to_master_json(self, server_id: str, pod_entry: Dict):
        """Add pod entry to master.json."""
        for server in self.master_config.get("servers", []):
            if server.get("id") == server_id:
                if "pods" not in server:
                    server["pods"] = []
                server["pods"].append(pod_entry)
                break
        
        self._save_master_config()
    
    def _deploy_pod_background(self, server_id: str, pod_id: str, pod_data: Dict, pod_entry: Dict):
        """Deploy pod to Kubernetes in background thread."""
        try:
            print(f"🚀 Starting deployment for pod {pod_id} on server {server_id}")
            
            # Get server provider
            provider = server_manager.get_server_provider(server_id)
            if not provider:
                self._update_pod_status(server_id, pod_id, PodStatus.FAILED.value, "Server provider not found")
                return
            
            # Deploy to Kubernetes
            result = provider.create_pod(pod_data)
            
            if result.get('status') == 'success':
                print(f"✅ Kubernetes deployment successful for {pod_id}")
                
                # Wait for pod to be ready
                self._wait_for_pod_ready(server_id, pod_id, provider, pod_data)
                
            else:
                print(f"❌ Kubernetes deployment failed for {pod_id}: {result}")
                self._update_pod_status(server_id, pod_id, PodStatus.FAILED.value, result.get('message', 'Deployment failed'))
                
        except Exception as e:
            print(f"❌ Deployment error for {pod_id}: {e}")
            self._update_pod_status(server_id, pod_id, PodStatus.FAILED.value, str(e))
    
    def _wait_for_pod_ready(self, server_id: str, pod_id: str, provider, pod_data: Dict):
        """Wait for pod to be ready and update status."""
        try:
            max_wait_time = 300  # 5 minutes
            check_interval = 10  # Check every 10 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                # Check pod status in Kubernetes
                pod_status = self._check_pod_status_in_kubernetes(provider, pod_data)
                
                if pod_status == "Running":
                    print(f"✅ Pod {pod_id} is now running")
                    self._update_pod_status(server_id, pod_id, PodStatus.ONLINE.value, "Pod is running")
                    self._update_pod_ip(server_id, pod_id, provider, pod_data)
                    return
                elif pod_status == "Failed":
                    print(f"❌ Pod {pod_id} failed")
                    self._update_pod_status(server_id, pod_id, PodStatus.FAILED.value, "Pod failed to start")
                    return
                elif pod_status == "Pending":
                    print(f"⏳ Pod {pod_id} still pending...")
                    self._update_pod_status(server_id, pod_id, PodStatus.PENDING.value, "Pod is starting up")
                
                time.sleep(check_interval)
                elapsed_time += check_interval
            
            # Timeout
            print(f"⏰ Pod {pod_id} deployment timed out")
            self._update_pod_status(server_id, pod_id, PodStatus.TIMEOUT.value, "Deployment timed out")
            
        except Exception as e:
            print(f"❌ Error waiting for pod {pod_id}: {e}")
            self._update_pod_status(server_id, pod_id, PodStatus.FAILED.value, str(e))
    
    def _check_pod_status_in_kubernetes(self, provider, pod_data: Dict) -> str:
        """Check pod status in Kubernetes."""
        try:
            if not provider.core_v1:
                return "Unknown"
            
            namespace = pod_data.get('namespace', 'default')
            deployment_name = pod_data.get('PodName', '')
            
            # Get pods from deployment
            pods = provider.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_name}"
            )
            
            if not pods.items:
                return "Pending"
            
            # Check all pods in deployment
            running_count = 0
            failed_count = 0
            
            for pod in pods.items:
                phase = pod.status.phase
                if phase == "Running":
                    running_count += 1
                elif phase == "Failed":
                    failed_count += 1
            
            if failed_count > 0:
                return "Failed"
            elif running_count == len(pods.items):
                return "Running"
            else:
                return "Pending"
                
        except Exception as e:
            print(f"Error checking pod status: {e}")
            return "Unknown"
    
    def _update_pod_status(self, server_id: str, pod_id: str, status: str, message: str = ""):
        """Update pod status in master.json."""
        try:
            self._load_master_config()  # Reload to get latest data
            
            for server in self.master_config.get("servers", []):
                if server.get("id") == server_id:
                    for pod in server.get("pods", []):
                        if pod.get("pod_id") == pod_id:
                            pod["status"] = status
                            pod["deployment_status"] = status
                            if message:
                                pod["deployment_message"] = message
                            pod["last_updated"] = datetime.now().isoformat()
                            break
                    break
            
            self._save_master_config()
            print(f"📝 Updated pod {pod_id} status to {status}")
            
        except Exception as e:
            print(f"❌ Failed to update pod status: {e}")
    
    def _update_pod_ip(self, server_id: str, pod_id: str, provider, pod_data: Dict):
        """Update pod IP in master.json."""
        try:
            if not provider.core_v1:
                return
            
            namespace = pod_data.get('namespace', 'default')
            deployment_name = pod_data.get('PodName', '')
            
            # Get pod IP
            pods = provider.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_name}"
            )
            
            if pods.items:
                pod_ip = pods.items[0].status.pod_ip
                if pod_ip:
                    self._load_master_config()
                    
                    for server in self.master_config.get("servers", []):
                        if server.get("id") == server_id:
                            for pod in server.get("pods", []):
                                if pod.get("pod_id") == pod_id:
                                    pod["pod_ip"] = pod_ip
                                    break
                            break
                    
                    self._save_master_config()
                    print(f"📝 Updated pod {pod_id} IP to {pod_ip}")
                    
        except Exception as e:
            print(f"❌ Failed to update pod IP: {e}")
    
    def get_deployment_status(self, server_id: str, pod_id: str) -> Dict:
        """Get deployment status for a specific pod."""
        try:
            self._load_master_config()
            
            for server in self.master_config.get("servers", []):
                if server.get("id") == server_id:
                    for pod in server.get("pods", []):
                        if pod.get("pod_id") == pod_id:
                            return {
                                "pod_id": pod_id,
                                "status": pod.get("status", "unknown"),
                                "deployment_status": pod.get("deployment_status", "unknown"),
                                "message": pod.get("deployment_message", ""),
                                "timestamp": pod.get("timestamp", ""),
                                "last_updated": pod.get("last_updated", "")
                            }
            
            return {"error": f"Pod {pod_id} not found"}
            
        except Exception as e:
            return {"error": f"Failed to get deployment status: {e}"}


# Global instance
enhanced_pod_manager = EnhancedPodManager() 