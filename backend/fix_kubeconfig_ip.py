#!/usr/bin/env python3
"""
Fix kubeconfig to use external IP instead of internal IP
"""

import json
import yaml

def fix_kubeconfig_ip():
    """Update kubeconfig to use external IP"""
    
    # Load master.json
    with open('data/master.json', 'r') as f:
        data = json.load(f)
    
    server = data['servers'][0]
    kubeconfig_data = server['connection_coordinates']['kubeconfig_data']
    
    # Update the server URL to use external IP
    for cluster in kubeconfig_data.get('clusters', []):
        if 'cluster' in cluster and 'server' in cluster['cluster']:
            old_server = cluster['cluster']['server']
            print(f"Original server: {old_server}")
            
            # Replace internal IP with external IP
            if '10.0.0.5' in old_server:
                new_server = old_server.replace('10.0.0.5', '4.246.178.26')
                cluster['cluster']['server'] = new_server
                print(f"Updated server: {new_server}")
            else:
                print(f"Server already uses external IP: {old_server}")
    
    # Write back the updated configuration
    with open('data/master.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print("Kubeconfig IP updated successfully")
    return True

if __name__ == "__main__":
    fix_kubeconfig_ip() 