#!/usr/bin/env python3
"""
Test Kubernetes connection to debug the error
"""

import json
import tempfile
import yaml
from kubernetes import client, config as k8s_config

def test_kubeconfig():
    """Test the kubeconfig from master.json"""
    
    # Load master.json
    with open('data/master.json', 'r') as f:
        data = json.load(f)
    
    server = data['servers'][0]
    kubeconfig_data = server['connection_coordinates']['kubeconfig_data']
    
    print("Testing kubeconfig data:")
    print(f"Cluster server: {kubeconfig_data['clusters'][0]['cluster']['server']}")
    print(f"Insecure skip TLS: {kubeconfig_data['clusters'][0]['cluster'].get('insecure-skip-tls-verify')}")
    
    try:
        # Create temporary kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as temp_file:
            yaml.dump(kubeconfig_data, temp_file)
            temp_file_path = temp_file.name
        
        print(f"Created temp kubeconfig at: {temp_file_path}")
        
        # Load the kubeconfig
        k8s_config.load_kube_config(config_file=temp_file_path)
        
        # Create API client
        core_v1 = client.CoreV1Api()
        
        # Test connection
        print("Testing connection to Kubernetes API...")
        nodes = core_v1.list_node()
        print(f"Success! Found {len(nodes.items)} nodes")
        
        # List first node
        if nodes.items:
            node = nodes.items[0]
            print(f"First node: {node.metadata.name}")
            print(f"Node status: {node.status.conditions[-1].type if node.status.conditions else 'Unknown'}")
        
        return True
        
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_kubeconfig() 