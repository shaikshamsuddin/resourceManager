"""
Demo Data Provider
Provides realistic mock data for demo servers in demo mode.
"""

import random
from typing import Dict, List
from datetime import datetime, timedelta


class DemoDataProvider:
    """Provides demo data for demonstration purposes."""
    
    def __init__(self):
        """Initialize demo data provider."""
        self.demo_servers = {
            "demo-server-01": {
                "name": "Demo Server Alpha",
                "ip": "192.168.1.100",
                "status": "Online",
                "resources": {
                    "total": {"cpus": 8, "ram_gb": 32, "gpus": 2, "storage_gb": 500},
                    "allocated": {"cpus": 4, "ram_gb": 16, "gpus": 1, "storage_gb": 200},
                    "available": {"cpus": 4, "ram_gb": 16, "gpus": 1, "storage_gb": 300}
                },
                "pods": [
                    {
                        "pod_id": "demo-web-app-01",
                        "serverName": "Demo Server Alpha",
                        "status": "Running",
                        "requested": {"cpus": 2, "ram_gb": 4, "gpus": 0, "storage_gb": 50},
                        "owner": "demo-user",
                        "image": "nginx:latest",
                        "created_at": (datetime.now() - timedelta(hours=2)).isoformat()
                    },
                    {
                        "pod_id": "demo-api-service-01",
                        "serverName": "Demo Server Alpha", 
                        "status": "Running",
                        "requested": {"cpus": 1, "ram_gb": 2, "gpus": 0, "storage_gb": 30},
                        "owner": "demo-user",
                        "image": "node:16-alpine",
                        "created_at": (datetime.now() - timedelta(hours=1)).isoformat()
                    },
                    {
                        "pod_id": "demo-ml-training-01",
                        "serverName": "Demo Server Alpha",
                        "status": "Running", 
                        "requested": {"cpus": 1, "ram_gb": 8, "gpus": 1, "storage_gb": 100},
                        "owner": "ml-team",
                        "image": "tensorflow/tensorflow:latest-gpu",
                        "created_at": (datetime.now() - timedelta(minutes=30)).isoformat()
                    }
                ]
            },
            "demo-server-02": {
                "name": "Demo Server Beta",
                "ip": "192.168.1.101", 
                "status": "Online",
                "resources": {
                    "total": {"cpus": 16, "ram_gb": 64, "gpus": 4, "storage_gb": 1000},
                    "allocated": {"cpus": 8, "ram_gb": 32, "gpus": 2, "storage_gb": 400},
                    "available": {"cpus": 8, "ram_gb": 32, "gpus": 2, "storage_gb": 600}
                },
                "pods": [
                    {
                        "pod_id": "demo-database-01",
                        "serverName": "Demo Server Beta",
                        "status": "Running",
                        "requested": {"cpus": 4, "ram_gb": 16, "gpus": 0, "storage_gb": 200},
                        "owner": "db-team",
                        "image": "postgres:13",
                        "created_at": (datetime.now() - timedelta(hours=4)).isoformat()
                    },
                    {
                        "pod_id": "demo-cache-service-01",
                        "serverName": "Demo Server Beta",
                        "status": "Running",
                        "requested": {"cpus": 2, "ram_gb": 8, "gpus": 0, "storage_gb": 50},
                        "owner": "cache-team", 
                        "image": "redis:6-alpine",
                        "created_at": (datetime.now() - timedelta(hours=3)).isoformat()
                    },
                    {
                        "pod_id": "demo-monitoring-01",
                        "serverName": "Demo Server Beta",
                        "status": "Running",
                        "requested": {"cpus": 1, "ram_gb": 4, "gpus": 0, "storage_gb": 100},
                        "owner": "ops-team",
                        "image": "prom/prometheus:latest",
                        "created_at": (datetime.now() - timedelta(hours=2)).isoformat()
                    },
                    {
                        "pod_id": "demo-gpu-inference-01",
                        "serverName": "Demo Server Beta",
                        "status": "Running",
                        "requested": {"cpus": 1, "ram_gb": 4, "gpus": 2, "storage_gb": 50},
                        "owner": "ai-team",
                        "image": "pytorch/pytorch:latest",
                        "created_at": (datetime.now() - timedelta(minutes=45)).isoformat()
                    }
                ]
            }
        }
    
    def get_servers_with_pods(self) -> List[Dict]:
        """Get all demo servers with their pods."""
        servers = []
        
        for server_id, server_data in self.demo_servers.items():
            server = {
                "id": server_id,
                "name": server_data["name"],
                "ip": server_data["ip"],
                "status": server_data["status"],
                "resources": server_data["resources"],
                "pods": server_data["pods"]
            }
            servers.append(server)
        
        return servers
    
    def create_pod(self, pod_data: Dict) -> Dict:
        """Create a demo pod."""
        pod_name = pod_data.get("PodName")
        server_id = pod_data.get("server_id")
        
        if not pod_name or not server_id:
            return {"error": "PodName and server_id are required"}
        
        if server_id not in self.demo_servers:
            return {"error": f"Server {server_id} not found"}
        
        # Check if pod already exists
        existing_pods = self.demo_servers[server_id]["pods"]
        if any(pod["pod_id"] == pod_name for pod in existing_pods):
            return {"error": f"Pod {pod_name} already exists"}
        
        # Create new pod
        new_pod = {
            "pod_id": pod_name,
            "serverName": self.demo_servers[server_id]["name"],
            "status": "Running",
            "requested": pod_data.get("Resources", {"cpus": 1, "ram_gb": 1, "gpus": 0, "storage_gb": 10}),
            "owner": pod_data.get("Owner", "demo-user"),
            "image": pod_data.get("ImageUrl", "nginx:latest"),
            "created_at": datetime.now().isoformat()
        }
        
        self.demo_servers[server_id]["pods"].append(new_pod)
        
        return {"message": f"Pod {pod_name} created successfully", "pod": new_pod}
    
    def delete_pod(self, pod_data: Dict) -> Dict:
        """Delete a demo pod."""
        pod_name = pod_data.get("PodName")
        server_id = pod_data.get("server_id")
        
        if not pod_name or not server_id:
            return {"error": "PodName and server_id are required"}
        
        if server_id not in self.demo_servers:
            return {"error": f"Server {server_id} not found"}
        
        # Find and remove pod
        pods = self.demo_servers[server_id]["pods"]
        for i, pod in enumerate(pods):
            if pod["pod_id"] == pod_name:
                deleted_pod = pods.pop(i)
                return {"message": f"Pod {pod_name} deleted successfully", "pod": deleted_pod}
        
        return {"error": f"Pod {pod_name} not found"}
    
    def update_pod(self, pod_data: Dict) -> Dict:
        """Update a demo pod."""
        pod_name = pod_data.get("PodName")
        server_id = pod_data.get("server_id")
        
        if not pod_name or not server_id:
            return {"error": "PodName and server_id are required"}
        
        if server_id not in self.demo_servers:
            return {"error": f"Server {server_id} not found"}
        
        # Find and update pod
        pods = self.demo_servers[server_id]["pods"]
        for pod in pods:
            if pod["pod_id"] == pod_name:
                # Update pod fields
                if "Resources" in pod_data:
                    pod["requested"] = pod_data["Resources"]
                if "Owner" in pod_data:
                    pod["owner"] = pod_data["Owner"]
                if "ImageUrl" in pod_data:
                    pod["image"] = pod_data["ImageUrl"]
                
                return {"message": f"Pod {pod_name} updated successfully", "pod": pod}
        
        return {"error": f"Pod {pod_name} not found"}


# Global instance
demo_data_provider = DemoDataProvider() 