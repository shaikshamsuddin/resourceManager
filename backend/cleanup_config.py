#!/usr/bin/env python3
"""
Clean up master.json to only keep the working VM-1 configuration
"""

import json

def cleanup_config():
    """Remove VM-2 and keep only VM-1 configuration"""
    
    # Load master.json
    with open('data/master.json', 'r') as f:
        data = json.load(f)
    
    # Keep only the first server (VM-1)
    servers = data.get('servers', [])
    if len(servers) > 1:
        print(f"Removing {len(servers) - 1} extra servers, keeping only VM-1")
        data['servers'] = [servers[0]]  # Keep only the first server
    
    # Write back the cleaned configuration
    with open('data/master.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print("Configuration cleaned up successfully")
    return True

if __name__ == "__main__":
    cleanup_config() 