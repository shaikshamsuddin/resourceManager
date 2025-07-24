#!/usr/bin/env python3
"""
Final kubeconfig fix - add insecure-skip-tls-verify flag
"""

import json

def final_kubeconfig_fix():
    """Add insecure-skip-tls-verify flag to bypass SSL verification"""
    
    # Load master.json
    with open('data/master.json', 'r') as f:
        data = json.load(f)
    
    server = data['servers'][0]
    kubeconfig_data = server['connection_coordinates']['kubeconfig_data']
    
    # Add insecure-skip-tls-verify flag to the cluster
    for cluster in kubeconfig_data.get('clusters', []):
        if 'cluster' in cluster:
            cluster_config = cluster['cluster']
            # Add insecure flag
            cluster_config['insecure-skip-tls-verify'] = True
            # Remove certificate authority data since we're using insecure mode
            if 'certificate-authority-data' in cluster_config:
                del cluster_config['certificate-authority-data']
            print("Added insecure-skip-tls-verify flag and removed certificate authority data")
    
    # Remove client certificate data from users since we're using insecure mode
    for user in kubeconfig_data.get('users', []):
        if 'user' in user:
            user_config = user['user']
            if 'client-certificate-data' in user_config:
                del user_config['client-certificate-data']
            if 'client-key-data' in user_config:
                del user_config['client-key-data']
            print("Removed client certificate data from user")
    
    # Write back the fixed data
    with open('data/master.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print("Final kubeconfig fix applied")
    return True

if __name__ == "__main__":
    final_kubeconfig_fix() 