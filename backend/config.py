"""
Configuration management for Resource Manager backend.
Handles environment-specific settings for development and production.
"""

import os
from typing import Optional, Dict, Any

from constants import (
    Environment, AuthMethod, DefaultValues, ConfigKeys,
    KubernetesConstants, ErrorMessages
)


class Config:
    """Base configuration class."""
    
    # Environment detection - no default mode
    @classmethod
    def get_environment(cls):
        """Get current environment dynamically."""
        env_value = os.getenv(ConfigKeys.ENVIRONMENT)
        if env_value is None:
            # No environment set - return None to indicate no default
            return None
        return Environment(env_value)
    
    @classmethod
    def get_environment_value(cls):
        """Get current environment value dynamically."""
        env = cls.get_environment()
        if env is None:
            # No environment set - return None
            return None
        return env.value
    
    @classmethod
    def is_debug(cls):
        """Check if in debug mode dynamically."""
        env = cls.get_environment()
        if env is None:
            return False
        return env == Environment.DEMO
    
    # Kubernetes configuration
    KUBERNETES_CONFIG = {
        Environment.DEMO.value: {
            'auth_method': AuthMethod.LOCAL_KUBECONFIG.value,
            'default_image': DefaultValues.DEFAULT_IMAGE_DEV,
            'namespace_prefix': DefaultValues.NAMESPACE_PREFIX_DEV
        },
        Environment.LIVE.value: {
            'auth_method': AuthMethod.LOCAL_KUBECONFIG.value,
            'default_image': DefaultValues.DEFAULT_IMAGE_DEV,
            'namespace_prefix': DefaultValues.NAMESPACE_PREFIX_DEV
        }
    }
    
    # Azure configuration (for production and Azure VM)
    AZURE_CONFIG = {
        'subscription_id': os.getenv(ConfigKeys.AZURE_SUBSCRIPTION_ID),
        'resource_group': os.getenv(ConfigKeys.AZURE_RESOURCE_GROUP),
        'aks_cluster_name': os.getenv(ConfigKeys.AZURE_AKS_CLUSTER_NAME),
        'use_managed_identity': os.getenv(ConfigKeys.AZURE_USE_MANAGED_IDENTITY, 'true').lower() == 'true',
        # Azure VM settings
        'vm_ip': os.getenv(ConfigKeys.AZURE_VM_IP),
        'vm_username': os.getenv(ConfigKeys.AZURE_VM_USERNAME, 'azureuser'),
        'vm_ssh_key_path': os.getenv(ConfigKeys.AZURE_VM_SSH_KEY_PATH),
        'vm_kubeconfig': os.getenv(ConfigKeys.AZURE_VM_KUBECONFIG),
        'vm_password': os.getenv(ConfigKeys.AZURE_VM_PASSWORD)
    }
    
    # API configuration
    API_CONFIG = {
        Environment.DEMO.value: {
            'require_image_url': False,
            'require_k8s_auth': False,
            'enable_swagger': True,
            'cors_origins': ['http://localhost:4200', 'http://127.0.0.1:4200']
        },
        Environment.LIVE.value: {
            'require_image_url': False,
            'require_k8s_auth': False,
            'enable_swagger': True,
            'cors_origins': ['http://localhost:4200', 'http://127.0.0.1:4200']
        }
    }
    
    @classmethod
    def get_kubernetes_config(cls) -> Dict[str, Any]:
        """Get Kubernetes configuration for current environment."""
        env_value = cls.get_environment_value()
        if env_value is None:
            # No environment set - return live config as fallback
            return cls.KUBERNETES_CONFIG[Environment.LIVE.value]
        return cls.KUBERNETES_CONFIG.get(env_value, cls.KUBERNETES_CONFIG[Environment.LIVE.value])
    
    @classmethod
    def get_api_config(cls) -> Dict[str, Any]:
        """Get API configuration for current environment."""
        env_value = cls.get_environment_value()
        if env_value is None:
            # No environment set - return live config as fallback
            return cls.API_CONFIG[Environment.LIVE.value]
        return cls.API_CONFIG.get(env_value, cls.API_CONFIG[Environment.LIVE.value])
    
    @classmethod
    def get_azure_config(cls) -> Dict[str, Any]:
        """Get Azure configuration."""
        return cls.AZURE_CONFIG
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment."""
        env = cls.get_environment()
        if env is None:
            return False
        return env == Environment.LIVE
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development environment."""
        env = cls.get_environment()
        if env is None:
            return False
        return env == Environment.DEMO
    
    @classmethod
    def is_mock_demo(cls) -> bool:
        """Check if running in local mock demo environment."""
        env = cls.get_environment()
        if env is None:
            return False
        return env == Environment.DEMO
    
    @classmethod
    def get_default_image(cls) -> str:
        """Get default container image for current environment."""
        return cls.get_kubernetes_config()['default_image']
    
    @classmethod
    def get_namespace_prefix(cls) -> str:
        """Get namespace prefix for current environment."""
        return cls.get_kubernetes_config()['namespace_prefix']
    
    @classmethod
    def require_image_url(cls) -> bool:
        """Check if image URL is required in current environment."""
        return cls.get_api_config()['require_image_url']
    
    @classmethod
    def get_cors_origins(cls) -> list:
        """Get CORS origins for current environment."""
        return cls.get_api_config()['cors_origins'] 