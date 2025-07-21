/**
 * Environment configuration for Resource Manager frontend.
 * Handles environment-specific settings and feature flags.
 */

import { Environment, FeatureFlags } from '../constants/app.constants';

export interface EnvironmentConfig {
  requireImageUrl: boolean;
  enableAdvancedFeatures: boolean;
  apiBaseUrl: string;
  environment: Environment;
}

export class EnvironmentService {
  private static instance: EnvironmentService;
  private config: EnvironmentConfig;

  private constructor() {
    this.config = this.loadConfig();
  }

  public static getInstance(): EnvironmentService {
    if (!EnvironmentService.instance) {
      EnvironmentService.instance = new EnvironmentService();
    }
    return EnvironmentService.instance;
  }

  private loadConfig(): EnvironmentConfig {
    // In development, use localhost
    const isDevelopment = window.location.hostname === 'localhost' || 
                         window.location.hostname === '127.0.0.1';

    if (isDevelopment) {
      return {
        requireImageUrl: FeatureFlags.REQUIRE_IMAGE_URL_DEV,
        enableAdvancedFeatures: FeatureFlags.ENABLE_ADVANCED_FEATURES_DEV,
        apiBaseUrl: 'http://localhost:5005',
        environment: Environment.DEVELOPMENT
      };
    } else {
      // Production configuration
      return {
        requireImageUrl: FeatureFlags.REQUIRE_IMAGE_URL_PROD,
        enableAdvancedFeatures: FeatureFlags.ENABLE_ADVANCED_FEATURES_PROD,
        apiBaseUrl: window.location.origin.replace('4200', '5005'), // Assume backend on same domain
        environment: Environment.PRODUCTION
      };
    }
  }

  public getConfig(): EnvironmentConfig {
    return this.config;
  }

  public requireImageUrl(): boolean {
    return this.config.requireImageUrl;
  }

  public enableAdvancedFeatures(): boolean {
    return this.config.enableAdvancedFeatures;
  }

  public getApiBaseUrl(): string {
    return this.config.apiBaseUrl;
  }

  public isDevelopment(): boolean {
    return this.config.environment === Environment.DEVELOPMENT;
  }

  public isProduction(): boolean {
    return this.config.environment === Environment.PRODUCTION;
  }
}

// Export singleton instance
export const environmentService = EnvironmentService.getInstance(); 