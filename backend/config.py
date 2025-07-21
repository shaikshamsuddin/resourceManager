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
    
    # Environment detection - default to local mock demo mode
    @classmethod
    def get_environment(cls):
        """Get current environment dynamically."""
        return Environment(os.getenv(ConfigKeys.ENVIRONMENT, Environment.LOCAL_MOCK_DB.value))
    
    @classmethod
    def get_environment_value(cls):
        """Get current environment value dynamically."""
        return cls.get_environment().value
    
    @classmethod
    def is_debug(cls):
        """Check if in debug mode dynamically."""
        return cls.get_environment() == Environment.DEVELOPMENT
    
    # Kubernetes configuration
    KUBERNETES_CONFIG = {
        Environment.LOCAL_MOCK_DB.value: {
            'auth_method': AuthMethod.LOCAL_KUBECONFIG.value,
            'default_image': DefaultValues.DEFAULT_IMAGE_DEV,
            'namespace_prefix': DefaultValues.NAMESPACE_PREFIX_DEV
        },
        Environment.DEVELOPMENT.value: {
            'auth_method': AuthMethod.LOCAL_KUBECONFIG.value,
            'default_image': DefaultValues.DEFAULT_IMAGE_DEV,
            'namespace_prefix': DefaultValues.NAMESPACE_PREFIX_DEV
        },
        Environment.PRODUCTION.value: {
            'auth_method': AuthMethod.AZURE_AKS.value,
            'default_image': DefaultValues.DEFAULT_IMAGE_PROD,
            'namespace_prefix': DefaultValues.NAMESPACE_PREFIX_PROD
        }
    }
    
    # Azure configuration (for production)
    AZURE_CONFIG = {
        'subscription_id': os.getenv(ConfigKeys.AZURE_SUBSCRIPTION_ID),
        'resource_group': os.getenv(ConfigKeys.AZURE_RESOURCE_GROUP),
        'aks_cluster_name': os.getenv(ConfigKeys.AZURE_AKS_CLUSTER_NAME),
        'use_managed_identity': os.getenv(ConfigKeys.AZURE_USE_MANAGED_IDENTITY, 'true').lower() == 'true'
    }
    
    # API configuration
    API_CONFIG = {
        Environment.LOCAL_MOCK_DB.value: {
            'require_image_url': False,
            'require_k8s_auth': False,
            'enable_swagger': True,
            'cors_origins': ['http://localhost:4200', 'http://127.0.0.1:4200']
        },
        Environment.DEVELOPMENT.value: {
            'require_image_url': False,
            'require_k8s_auth': False,
            'enable_swagger': True,
            'cors_origins': ['http://localhost:4200', 'http://127.0.0.1:4200']
        },
        Environment.PRODUCTION.value: {
            'require_image_url': True,
            'require_k8s_auth': False,  # Handled by Azure
            'enable_swagger': False,
            'cors_origins': os.getenv(ConfigKeys.CORS_ORIGINS, '').split(',') if os.getenv(ConfigKeys.CORS_ORIGINS) else []
        }
    }
    
    @classmethod
    def get_kubernetes_config(cls) -> Dict[str, Any]:
        """Get Kubernetes configuration for current environment."""
        return cls.KUBERNETES_CONFIG.get(cls.get_environment_value(), cls.KUBERNETES_CONFIG[Environment.DEVELOPMENT.value])
    
    @classmethod
    def get_api_config(cls) -> Dict[str, Any]:
        """Get API configuration for current environment."""
        return cls.API_CONFIG.get(cls.get_environment_value(), cls.API_CONFIG[Environment.DEVELOPMENT.value])
    
    @classmethod
    def get_azure_config(cls) -> Dict[str, Any]:
        """Get Azure configuration."""
        return cls.AZURE_CONFIG
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment."""
        return cls.get_environment() == Environment.PRODUCTION
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development environment."""
        return cls.get_environment() == Environment.DEVELOPMENT
    
    @classmethod
    def is_mock_demo(cls) -> bool:
        """Check if running in local mock demo environment."""
        return cls.get_environment() == Environment.LOCAL_MOCK_DB
    
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