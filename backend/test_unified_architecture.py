#!/usr/bin/env python3
"""
Test script for the new unified architecture
"""

import json
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from server_manager import server_manager


def test_server_manager():
    """Test the server manager functionality."""
    print("🧪 Testing Unified Architecture")
    print("=" * 50)
    
    # Test 1: Check if servers are loaded
    print("\n1. Testing server loading...")
    server_ids = server_manager.get_server_ids()
    print(f"   Found {len(server_ids)} servers: {server_ids}")
    
    if not server_ids:
        print("   ❌ No servers found in master.json")
        return False
    
    # Test 2: Get server configurations
    print("\n2. Testing server configurations...")
    for server_id in server_ids:
        config = server_manager.get_server_config(server_id)
        if config:
            print(f"   ✅ {server_id}: {config.get('name', 'Unknown')} ({config.get('type', 'unknown')})")
        else:
            print(f"   ❌ {server_id}: Configuration not found")
    
    # Test 3: Test getting all servers data
    print("\n3. Testing server data retrieval...")
    try:
        all_servers = server_manager.get_all_servers_with_pods()
        print(f"   Retrieved data for {len(all_servers)} server instances")
        
        for server in all_servers:
            server_id = server.get('server_id', 'unknown')
            server_name = server.get('server_name', 'Unknown')
            status = server.get('status', 'unknown')
            pod_count = len(server.get('pods', []))
            
            if 'error' in server:
                print(f"   ⚠️  {server_id} ({server_name}): {server['error']}")
            else:
                print(f"   ✅ {server_id} ({server_name}): {status} - {pod_count} pods")
                
    except Exception as e:
        print(f"   ❌ Error getting server data: {e}")
        return False
    
    # Test 4: Test getting specific server data
    print("\n4. Testing specific server data...")
    if server_ids:
        test_server_id = server_ids[0]
        server_data = server_manager.get_server_with_pods(test_server_id)
        
        if server_data:
            if 'error' in server_data:
                print(f"   ⚠️  {test_server_id}: {server_data['error']}")
            else:
                print(f"   ✅ {test_server_id}: {server_data.get('status', 'unknown')} - {len(server_data.get('pods', []))} pods")
        else:
            print(f"   ❌ {test_server_id}: No data returned")
    
    # Test 5: Test default server
    print("\n5. Testing default server...")
    default_server = server_manager.get_default_server_id()
    if default_server:
        print(f"   Default server: {default_server}")
    else:
        print("   No default server configured")
    
    print("\n" + "=" * 50)
    print("✅ Unified architecture test completed!")
    return True


def test_master_config():
    """Test the master.json configuration."""
    print("\n📋 Testing Master Configuration")
    print("=" * 40)
    
    try:
        config_path = Path(__file__).parent / "data" / "master.json"
        
        if not config_path.exists():
            print("❌ master.json not found")
            return False
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        servers = config.get("servers", [])
        print(f"✅ Found {len(servers)} servers in master.json")
        
        for server in servers:
            server_id = server.get("id", "unknown")
            server_name = server.get("name", "Unknown")
            server_type = server.get("type", "unknown")
            connection = server.get("connection_coordinates", {})
            
            print(f"   📍 {server_id}: {server_name} ({server_type})")
            print(f"      Method: {connection.get('method', 'unknown')}")
            
            if connection.get("method") == "kubeconfig":
                kubeconfig_path = connection.get("kubeconfig_path", "not specified")
                print(f"      Kubeconfig: {kubeconfig_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading master.json: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Unified Architecture Test Suite")
    print("=" * 60)
    
    # Test master configuration
    if not test_master_config():
        print("\n❌ Master configuration test failed")
        return
    
    # Test server manager
    if not test_server_manager():
        print("\n❌ Server manager test failed")
        return
    
    print("\n🎉 All tests passed!")
    print("\n📋 Next Steps:")
    print("1. Start the backend: python app.py")
    print("2. Test API endpoints:")
    print("   - GET /servers")
    print("   - GET /servers?server_id=azure-vm-01")
    print("   - POST /create (with server_id)")
    print("   - POST /delete (with server_id)")
    print("   - POST /update (with server_id)")


if __name__ == "__main__":
    main() 