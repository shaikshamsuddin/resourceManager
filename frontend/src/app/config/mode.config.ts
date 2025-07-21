/**
 * Mode Configuration for Resource Manager
 * Controls backend behavior and data sources
 */

export enum ResourceManagerMode {
  DEMO = 'demo',                    // Mock data for showcasing
  LOCAL_K8S = 'local-k8s',          // Local Kubernetes (minikube)
  CLOUD_K8S = 'cloud-k8s'          // Cloud Kubernetes (Azure/GCP/AWS)
}

export interface ModeConfig {
  id: ResourceManagerMode;
  name: string;
  description: string;
  icon: string;
  color: string;
  backendEnv: string;
  features: string[];
}

export const MODE_CONFIGS: Record<ResourceManagerMode, ModeConfig> = {
  [ResourceManagerMode.DEMO]: {
    id: ResourceManagerMode.DEMO,
    name: 'Local Mock Demo',
    description: 'Showcase functionality with realistic mock data',
    icon: 'play_circle',
    color: '#4CAF50',
    backendEnv: 'local-mock-db',
    features: [
      'Realistic mock data',
      'Full UI functionality',
      'No Kubernetes required',
      'Perfect for demos'
    ]
  },
  [ResourceManagerMode.LOCAL_K8S]: {
    id: ResourceManagerMode.LOCAL_K8S,
    name: 'Local Kubernetes',
    description: 'Real Kubernetes cluster (minikube)',
    icon: 'computer',
    color: '#2196F3',
    backendEnv: 'development',
    features: [
      'Real Kubernetes pods',
      'Local resource management',
      'Minikube integration',
      'Full cluster operations'
    ]
  },
  [ResourceManagerMode.CLOUD_K8S]: {
    id: ResourceManagerMode.CLOUD_K8S,
    name: 'Cloud Kubernetes',
    description: 'Production cloud clusters (Azure/GCP/AWS)',
    icon: 'cloud',
    color: '#FF9800',
    backendEnv: 'production',
    features: [
      'Production clusters',
      'Cloud resource management',
      'Enterprise features',
      'Scalable infrastructure'
    ]
  }
};

export class ModeManager {
  private static readonly STORAGE_KEY = 'resource-manager-mode';
  private static currentMode: ResourceManagerMode | undefined = undefined;

  /**
   * Get current mode
   */
  static getCurrentMode(): ResourceManagerMode | undefined {
    return this.currentMode;
  }

  /**
   * Set current mode
   */
  static setCurrentMode(mode: ResourceManagerMode): void {
    this.currentMode = mode;
    localStorage.setItem(this.STORAGE_KEY, mode);
  }

  /**
   * Get current mode configuration
   */
  static getCurrentModeConfig(): ModeConfig | undefined {
    if (!this.currentMode) {
      return undefined;
    }
    return MODE_CONFIGS[this.currentMode];
  }

  /**
   * Initialize mode from storage or default
   */
  static initializeMode(): void {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    if (stored && Object.values(ResourceManagerMode).includes(stored as ResourceManagerMode)) {
      this.currentMode = stored as ResourceManagerMode;
    } else {
      // No default mode; require user to pick on first launch
      this.currentMode = undefined as any;
    }
  }

  /**
   * Initialize mode on app startup
   */
  static initialize(): void {
    this.initializeMode();
  }

  /**
   * Get backend environment for current mode
   */
  static getBackendEnvironment(): string {
    return this.getCurrentModeConfig()?.backendEnv || '';
  }

  /**
   * Check if current mode is demo
   */
  static isDemoMode(): boolean {
    return this.currentMode === ResourceManagerMode.DEMO;
  }

  /**
   * Check if current mode uses real Kubernetes
   */
  static isRealKubernetesMode(): boolean {
    return this.currentMode === ResourceManagerMode.LOCAL_K8S || 
           this.currentMode === ResourceManagerMode.CLOUD_K8S;
  }

  /**
   * Get all available modes
   */
  static getAvailableModes(): ModeConfig[] {
    return Object.values(MODE_CONFIGS);
  }
} 