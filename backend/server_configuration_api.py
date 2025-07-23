"""
Server Configuration API
This module provides REST API endpoints for configuring Azure VM servers automatically.
"""

import os
import json
import yaml
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from datetime import datetime
import getpass

from flask import Blueprint, request, jsonify
from flasgger import swag_from

from constants import (
    ApiResponse, HttpStatus, ErrorMessages, SuccessMessages,
    ConfigKeys, TimeFormats
)

# Create Blueprint for server configuration API
server_config_bp = Blueprint('server_config', __name__, url_prefix='/api/server-config')


class ServerConfigurationManager:
    """Manages server configuration operations."""
    
    def __init__(self):
        """Initialize the server configuration manager."""
        self.backend_dir = Path(__file__).parent
        self.master_json_path = self.backend_dir / "data" / "master.json"
        self.kubeconfig_path = self.backend_dir / "azure_vm_kubeconfig"
        self.kubeconfig_updated_path = self.backend_dir / "azure_vm_kubeconfig_updated"
        self.kubeconfig_sanitized_path = self.backend_dir / "azure_vm_kubeconfig_updated.sanitized"
        
        # Note: Auto-reconnection is now manual only to avoid blocking startup
        # Use the /reconnect endpoint or call reconnect_servers() manually
    
    def _auto_reconnect_on_startup(self):
        """Automatically reconnect to configured servers on startup."""
        try:
            if not self.master_json_path.exists():
                print("ℹ️  No master.json found - no servers to reconnect to")
                return
            
            with open(self.master_json_path, 'r') as f:
                data = json.load(f)
            
            servers = data.get('servers', [])
            if not servers:
                print("ℹ️  No configured servers found in master.json")
                return
            
            print(f"🔄 Attempting to reconnect to {len(servers)} configured server(s)...")
            
            for server in servers:
                server_id = server.get('id')
                server_name = server.get('name', 'Unknown')
                vm_ip = server.get('connection_coordinates', {}).get('host')
                
                if not vm_ip:
                    print(f"⚠️  Server {server_name} ({server_id}) has no VM IP - skipping")
                    continue
                
                print(f"🔗 Reconnecting to {server_name} ({vm_ip})...")
                
                # Test connection to this server
                connection_result = self.test_server_connection(server_id)
                
                if connection_result.get('success'):
                    print(f"✅ Successfully reconnected to {server_name}")
                else:
                    print(f"❌ Failed to reconnect to {server_name}: {connection_result.get('message', 'Unknown error')}")
            
            print("🎯 Server reconnection process completed")
            
        except Exception as e:
            print(f"⚠️  Error during startup reconnection: {e}")
    
    def configure_server(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configure a server using the provided configuration.
        
        Args:
            server_config: Dictionary containing server configuration
            
        Returns:
            Dictionary with configuration result
        """
        try:
            # Extract configuration
            vm_ip = server_config.get('vm_ip')
            username = server_config.get('username', 'azureuser')
            password = server_config.get('password')
            
            if not vm_ip:
                return {
                    'status': ApiResponse.ERROR.value,
                    'message': 'VM IP address is required',
                    'code': HttpStatus.BAD_REQUEST.value
                }
            
            if not password:
                return {
                    'status': ApiResponse.ERROR.value,
                    'message': 'Password is required',
                    'code': HttpStatus.BAD_REQUEST.value
                }
            
            # Step 1: Fetch kubeconfig from VM
            kubeconfig_result = self._fetch_kubeconfig_from_vm(vm_ip, username, password)
            if not kubeconfig_result['success']:
                return {
                    'status': ApiResponse.ERROR.value,
                    'message': f"Failed to fetch kubeconfig: {kubeconfig_result['error']}",
                    'code': HttpStatus.BAD_REQUEST.value
                }
            
            original_kubeconfig = kubeconfig_result['kubeconfig']
            
            # Step 2: Process kubeconfig
            processed_kubeconfig = self._process_kubeconfig(original_kubeconfig, vm_ip)
            
            # Step 3: Save kubeconfig files
            self._save_kubeconfig_files(original_kubeconfig, processed_kubeconfig)
            
            # Step 4: Update master.json
            server_id = self._update_master_json(vm_ip, username, server_config, processed_kubeconfig)
            
            # Step 5: Create environment file
            self._create_environment_file(vm_ip, username)
            
            # Step 6: Test connection
            connection_test = self._test_connection(vm_ip)
            
            return {
                'status': ApiResponse.SUCCESS.value,
                'message': 'Server configured successfully',
                'data': {
                    'server_id': server_id,
                    'vm_ip': vm_ip,
                    'username': username,
                    'kubeconfig_path': str(self.kubeconfig_updated_path.relative_to(self.backend_dir)),
                    'connection_test': connection_test,
                    'timestamp': datetime.now().isoformat()
                },
                'code': HttpStatus.OK.value
            }
            
        except Exception as e:
            return {
                'status': ApiResponse.ERROR.value,
                'message': f'Server configuration failed: {str(e)}',
                'code': HttpStatus.INTERNAL_SERVER_ERROR.value
            }
    
    def _fetch_kubeconfig_from_vm(self, vm_ip: str, username: str, password: str) -> Dict[str, Any]:
        """Fetch kubeconfig from VM using SSH with password authentication."""
        try:
            # Check if sshpass is available
            if not self._check_sshpass_available():
                return {
                    'success': False,
                    'error': 'sshpass is not installed. Please install sshpass first.'
                }
            
            # Build SSH command with sshpass
            ssh_cmd = ['sshpass', '-p', password, 'ssh']
            ssh_cmd.extend(['-o', 'StrictHostKeyChecking=no'])
            ssh_cmd.extend(['-o', 'PubkeyAuthentication=no'])
            ssh_cmd.extend(['-o', 'PasswordAuthentication=yes'])
            ssh_cmd.extend(['-o', 'ConnectTimeout=10'])
            ssh_cmd.extend([f'{username}@{vm_ip}'])
            
            # Test SSH connection first
            test_cmd = ssh_cmd + ['echo "SSH connection successful"']
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'SSH connection failed: {result.stderr}'
                }
            
            # Try multiple kubeconfig locations
            kubeconfig_locations = [
                '~/.kube/config',
                '/var/snap/microk8s/current/credentials/client.config',
                '/etc/kubernetes/admin.conf',
                '/etc/kubernetes/kubeconfig'
            ]
            
            kubeconfig_content = None
            for location in kubeconfig_locations:
                kubeconfig_cmd = ssh_cmd + [f'cat {location}']
                result = subprocess.run(kubeconfig_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout.strip():
                    print(f"Found kubeconfig at: {location}")
                    kubeconfig_content = result.stdout
                    break
            
            # If no kubeconfig found, try to initialize MicroK8s
            if not kubeconfig_content:
                print("No kubeconfig found, attempting to initialize MicroK8s...")
                
                # Check if MicroK8s is installed
                check_cmd = ssh_cmd + ['which microk8s']
                result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    # MicroK8s is installed, try to start it
                    init_cmd = ssh_cmd + ['microk8s start && microk8s status --wait-ready && microk8s config > ~/.kube/config']
                    result = subprocess.run(init_cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        # Try to get the newly created kubeconfig
                        kubeconfig_cmd = ssh_cmd + ['cat ~/.kube/config']
                        result = subprocess.run(kubeconfig_cmd, capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            kubeconfig_content = result.stdout
                            print("Successfully initialized MicroK8s and created kubeconfig")
                        else:
                            raise Exception(f"Failed to read newly created kubeconfig: {result.stderr}")
                    else:
                        raise Exception(f"Failed to initialize MicroK8s: {result.stderr}")
                else:
                    raise Exception("MicroK8s is not installed on the VM. Please install it first: sudo snap install microk8s --classic")
            
            if not kubeconfig_content:
                raise Exception("Could not find or create kubeconfig file on the VM")
            
            if result.returncode != 0:
                # Try alternative kubeconfig locations
                alternative_paths = [
                    'sudo cat /etc/rancher/k3s/k3s.yaml',  # k3s
                    'sudo cat /var/lib/k0s/pki/admin.conf',  # k0s
                    'sudo cat /etc/kubernetes/admin.conf',  # standard k8s
                    'cat ~/.kube/config'  # user kubeconfig
                ]
                
                for path in alternative_paths:
                    alt_cmd = ssh_cmd + [path]
                    result = subprocess.run(alt_cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        break
                else:
                    return {
                        'success': False,
                        'error': f'Failed to get kubeconfig from VM: {result.stderr}'
                    }
            
            kubeconfig_content = result.stdout.strip()
            
            # Validate kubeconfig format
            if not self._validate_kubeconfig(kubeconfig_content):
                # Show the first part of the content for debugging
                content_preview = kubeconfig_content[:200] if kubeconfig_content else "Empty content"
                return {
                    'success': False,
                    'error': f'Invalid kubeconfig format received from VM. Content preview: {content_preview}...'
                }
            
            return {
                'success': True,
                'kubeconfig': kubeconfig_content
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Timeout connecting to Azure VM'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to fetch kubeconfig: {str(e)}'
            }
    
    def _process_kubeconfig(self, kubeconfig_content: str, vm_ip: str) -> str:
        """Process kubeconfig to update server addresses (supports both YAML and JSON)."""
        try:
            # Parse kubeconfig (try YAML first, then JSON)
            try:
                kubeconfig_data = yaml.safe_load(kubeconfig_content)
            except yaml.YAMLError:
                kubeconfig_data = json.loads(kubeconfig_content)
            
            # Update server addresses
            for cluster in kubeconfig_data.get('clusters', []):
                if 'cluster' in cluster and 'server' in cluster['cluster']:
                    server = cluster['cluster']['server']
                    
                    # Check if server needs updating
                    if 'localhost' in server or '127.0.0.1' in server:
                        # Extract port from server URL
                        if ':' in server:
                            port = server.split(':')[-1]
                            new_server = f'https://{vm_ip}:{port}'
                        else:
                            new_server = f'https://{vm_ip}:6443'
                        
                        cluster['cluster']['server'] = new_server
            
            # Add insecure TLS configuration for Azure VM and remove certificate data
            for cluster in kubeconfig_data.get('clusters', []):
                if 'cluster' in cluster:
                    cluster['cluster']['insecure-skip-tls-verify'] = True
                    
                    # Remove certificate authority data (not allowed with insecure flag)
                    if 'certificate-authority-data' in cluster['cluster']:
                        del cluster['cluster']['certificate-authority-data']
                    if 'certificate-authority' in cluster['cluster']:
                        del cluster['cluster']['certificate-authority']
            
            # Return as JSON (standard format for our system)
            return json.dumps(kubeconfig_data, indent=2)
            
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise Exception(f"Invalid kubeconfig format: {e}")
        except Exception as e:
            raise Exception(f"Failed to process kubeconfig: {e}")
    
    def _save_kubeconfig_files(self, original_content: str, processed_content: str) -> None:
        """Save kubeconfig files to appropriate locations."""
        try:
            # Save original kubeconfig
            with open(self.kubeconfig_path, 'w') as f:
                f.write(original_content)
            
            # Save processed kubeconfig
            with open(self.kubeconfig_updated_path, 'w') as f:
                f.write(processed_content)
            
            # Create sanitized version
            sanitized_content = self._create_sanitized_kubeconfig(processed_content)
            with open(self.kubeconfig_sanitized_path, 'w') as f:
                f.write(sanitized_content)
            
            # Set proper permissions
            os.chmod(self.kubeconfig_path, 0o600)
            os.chmod(self.kubeconfig_updated_path, 0o600)
            os.chmod(self.kubeconfig_sanitized_path, 0o644)
            
        except Exception as e:
            raise Exception(f"Failed to save kubeconfig files: {e}")
    
    def _update_master_json(self, vm_ip: str, username: str, server_config: Dict[str, Any], processed_kubeconfig_json: str) -> str:
        """Update master.json with the new server configuration including kubeconfig JSON."""
        try:
            # Read existing master.json
            if self.master_json_path.exists():
                with open(self.master_json_path, 'r') as f:
                    master_config = json.load(f)
            else:
                master_config = {"servers": [], "config": {}}
            
            # Create server ID
            server_id = f"azure-vm-{vm_ip.replace('.', '-')}"
            
            # Parse the processed kubeconfig JSON to include in master.json
            kubeconfig_data = json.loads(processed_kubeconfig_json)
            
            # Create new server configuration
            new_server = {
                "id": server_id,
                "name": server_config.get('name', f"Azure VM Kubernetes ({vm_ip})"),
                "type": "kubernetes",
                "environment": server_config.get('environment', 'live'),
                "connection_coordinates": {
                    "method": "kubeconfig",
                    "host": vm_ip,
                    "port": server_config.get('port', 16443),
                    "username": username,
                    "kubeconfig_path": str(self.kubeconfig_updated_path.relative_to(self.backend_dir)),
                    "kubeconfig_data": kubeconfig_data,  # Include the actual kubeconfig JSON
                    "insecure_skip_tls_verify": True
                },
                "metadata": {
                    "location": server_config.get('location', 'Azure VM'),
                    "environment": server_config.get('environment', 'production'),
                    "description": server_config.get('description', f"Azure VM Kubernetes cluster at {vm_ip}"),
                    "setup_method": "api_automated",
                    "setup_timestamp": datetime.now().isoformat(),
                    "configured_by": server_config.get('configured_by', 'api')
                }
            }
            
            # Check if server already exists and update it
            server_exists = False
            for i, server in enumerate(master_config.get("servers", [])):
                if server.get("id") == server_id:
                    master_config["servers"][i] = new_server
                    server_exists = True
                    break
            
            if not server_exists:
                master_config.setdefault("servers", []).append(new_server)
            
            # Update default server if not set
            if not master_config.get("config", {}).get("default_server"):
                master_config.setdefault("config", {})["default_server"] = server_id
            
            # Ensure config section exists
            if "config" not in master_config:
                master_config["config"] = {}
            
            # Add/update common config
            master_config["config"].update({
                "refresh_interval": 30,
                "timeout": 30,
                "max_retries": 3
            })
            
            # Write updated master.json
            with open(self.master_json_path, 'w') as f:
                json.dump(master_config, f, indent=2)
            
            return server_id
            
        except Exception as e:
            raise Exception(f"Failed to update master.json: {e}")
    
    def _create_environment_file(self, vm_ip: str, username: str) -> None:
        """Create .env file with the new configuration."""
        try:
            env_content = f"""# Azure VM Configuration - Auto-generated via API
# Generated on: {datetime.now().isoformat()}

# Azure VM Connection Details
AZURE_VM_IP={vm_ip}
AZURE_VM_USERNAME={username}
AZURE_VM_KUBECONFIG={self.kubeconfig_updated_path.relative_to(self.backend_dir)}

# Backend Configuration
ENVIRONMENT=live
BACKEND_PORT=5005

# CORS Configuration (for frontend)
CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
"""
            
            env_file = self.backend_dir / ".env"
            with open(env_file, 'w') as f:
                f.write(env_content)
            
        except Exception as e:
            raise Exception(f"Failed to create .env file: {e}")
    
    def _test_connection(self, vm_ip: str) -> Dict[str, Any]:
        """Test the connection using the new kubeconfig."""
        try:
            # Test with kubectl
            test_cmd = [
                'kubectl', 
                '--kubeconfig', str(self.kubeconfig_updated_path),
                'get', 'nodes'
            ]
            
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': 'Connection test successful',
                    'nodes': result.stdout.strip()
                }
            else:
                return {
                    'success': False,
                    'message': f'Connection test failed: {result.stderr}',
                    'error': result.stderr
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection test error: {str(e)}',
                'error': str(e)
            }
    
    def _check_sshpass_available(self) -> bool:
        """Check if sshpass is available."""
        try:
            result = subprocess.run(['sshpass', '-V'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _validate_kubeconfig(self, content: str) -> bool:
        """Validate kubeconfig format (supports both YAML and JSON)."""
        try:
            # Check if content is empty or whitespace only
            if not content or not content.strip():
                print("Kubeconfig content is empty")
                return False
            
            # Try to parse as YAML first (most common format)
            try:
                data = yaml.safe_load(content)
                print("Successfully parsed kubeconfig as YAML")
            except yaml.YAMLError:
                # Try to parse as JSON
                try:
                    data = json.loads(content)
                    print("Successfully parsed kubeconfig as JSON")
                except json.JSONDecodeError as e:
                    print(f"Kubeconfig parsing failed (neither YAML nor JSON): {e}")
                    return False
            
            # Basic validation of kubeconfig structure
            required_keys = ['apiVersion', 'kind']
            if not all(key in data for key in required_keys):
                print(f"Missing required keys in kubeconfig: {required_keys}")
                return False
            
            # Check if it's a Config object
            if data.get('kind') != 'Config':
                print(f"Invalid kubeconfig kind: {data.get('kind')}, expected 'Config'")
                return False
            
            # Check for clusters, contexts, and users
            if not data.get('clusters'):
                print("No clusters found in kubeconfig")
                return False
                
            if not data.get('contexts'):
                print("No contexts found in kubeconfig")
                return False
                
            if not data.get('users'):
                print("No users found in kubeconfig")
                return False
            
            print("Kubeconfig validation successful")
            return True
            
        except Exception as e:
            print(f"Kubeconfig validation failed: {e}")
            return False
    
    def _create_sanitized_kubeconfig(self, kubeconfig_content: str) -> str:
        """Create a sanitized version of kubeconfig for documentation (supports both YAML and JSON)."""
        try:
            # Parse kubeconfig (try YAML first, then JSON)
            try:
                data = yaml.safe_load(kubeconfig_content)
            except yaml.YAMLError:
                data = json.loads(kubeconfig_content)
            
            # Remove sensitive data
            for user in data.get('users', []):
                if 'user' in user:
                    user['user'] = {
                        'client-certificate-data': '<REDACTED>',
                        'client-key-data': '<REDACTED>'
                    }
            
            # Add sanitization notice
            sanitized_content = f"""# Sanitized version of kubeconfig
# This file contains the structure but no sensitive credentials
# Generated on: {datetime.now().isoformat()}

{json.dumps(data, indent=2)}
"""
            return sanitized_content
            
        except Exception as e:
            return f"# Error creating sanitized version: {e}\n{kubeconfig_content}"
    
    def get_configured_servers(self) -> Dict[str, Any]:
        """Get list of configured servers."""
        try:
            if not self.master_json_path.exists():
                return {
                    'status': ApiResponse.SUCCESS.value,
                    'data': {'servers': []},
                    'code': HttpStatus.OK.value
                }
            
            with open(self.master_json_path, 'r') as f:
                master_config = json.load(f)
            
            servers = master_config.get('servers', [])
            
            # Add connection status for each server
            for server in servers:
                server_id = server.get('id')
                if server_id:
                    # Check if kubeconfig exists
                    kubeconfig_path = server.get('connection_coordinates', {}).get('kubeconfig_path')
                    if kubeconfig_path:
                        full_path = self.backend_dir / kubeconfig_path
                        server['kubeconfig_exists'] = full_path.exists()
                    else:
                        server['kubeconfig_exists'] = False
            
            return {
                'status': ApiResponse.SUCCESS.value,
                'data': {
                    'servers': servers,
                    'total_count': len(servers),
                    'default_server': master_config.get('config', {}).get('default_server')
                },
                'code': HttpStatus.OK.value
            }
            
        except Exception as e:
            return {
                'status': ApiResponse.ERROR.value,
                'message': f'Failed to get configured servers: {str(e)}',
                'code': HttpStatus.INTERNAL_SERVER_ERROR.value
            }
    
    def test_server_connection(self, server_id: str) -> Dict[str, Any]:
        """Test connection to a specific server."""
        try:
            if not self.master_json_path.exists():
                return {
                    'status': ApiResponse.ERROR.value,
                    'message': 'No servers configured',
                    'code': HttpStatus.NOT_FOUND.value
                }
            
            with open(self.master_json_path, 'r') as f:
                master_config = json.load(f)
            
            # Find the server
            server = None
            for s in master_config.get('servers', []):
                if s.get('id') == server_id:
                    server = s
                    break
            
            if not server:
                return {
                    'status': ApiResponse.ERROR.value,
                    'message': f'Server {server_id} not found',
                    'code': HttpStatus.NOT_FOUND.value
                }
            
            # Check for kubeconfig data in master.json first
            kubeconfig_data = server.get('connection_coordinates', {}).get('kubeconfig_data')
            kubeconfig_path = server.get('connection_coordinates', {}).get('kubeconfig_path')
            
            if kubeconfig_data:
                # Use kubeconfig data from master.json
                test_result = self._test_connection_with_kubeconfig_data(kubeconfig_data)
            elif kubeconfig_path:
                # Fall back to file path method
                full_kubeconfig_path = self.backend_dir / kubeconfig_path
                if not full_kubeconfig_path.exists():
                    return {
                        'status': ApiResponse.ERROR.value,
                        'message': 'Kubeconfig file not found',
                        'code': HttpStatus.NOT_FOUND.value
                    }
                test_result = self._test_connection_with_kubeconfig(full_kubeconfig_path)
            else:
                return {
                    'status': ApiResponse.ERROR.value,
                    'message': 'No kubeconfig found for server',
                    'code': HttpStatus.BAD_REQUEST.value
                }
            
            return {
                'status': ApiResponse.SUCCESS.value,
                'data': {
                    'server_id': server_id,
                    'server_name': server.get('name'),
                    'connection_test': test_result,
                    'timestamp': datetime.now().isoformat()
                },
                'code': HttpStatus.OK.value
            }
            
        except Exception as e:
            return {
                'status': ApiResponse.ERROR.value,
                'message': f'Failed to test server connection: {str(e)}',
                'code': HttpStatus.INTERNAL_SERVER_ERROR.value
            }
    
    def _test_connection_with_kubeconfig(self, kubeconfig_path: Path) -> Dict[str, Any]:
        """Test connection using a specific kubeconfig file."""
        try:
            test_cmd = [
                'kubectl', 
                '--kubeconfig', str(kubeconfig_path),
                'get', 'nodes'
            ]
            
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': 'Connection test successful',
                    'nodes': result.stdout.strip()
                }
            else:
                return {
                    'success': False,
                    'message': f'Connection test failed: {result.stderr}',
                    'error': result.stderr
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection test error: {str(e)}',
                'error': str(e)
            }

    def _test_connection_with_kubeconfig_data(self, kubeconfig_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection using kubeconfig data from master.json."""
        try:
            # Create temporary kubeconfig file from JSON data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
                # Convert JSON back to YAML for kubectl
                yaml.dump(kubeconfig_data, temp_file, default_flow_style=False)
                temp_kubeconfig_path = temp_file.name
            
            try:
                # Test connection using temporary kubeconfig
                test_cmd = [
                    'kubectl', 
                    '--kubeconfig', temp_kubeconfig_path,
                    'get', 'nodes'
                ]
                
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    return {
                        'success': True,
                        'message': 'Connection test successful',
                        'nodes': result.stdout.strip()
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Connection test failed: {result.stderr}',
                        'error': result.stderr
                    }
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_kubeconfig_path)
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection test error: {str(e)}',
                'error': str(e)
            }

    def deconfigure_server(self, server_id: str) -> Dict[str, Any]:
        """De-configure/remove an existing server."""
        try:
            # Load current server configuration
            if not self.master_json_path.exists():
                return {
                    'success': False,
                    'message': 'No server configuration found',
                    'code': 404
                }
            
            with open(self.master_json_path, 'r') as f:
                data = json.load(f)
            
            # Find the server to remove
            server_to_remove = None
            server_index = None
            
            for i, server in enumerate(data.get('servers', [])):
                if server.get('id') == server_id or server.get('server_id') == server_id:
                    server_to_remove = server
                    server_index = i
                    break
            
            if not server_to_remove:
                return {
                    'success': False,
                    'message': f'Server {server_id} not found',
                    'code': 404
                }
            
            # Get kubeconfig path for cleanup
            kubeconfig_path = server_to_remove.get('connection_coordinates', {}).get('kubeconfig_path')
            
            # Remove server from configuration
            data['servers'].pop(server_index)
            
            # Update default server if it was the one being removed
            if data.get('config', {}).get('default_server') == server_id:
                # Set first available server as default, or None if no servers left
                if data['servers']:
                    data.setdefault('config', {})['default_server'] = data['servers'][0].get('id')
                else:
                    data.setdefault('config', {})['default_server'] = None
            
            # Save updated configuration
            with open(self.master_json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Clean up kubeconfig files if they exist
            files_to_remove = []
            if kubeconfig_path:
                # Convert relative path to absolute
                kubeconfig_abs_path = self.backend_dir / kubeconfig_path
                
                # Remove the main kubeconfig file
                if kubeconfig_abs_path.exists():
                    files_to_remove.append(str(kubeconfig_abs_path))
                
                # Remove related files (original, sanitized versions)
                base_name = str(kubeconfig_abs_path).replace('_updated', '').replace('_sanitized', '')
                related_files = [
                    f"{base_name}",
                    f"{base_name}_updated",
                    f"{base_name}_updated_sanitized",
                    f"{base_name}_sanitized"
                ]
                
                for file_path in related_files:
                    if Path(file_path).exists() and file_path not in files_to_remove:
                        files_to_remove.append(file_path)
            
            # Actually remove the files
            removed_files = []
            for file_path in files_to_remove:
                try:
                    Path(file_path).unlink()
                    removed_files.append(file_path)
                except OSError as e:
                    print(f"Warning: Could not remove file {file_path}: {e}")
            
            return {
                'success': True,
                'message': f'Server {server_id} de-configured successfully',
                'data': {
                    'server_id': server_id,
                    'server_name': server_to_remove.get('name') or server_to_remove.get('server_name'),
                    'removed_files': removed_files,
                    'remaining_servers': len(data['servers']),
                    'new_default_server': data.get('config', {}).get('default_server'),
                    'timestamp': datetime.now().isoformat()
                },
                'code': 200
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to de-configure server: {str(e)}',
                'code': 500
            }


# Global instance
server_config_manager = ServerConfigurationManager()


# API Endpoints

@server_config_bp.route('/configure', methods=['POST'])
@swag_from({
    'tags': ['Server Configuration'],
    'summary': 'Configure a new Azure VM server',
    'description': 'Automatically configure an Azure VM server by fetching kubeconfig and updating configuration files',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'vm_ip': {'type': 'string', 'description': 'Azure VM IP address'},
                    'username': {'type': 'string', 'description': 'VM username (default: azureuser)'},
                    'password': {'type': 'string', 'description': 'VM password'},
                    'name': {'type': 'string', 'description': 'Server name (optional)'},
                    'environment': {'type': 'string', 'description': 'Environment (default: live)'},
                    'port': {'type': 'integer', 'description': 'Kubernetes port (default: 16443)'},
                    'location': {'type': 'string', 'description': 'Server location (optional)'},
                    'description': {'type': 'string', 'description': 'Server description (optional)'},
                    'configured_by': {'type': 'string', 'description': 'Who configured this server (optional)'}
                },
                'required': ['vm_ip', 'password']
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Server configured successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'message': {'type': 'string'},
                    'data': {'type': 'object'},
                    'code': {'type': 'integer'}
                }
            }
        },
        400: {'description': 'Bad request - missing required fields'},
        500: {'description': 'Internal server error'}
    }
})
def configure_server():
    """Configure a new Azure VM server."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': ApiResponse.ERROR.value,
                'message': 'No data provided',
                'code': HttpStatus.BAD_REQUEST.value
            }), HttpStatus.BAD_REQUEST.value
        
        # Configure the server
        result = server_config_manager.configure_server(data)
        
        return jsonify(result), result.get('code', HttpStatus.OK.value)
        
    except Exception as e:
        return jsonify({
            'status': ApiResponse.ERROR.value,
            'message': f'Server configuration failed: {str(e)}',
            'code': HttpStatus.INTERNAL_SERVER_ERROR.value
        }), HttpStatus.INTERNAL_SERVER_ERROR.value


@server_config_bp.route('/servers', methods=['GET'])
@swag_from({
    'tags': ['Server Configuration'],
    'summary': 'Get configured servers',
    'description': 'Get list of all configured servers with their status',
    'responses': {
        200: {
            'description': 'List of configured servers',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'data': {'type': 'object'},
                    'code': {'type': 'integer'}
                }
            }
        }
    }
})
def get_configured_servers():
    """Get list of configured servers."""
    try:
        result = server_config_manager.get_configured_servers()
        return jsonify(result), result.get('code', HttpStatus.OK.value)
        
    except Exception as e:
        return jsonify({
            'status': ApiResponse.ERROR.value,
            'message': f'Failed to get servers: {str(e)}',
            'code': HttpStatus.INTERNAL_SERVER_ERROR.value
        }), HttpStatus.INTERNAL_SERVER_ERROR.value


@server_config_bp.route('/test/<server_id>', methods=['POST'])
@swag_from({
    'tags': ['Server Configuration'],
    'summary': 'Test server connection',
    'description': 'Test connection to a specific configured server',
    'parameters': [
        {
            'name': 'server_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Server ID to test'
        }
    ],
    'responses': {
        200: {
            'description': 'Connection test result',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'data': {'type': 'object'},
                    'code': {'type': 'integer'}
                }
            }
        },
        404: {'description': 'Server not found'}
    }
})
def test_server_connection(server_id):
    """Test connection to a specific server."""
    try:
        result = server_config_manager.test_server_connection(server_id)
        return jsonify(result), result.get('code', HttpStatus.OK.value)
        
    except Exception as e:
        return jsonify({
            'status': ApiResponse.ERROR.value,
            'message': f'Failed to test connection: {str(e)}',
            'code': HttpStatus.INTERNAL_SERVER_ERROR.value
        }), HttpStatus.INTERNAL_SERVER_ERROR.value


@server_config_bp.route('/deconfigure/<server_id>', methods=['DELETE'])
@swag_from({
    'tags': ['Server Configuration'],
    'summary': 'De-configure/remove a server',
    'description': 'Remove an existing server configuration and clean up associated files',
    'parameters': [
        {
            'name': 'server_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Server ID to de-configure'
        }
    ],
    'responses': {
        200: {
            'description': 'Server de-configured successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'message': {'type': 'string'},
                    'data': {'type': 'object'},
                    'code': {'type': 'integer'}
                }
            }
        },
        404: {'description': 'Server not found'},
        500: {'description': 'Internal server error'}
    }
})
def deconfigure_server(server_id):
    """De-configure/remove an existing server."""
    try:
        result = server_config_manager.deconfigure_server(server_id)
        return jsonify(result), result.get('code', HttpStatus.OK.value)
        
    except Exception as e:
        return jsonify({
            'status': ApiResponse.ERROR.value,
            'message': f'Failed to de-configure server: {str(e)}',
            'code': HttpStatus.INTERNAL_SERVER_ERROR.value
        }), HttpStatus.INTERNAL_SERVER_ERROR.value


@server_config_bp.route('/startup-reconnect', methods=['POST'])
@swag_from({
    'tags': ['Server Configuration'],
    'summary': 'Trigger startup reconnection to configured servers',
    'description': 'Manually trigger the startup reconnection process that was previously automatic',
    'responses': {
        200: {
            'description': 'Startup reconnection process completed',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'message': {'type': 'string'},
                    'data': {'type': 'object'},
                    'code': {'type': 'integer'}
                }
            }
        },
        500: {'description': 'Internal server error'}
    }
})
def startup_reconnect():
    """Trigger the startup reconnection process manually."""
    try:
        manager = ServerConfigurationManager()
        manager._auto_reconnect_on_startup()
        
        return jsonify({
            'status': ApiResponse.SUCCESS.value,
            'message': 'Startup reconnection process completed',
            'data': {
                'timestamp': datetime.now().isoformat()
            },
            'code': HttpStatus.OK.value
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': ApiResponse.ERROR.value,
            'message': f'Failed to complete startup reconnection: {str(e)}',
            'code': HttpStatus.INTERNAL_SERVER_ERROR.value
        }), 500

@server_config_bp.route('/reconnect', methods=['POST'])
@swag_from({
    'tags': ['Server Configuration'],
    'summary': 'Reconnect to all configured servers',
    'description': 'Manually trigger reconnection to all configured servers to refresh their status',
    'responses': {
        200: {
            'description': 'Reconnection process completed',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'message': {'type': 'string'},
                    'data': {'type': 'object'},
                    'code': {'type': 'integer'}
                }
            }
        },
        500: {'description': 'Internal server error'}
    }
})
def reconnect_servers():
    """Manually reconnect to all configured servers."""
    try:
        manager = ServerConfigurationManager()
        
        if not manager.master_json_path.exists():
            return jsonify({
                'status': ApiResponse.ERROR.value,
                'message': 'No server configuration found',
                'code': HttpStatus.NOT_FOUND.value
            }), 404
        
        with open(manager.master_json_path, 'r') as f:
            data = json.load(f)
        
        servers = data.get('servers', [])
        if not servers:
            return jsonify({
                'status': ApiResponse.ERROR.value,
                'message': 'No configured servers found',
                'code': HttpStatus.NOT_FOUND.value
            }), 404
        
        results = []
        successful_reconnections = 0
        
        for server in servers:
            server_id = server.get('id')
            server_name = server.get('name', 'Unknown')
            vm_ip = server.get('connection_coordinates', {}).get('host')
            
            if not vm_ip:
                results.append({
                    'server_id': server_id,
                    'server_name': server_name,
                    'status': 'skipped',
                    'message': 'No VM IP found'
                })
                continue
            
            # Test connection to this server
            connection_result = manager.test_server_connection(server_id)
            
            if connection_result.get('success'):
                successful_reconnections += 1
                results.append({
                    'server_id': server_id,
                    'server_name': server_name,
                    'status': 'success',
                    'message': 'Successfully reconnected'
                })
            else:
                results.append({
                    'server_id': server_id,
                    'server_name': server_name,
                    'status': 'failed',
                    'message': connection_result.get('message', 'Unknown error')
                })
        
        return jsonify({
            'status': ApiResponse.SUCCESS.value,
            'message': f'Reconnection process completed. {successful_reconnections}/{len(servers)} servers reconnected successfully.',
            'data': {
                'total_servers': len(servers),
                'successful_reconnections': successful_reconnections,
                'failed_reconnections': len(servers) - successful_reconnections,
                'results': results,
                'timestamp': datetime.now().isoformat()
            },
            'code': HttpStatus.OK.value
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': ApiResponse.ERROR.value,
            'message': f'Failed to reconnect servers: {str(e)}',
            'code': HttpStatus.INTERNAL_SERVER_ERROR.value
        }), 500

@server_config_bp.route('/health', methods=['GET'])
@swag_from({
    'tags': ['Server Configuration'],
    'summary': 'Health check for server configuration API',
    'description': 'Check if the server configuration API is working',
    'responses': {
        200: {
            'description': 'API is healthy',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'message': {'type': 'string'},
                    'timestamp': {'type': 'string'},
                    'code': {'type': 'integer'}
                }
            }
        }
    }
})
def health_check():
    """Health check for server configuration API."""
    return jsonify({
        'status': ApiResponse.SUCCESS.value,
        'message': 'Server Configuration API is healthy',
        'timestamp': datetime.now().isoformat(),
        'code': HttpStatus.OK.value
    }), HttpStatus.OK.value 