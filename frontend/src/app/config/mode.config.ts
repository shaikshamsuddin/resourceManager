/**
 * Mode Configuration for Resource Manager
 * Controls backend behavior and data sources
 */

export enum ResourceManagerMode {
  DEMO = 'demo',
  LIVE = 'live'
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
    name: 'Demo Mode',
    description: 'Work with realistic demo servers and mock data',
    icon: 'play_circle',
    color: '#4CAF50',
    backendEnv: 'demo',
    features: [
      'Demo servers only',
      'Realistic mock data',
      'Full UI functionality',
      'No real Kubernetes required',
      'Perfect for demos and testing'
    ]
  },
  [ResourceManagerMode.LIVE]: {
    id: ResourceManagerMode.LIVE,
    name: 'Live Mode',
    description: 'Work with real Kubernetes clusters and infrastructure',
    icon: 'cloud',
    color: '#2196F3',
    backendEnv: 'live',
    features: [
      'Real clusters only',
      'Live resource management',
      'Production/Dev clusters',
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
    return this.currentMode === ResourceManagerMode.LIVE;
  }

  /**
   * Get all available modes
   */
  static getAvailableModes(): ModeConfig[] {
    return Object.values(MODE_CONFIGS);
  }
} 