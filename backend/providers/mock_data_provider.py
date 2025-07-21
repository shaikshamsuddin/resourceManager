"""
Mock Data Provider for Demo Mode
This module provides realistic mock data for showcasing the Resource Manager functionality.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

from constants import (
    PodStatus, DefaultValues, TimeFormats
)


class MockDataProvider:
    """Provides realistic mock data for demo mode."""
    
    def __init__(self):
        """Initialize mock data provider."""
        self.mock_db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'mock_db.json')
        self.demo_data = self._generate_demo_data()
    
    def _generate_demo_data(self) -> List[Dict]:
        """
        Generate realistic demo data for showcasing.
        
        Returns:
            List of mock servers with pods
        """
        return [
            {
                "id": "server-01",
                "name": "gpu-node-h100-a",
                "ip": "192.168.1.101",
                "status": "Online",
                "resources": {
                    "total": {"cpus": 64, "ram_gb": 512, "storage_gb": 2048, "gpus": 8},
                    "available": {"cpus": 32, "ram_gb": 256, "storage_gb": 1024, "gpus": 4}
                },
                "pods": [
                    {
                        "pod_id": "ml-training-pod-001",
                        "server_id": "server-01",
                        "image_url": "tensorflow/tensorflow:2.12.0-gpu",
                        "requested": {"gpus": 2, "ram_gb": 32, "storage_gb": 100, "cpus": 8},
                        "owner": "ml-team",
                        "status": "online",
                        "timestamp": (datetime.utcnow() - timedelta(hours=2)).strftime(TimeFormats.ISO_FORMAT),
                        "ports": {
                            "container_port": 8888,
                            "service_port": 8888,
                            "expose_service": True
                        }
                    },
                    {
                        "pod_id": "data-processing-pod-002",
                        "server_id": "server-01",
                        "image_url": "apache/spark:3.4.0",
                        "requested": {"gpus": 0, "ram_gb": 16, "storage_gb": 50, "cpus": 4},
                        "owner": "data-team",
                        "status": "online",
                        "timestamp": (datetime.utcnow() - timedelta(hours=1)).strftime(TimeFormats.ISO_FORMAT)
                    }
                ]
            },
            {
                "id": "server-02",
                "name": "gpu-node-h100-b",
                "ip": "192.168.1.102",
                "status": "Online",
                "resources": {
                    "total": {"cpus": 64, "ram_gb": 512, "storage_gb": 2048, "gpus": 8},
                    "available": {"cpus": 48, "ram_gb": 384, "storage_gb": 1536, "gpus": 6}
                },
                "pods": [
                    {
                        "pod_id": "inference-pod-003",
                        "server_id": "server-02",
                        "image_url": "pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime",
                        "requested": {"gpus": 1, "ram_gb": 8, "storage_gb": 20, "cpus": 2},
                        "owner": "ai-team",
                        "status": "online",
                        "timestamp": (datetime.utcnow() - timedelta(minutes=30)).strftime(TimeFormats.ISO_FORMAT)
                    }
                ]
            },
            {
                "id": "server-03",
                "name": "cpu-node-c5n-18xlarge",
                "ip": "192.168.1.103",
                "status": "Online",
                "resources": {
                    "total": {"cpus": 96, "ram_gb": 192, "storage_gb": 2000, "gpus": 0},
                    "available": {"cpus": 64, "ram_gb": 128, "storage_gb": 1500, "gpus": 0}
                },
                "pods": [
                    {
                        "pod_id": "web-app-pod-004",
                        "server_id": "server-03",
                        "image_url": "nginx:latest",
                        "requested": {"gpus": 0, "ram_gb": 4, "storage_gb": 10, "cpus": 2},
                        "owner": "web-team",
                        "status": "online",
                        "timestamp": (datetime.utcnow() - timedelta(hours=3)).strftime(TimeFormats.ISO_FORMAT)
                    },
                    {
                        "pod_id": "api-pod-005",
                        "server_id": "server-03",
                        "image_url": "node:18-alpine",
                        "requested": {"gpus": 0, "ram_gb": 8, "storage_gb": 20, "cpus": 4},
                        "owner": "backend-team",
                        "status": "online",
                        "timestamp": (datetime.utcnow() - timedelta(hours=2)).strftime(TimeFormats.ISO_FORMAT)
                    },
                    {
                        "pod_id": "database-pod-006",
                        "server_id": "server-03",
                        "image_url": "postgres:15",
                        "requested": {"gpus": 0, "ram_gb": 16, "storage_gb": 100, "cpus": 8},
                        "owner": "db-team",
                        "status": "online",
                        "timestamp": (datetime.utcnow() - timedelta(hours=4)).strftime(TimeFormats.ISO_FORMAT)
                    }
                ]
            },
            {
                "id": "server-04",
                "name": "gpu-node-rtx-4090",
                "ip": "192.168.1.104",
                "status": "Online",
                "resources": {
                    "total": {"cpus": 32, "ram_gb": 256, "storage_gb": 1024, "gpus": 4},
                    "available": {"cpus": 16, "ram_gb": 128, "storage_gb": 512, "gpus": 2}
                },
                "pods": [
                    {
                        "pod_id": "research-pod-007",
                        "server_id": "server-04",
                        "image_url": "jupyter/datascience-notebook:latest",
                        "requested": {"gpus": 1, "ram_gb": 16, "storage_gb": 50, "cpus": 4},
                        "owner": "research-team",
                        "status": "online",
                        "timestamp": (datetime.utcnow() - timedelta(hours=1)).strftime(TimeFormats.ISO_FORMAT)
                    },
                    {
                        "pod_id": "testing-pod-008",
                        "server_id": "server-04",
                        "image_url": "ubuntu:22.04",
                        "requested": {"gpus": 1, "ram_gb": 8, "storage_gb": 20, "cpus": 2},
                        "owner": "qa-team",
                        "status": "pending",
                        "timestamp": datetime.utcnow().strftime(TimeFormats.ISO_FORMAT)
                    }
                ]
            },
            {
                "id": "server-05",
                "name": "storage-node-nvme",
                "ip": "192.168.1.105",
                "status": "Online",
                "resources": {
                    "total": {"cpus": 16, "ram_gb": 64, "storage_gb": 10000, "gpus": 0},
                    "available": {"cpus": 8, "ram_gb": 32, "storage_gb": 6000, "gpus": 0}
                },
                "pods": [
                    {
                        "pod_id": "backup-pod-009",
                        "server_id": "server-05",
                        "image_url": "minio/minio:latest",
                        "requested": {"gpus": 0, "ram_gb": 4, "storage_gb": 2000, "cpus": 2},
                        "owner": "storage-team",
                        "status": "online",
                        "timestamp": (datetime.utcnow() - timedelta(hours=6)).strftime(TimeFormats.ISO_FORMAT)
                    },
                    {
                        "pod_id": "cache-pod-010",
                        "server_id": "server-05",
                        "image_url": "redis:7-alpine",
                        "requested": {"gpus": 0, "ram_gb": 8, "storage_gb": 100, "cpus": 2},
                        "owner": "cache-team",
                        "status": "online",
                        "timestamp": (datetime.utcnow() - timedelta(hours=5)).strftime(TimeFormats.ISO_FORMAT)
                    }
                ]
            }
        ]
    
    def get_servers_with_pods_mdem(self) -> List[Dict]:
        """
        Get mock servers with their pods.
        
        Returns:
            List of mock servers with pods
        """
        return self.demo_data
    
    def add_pod_mdem(self, server_id: str, pod_data: Dict) -> bool:
        """
        Add a pod to the mock data.
        
        Args:
            server_id: Server ID to add pod to
            pod_data: Pod data to add
            
        Returns:
            True if successful, False otherwise
        """
        server = next((s for s in self.demo_data if s['id'] == server_id), None)
        if not server:
            return False
        
        # Update available resources
        available = server['resources']['available']
        requested = pod_data['requested']
        
        for key in ['gpus', 'ram_gb', 'storage_gb', 'cpus']:
            if available.get(key, 0) < requested.get(key, 0):
                return False  # Insufficient resources
            available[key] -= requested.get(key, 0)
        
        # Add pod to server
        pod_data['server_id'] = server_id
        pod_data['timestamp'] = datetime.utcnow().strftime(TimeFormats.ISO_FORMAT)
        server['pods'].append(pod_data)
        
        return True
    
    def remove_pod_mdem(self, pod_id: str) -> bool:
        """
        Remove a pod from the mock data.
        
        Args:
            pod_id: Pod ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        for server in self.demo_data:
            pod = next((p for p in server['pods'] if p['pod_id'] == pod_id), None)
            if pod:
                # Return resources to available pool
                available = server['resources']['available']
                requested = pod['requested']
                
                for key in ['gpus', 'ram_gb', 'storage_gb', 'cpus']:
                    available[key] += requested.get(key, 0)
                
                # Remove pod
                server['pods'].remove(pod)
                return True
        
        return False

    def reset_demo_data(self):
        """
        Reset the in-memory demo data to its initial state.
        """
        self.demo_data = self._generate_demo_data()


# Global instance
mock_data_provider = MockDataProvider() 