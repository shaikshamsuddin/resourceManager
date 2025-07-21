#!/usr/bin/env python3
"""
Auto-fix minikube script.
Automatically detects and fixes common minikube issues.
"""

import subprocess
import time
import logging
from typing import Optional, Dict, Any
import json

class MinikubeAutoFix:
    """Automatically detects and fixes minikube issues."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def get_minikube_status(self) -> Optional[Dict[str, Any]]:
        """Get minikube status as JSON."""
        try:
            result = subprocess.run(
                ['minikube', 'status', '--output', 'json'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            self.logger.error(f"Failed to get minikube status: {e}")
        return None
    
    def is_minikube_running(self) -> bool:
        """Check if minikube is running."""
        status = self.get_minikube_status()
        if not status:
            return False
        
        # Check if host and apiserver are running
        host_status = status.get('Host', {}).get('Status', '')
        apiserver_status = status.get('APIServer', {}).get('Status', '')
        
        return host_status == 'Running' and apiserver_status == 'Running'
    
    def get_current_port(self) -> Optional[int]:
        """Get current minikube port."""
        status = self.get_minikube_status()
        if status and 'Host' in status and 'Port' in status['Host']:
            return int(status['Host']['Port'])
        return None
    
    def fix_kubeconfig(self) -> bool:
        """Fix kubeconfig if it's misconfigured."""
        try:
            self.logger.info("Attempting to fix kubeconfig...")
            result = subprocess.run(
                ['minikube', 'update-context'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.logger.info("Kubeconfig updated successfully")
                return True
            else:
                self.logger.error(f"Failed to update kubeconfig: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error fixing kubeconfig: {e}")
            return False
    
    def restart_minikube(self) -> bool:
        """Restart minikube if needed."""
        try:
            self.logger.info("Restarting minikube...")
            result = subprocess.run(
                ['minikube', 'start'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                self.logger.info("Minikube restarted successfully")
                return True
            else:
                self.logger.error(f"Failed to restart minikube: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error restarting minikube: {e}")
            return False
    
    def auto_fix(self) -> bool:
        """Automatically detect and fix minikube issues."""
        self.logger.info("Starting minikube auto-fix...")
        
        # Check if minikube is running
        if not self.is_minikube_running():
            self.logger.info("Minikube is not running, starting it...")
            return self.restart_minikube()
        
        # Check if kubeconfig is misconfigured
        try:
            result = subprocess.run(
                ['kubectl', 'config', 'view', '--minify', '--output', 'jsonpath={.clusters[0].cluster.server}'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                self.logger.info("Kubeconfig appears misconfigured, fixing...")
                return self.fix_kubeconfig()
        except Exception as e:
            self.logger.error(f"Error checking kubeconfig: {e}")
            return False
        
        # If we get here, everything should be working
        current_port = self.get_current_port()
        self.logger.info(f"Minikube is running on port {current_port}")
        return True
    
    def wait_for_ready(self, timeout: int = 60) -> bool:
        """Wait for minikube to be ready."""
        self.logger.info(f"Waiting for minikube to be ready (timeout: {timeout}s)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_minikube_running():
                self.logger.info("Minikube is ready!")
                return True
            time.sleep(2)
        
        self.logger.error("Timeout waiting for minikube to be ready")
        return False

def main():
    """Main function for command-line usage."""
    fixer = MinikubeAutoFix()
    success = fixer.auto_fix()
    
    if success:
        print("✅ Minikube auto-fix completed successfully")
        return 0
    else:
        print("❌ Minikube auto-fix failed")
        return 1

if __name__ == "__main__":
    exit(main()) 