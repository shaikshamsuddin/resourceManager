#!/usr/bin/env python3
"""
Update kubeconfig to use Azure VM public IP
"""

import yaml
import sys

def update_kubeconfig(input_file, output_file, vm_ip):
    """Update kubeconfig to use Azure VM public IP."""
    
    # Read the kubeconfig
    with open(input_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update server address and add insecure flag
    for cluster in config.get('clusters', []):
        if 'cluster' in cluster and 'server' in cluster['cluster']:
            old_server = cluster['cluster']['server']
            print(f"Original server: {old_server}")
            
            # Replace internal IP with public IP
            if '10.0.0.5' in old_server:
                new_server = old_server.replace('10.0.0.5', vm_ip)
                cluster['cluster']['server'] = new_server
                print(f"Updated server: {new_server}")
            else:
                print(f"Server already uses external IP: {old_server}")
            
            # Add insecure-skip-tls-verify flag
            cluster['cluster']['insecure-skip-tls-verify'] = True
            # Remove certificate authority data when using insecure mode
            if 'certificate-authority-data' in cluster['cluster']:
                del cluster['cluster']['certificate-authority-data']
                print("Removed certificate-authority-data (insecure mode)")
            print("Added insecure-skip-tls-verify flag")
    
    # Write updated kubeconfig
    with open(output_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"Updated kubeconfig saved to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_kubeconfig.py <azure_vm_ip>")
        sys.exit(1)
    
    vm_ip = sys.argv[1]
    input_file = "azure_vm_kubeconfig"
    output_file = "azure_vm_kubeconfig_updated"
    
    try:
        update_kubeconfig(input_file, output_file, vm_ip)
        print(f"\n✅ Kubeconfig updated successfully!")
        print(f"📁 Updated file: {output_file}")
        print(f"🌐 Azure VM IP: {vm_ip}")
    except Exception as e:
        print(f"❌ Error updating kubeconfig: {e}")
        sys.exit(1) 