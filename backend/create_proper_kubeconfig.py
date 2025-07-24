#!/usr/bin/env python3
"""
Create a proper kubeconfig with external IP and correct authentication
"""

import json
import subprocess
import yaml

def create_proper_kubeconfig():
    """Create kubeconfig with external IP and proper authentication"""
    
    # Get kubeconfig from Azure VM
    try:
        result = subprocess.run([
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            'azureuser@4.246.178.26', 'sudo microk8s config'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Failed to get kubeconfig: {result.stderr}")
            return False
        
        kubeconfig_content = result.stdout
        print("Successfully retrieved kubeconfig from Azure VM")
        
        # Parse the kubeconfig
        kubeconfig_data = yaml.safe_load(kubeconfig_content)
        
        # Update server URL to use external IP
        for cluster in kubeconfig_data.get('clusters', []):
            if 'cluster' in cluster and 'server' in cluster['cluster']:
                old_server = cluster['cluster']['server']
                print(f"Original server: {old_server}")
                
                # Replace internal IP with external IP
                if '10.0.0.5' in old_server:
                    new_server = old_server.replace('10.0.0.5', '4.246.178.26')
                    cluster['cluster']['server'] = new_server
                    print(f"Updated server: {new_server}")
        
        # Load master.json
        with open('data/master.json', 'r') as f:
            data = json.load(f)
        
        # Update the kubeconfig data
        server = data['servers'][0]
        server['connection_coordinates']['kubeconfig_data'] = kubeconfig_data
        
        # Write back to master.json
        with open('data/master.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        print("Successfully updated master.json with proper kubeconfig")
        return True
        
    except subprocess.TimeoutExpired:
        print("Timeout getting kubeconfig from Azure VM")
        return False
    except Exception as e:
        print(f"Error creating kubeconfig: {e}")
        return False

if __name__ == "__main__":
    create_proper_kubeconfig() 