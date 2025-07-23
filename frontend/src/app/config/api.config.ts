/**
 * API Configuration
 * Centralized configuration for all backend API endpoints and URLs
 */

import { environment } from '../../environments/environment';

export class ApiConfig {
  // Base URL configuration
  private static readonly DEFAULT_HOST = '127.0.0.1';
  private static readonly DEFAULT_PORT = '5005';
  private static readonly DEFAULT_PROTOCOL = 'http';
  

  
  // Get base URL from environment or use defaults
  private static getBaseUrl(): string {
    const host = environment.api?.host || this.DEFAULT_HOST;
    const port = environment.api?.port || this.DEFAULT_PORT;
    const protocol = environment.api?.protocol || this.DEFAULT_PROTOCOL;
    
    return `${protocol}://${host}:${port}`;
  }
  
  // Public base URL getter
  static get BASE_URL(): string {
    return this.getBaseUrl();
  }
  
  // API Endpoints
  static readonly ENDPOINTS = {
    // Health and monitoring endpoints
    HEALTH: '/health',
    HEALTH_DETAILED: '/health/detailed',

    RESOURCE_VALIDATION: '/resource-validation',
    
    // Resource management endpoints
    SERVERS: '/servers',
    CREATE_POD: '/create',
    DELETE_POD: '/delete',
    UPDATE_POD: '/update',
    

    
    // Root endpoint
    ROOT: '/'
  } as const;
  
  // Full URL getters
  static getHealthUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.HEALTH}`;
  }
  
  static getHealthDetailedUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.HEALTH_DETAILED}`;
  }
  

  
  static getResourceValidationUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.RESOURCE_VALIDATION}`;
  }
  
  static getServersUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.SERVERS}`;
  }
  
  static getCreatePodUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.CREATE_POD}`;
  }
  
  static getDeletePodUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.DELETE_POD}`;
  }
  
  static getUpdatePodUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.UPDATE_POD}`;
  }
  

  
  static getRootUrl(): string {
    return `${this.BASE_URL}${this.ENDPOINTS.ROOT}`;
  }
  

  
  // Configuration override methods for runtime changes
  static setPort(port: string): void {
    (this as any).DEFAULT_PORT = port;
  }
  
  static setHost(host: string): void {
    (this as any).DEFAULT_HOST = host;
  }
  
  // Configuration validation
  static validateConfig(): void {
    console.log(`🔧 API Configuration:`);
    console.log(`   Base URL: ${this.BASE_URL}`);
    console.log(`   Health Check: ${this.getHealthUrl()}`);
    console.log(`   Servers: ${this.getServersUrl()}`);
  }
} 