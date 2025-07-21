import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDividerModule } from '@angular/material/divider';
import { MatDialog, MatDialogModule, MatDialogConfig } from '@angular/material/dialog';
import { AddPodDialogComponent } from './add-pod-dialog/add-pod-dialog';
import { EditPodDialogComponent } from './edit-pod-dialog/edit-pod-dialog';
import { AlertDialogComponent } from './alert-dialog/alert-dialog';
import { ModeSelectorComponent } from './mode-selector/mode-selector';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { ApiConfig } from './config/api.config';
import { ModeManager, ResourceManagerMode } from './config/mode.config';

@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    FormsModule,
    HttpClientModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDividerModule,
    MatDialogModule,
    MatTableModule,
    MatIconModule,
    AddPodDialogComponent,
    EditPodDialogComponent,
    ModeSelectorComponent
  ],
  templateUrl: './app.html',
  styleUrl: './app.css',
  standalone: true
})
export class App {
  protected readonly title = signal('frontend');

  servers: any[] = [];
  selectedServer: any = null;
  consistencyMessage: string = '';
  consistencyCheckInterval: any;
  podMessage: string = '';
  podMessageType: 'success' | 'error' | '' = '';
  clusterStatus: string = 'unknown';
  clusterStatusInterval: any;
  modeCheckInterval: any;
  showModeSelector: boolean = false;
  currentModeConfig: any = null;

  constructor(private http: HttpClient, private dialog: MatDialog) {
    // Initialize mode manager
    ModeManager.initialize();
    
    // Validate API configuration on startup
    ApiConfig.validateConfig();
    this.fetchServers();
    this.getCurrentMode();
    this.updateCurrentModeDisplay();
  }

  onModeChanged(mode: any) {
    // Send mode change to backend
    this.http.post(ApiConfig.getModeUrl(), { mode: mode }).subscribe({
      next: (response: any) => {
        console.log('Mode changed successfully:', response);
        // Update mode display
        this.updateCurrentModeDisplay();
        // Refresh data when mode changes
        this.fetchServers();
        this.checkConsistency();
        
        // Handle cluster status polling based on new mode
        if (this.isRealKubernetesMode()) {
          this.startClusterStatusPolling();
        } else {
          // Stop cluster status polling if switching to demo mode
          if (this.clusterStatusInterval) {
            clearInterval(this.clusterStatusInterval);
            this.clusterStatusInterval = null;
          }
          this.clusterStatus = 'unknown';
        }
      },
      error: (error) => {
        console.error('Failed to change mode:', error);
        // Still refresh data even if mode change failed
        this.fetchServers();
        this.checkConsistency();
      }
    });
  }

  updateCurrentModeDisplay() {
    this.currentModeConfig = ModeManager.getCurrentModeConfig();
    console.log('Current mode config:', this.currentModeConfig);
    console.log('Current servers:', this.servers);
    
    // Show mode selector if no mode is selected OR if no servers are available (empty array)
    if (!this.currentModeConfig || this.servers.length === 0) {
      console.log('No mode selected or no servers available, showing mode selector');
      this.showModeSelector = true;
    } else {
      console.log('Mode selected and servers available, hiding mode selector');
      this.showModeSelector = false;
    }
  }

  isRealKubernetesMode(): boolean {
    return ModeManager.isRealKubernetesMode();
  }

  toggleModeSelector() {
    this.showModeSelector = !this.showModeSelector;
  }

  getCurrentMode() {
    // Get current mode from backend
    this.http.get(ApiConfig.getModeUrl()).subscribe({
      next: (response: any) => {
        console.log('Current mode from backend:', response);
        
        // If no current mode is set, try to load the last saved mode
        if (!response.current_mode) {
          this.loadLastSavedMode();
        } else {
          // Update mode display after getting backend response
          this.updateCurrentModeDisplay();
        }
      },
      error: (error) => {
        console.error('Failed to get current mode:', error);
        // Try to load last saved mode as fallback
        this.loadLastSavedMode();
      }
    });
  }

  loadLastSavedMode() {
    // Get last saved mode from backend
    this.http.get(ApiConfig.getLastModeUrl()).subscribe({
      next: (response: any) => {
        console.log('Last saved mode:', response);
        
        if (response.last_mode && response.last_mode !== 'null') {
          // Restore the last saved mode
          this.restoreLastMode(response.last_mode);
        } else {
          // No last mode saved, update display to show mode selector
          this.updateCurrentModeDisplay();
        }
      },
      error: (error) => {
        console.error('Failed to load last saved mode:', error);
        // Still update mode display even on error
        this.updateCurrentModeDisplay();
      }
    });
  }

  restoreLastMode(mode: string) {
    // Restore the last saved mode by sending it to the backend
    this.http.post(ApiConfig.getModeUrl(), { mode: mode }).subscribe({
      next: (response: any) => {
        console.log('Last mode restored successfully:', response);
        this.updateCurrentModeDisplay();
        this.fetchServers();
        this.checkConsistency();
        
        // Handle cluster status polling based on restored mode
        if (this.isRealKubernetesMode()) {
          this.startClusterStatusPolling();
        }
      },
      error: (error) => {
        console.error('Failed to restore last mode:', error);
        // Still update mode display even if restoration failed
        this.updateCurrentModeDisplay();
      }
    });
  }

  ngOnInit() {
    this.startConsistencyPolling();
    this.startModePolling();
    // Only start cluster status polling if in real Kubernetes mode
    if (this.isRealKubernetesMode()) {
      this.startClusterStatusPolling();
    }
  }

  ngOnDestroy() {
    if (this.consistencyCheckInterval) {
      clearInterval(this.consistencyCheckInterval);
    }
    if (this.clusterStatusInterval) {
      clearInterval(this.clusterStatusInterval);
    }
    if (this.modeCheckInterval) {
      clearInterval(this.modeCheckInterval);
    }
  }

  startConsistencyPolling() {
    this.checkConsistency();
    this.consistencyCheckInterval = setInterval(() => this.checkConsistency(), 10000);
  }

  checkConsistency() {
    this.http.get<any>(ApiConfig.getConsistencyCheckUrl()).subscribe({
      next: (res) => {
        this.consistencyMessage = res.message;
      },
      error: (err) => {
        this.consistencyMessage = err?.error?.message || 'data inconsistency error';
      }
    });
  }

  startModePolling() {
    this.checkMode();
    this.modeCheckInterval = setInterval(() => this.checkMode(), 15000); // Poll every 15 seconds
  }

  checkMode() {
    this.http.get<any>(ApiConfig.getModeUrl()).subscribe({
      next: (response: any) => {
        console.log('Mode polling response:', response);
        
        // Check if the mode has changed
        const currentBackendMode = response.current_mode;
        const currentFrontendMode = ModeManager.getCurrentMode();
        
        if (currentBackendMode !== currentFrontendMode) {
          console.log('Mode change detected:', { backend: currentBackendMode, frontend: currentFrontendMode });
          
          if (currentBackendMode) {
            // Backend has a mode, update frontend
            ModeManager.setCurrentMode(currentBackendMode as ResourceManagerMode);
            this.updateCurrentModeDisplay();
            this.fetchServers();
            this.checkConsistency();
            
            // Handle cluster status polling based on new mode
            if (this.isRealKubernetesMode()) {
              this.startClusterStatusPolling();
            } else {
              // Stop cluster status polling if switching to demo mode
              if (this.clusterStatusInterval) {
                clearInterval(this.clusterStatusInterval);
                this.clusterStatusInterval = null;
              }
              this.clusterStatus = 'unknown';
            }
          } else {
            // Backend has no mode, check for last saved mode
            this.loadLastSavedMode();
          }
        }
      },
      error: (error) => {
        console.error('Mode polling failed:', error);
      }
    });
  }

  startClusterStatusPolling() {
    this.checkClusterStatus();
    this.clusterStatusInterval = setInterval(() => this.checkClusterStatus(), 30000);
  }

  checkClusterStatus() {
    this.http.get<any>(ApiConfig.getClusterStatusUrl()).subscribe({
      next: (res) => {
        this.clusterStatus = res.status;
      },
      error: (err) => {
        this.clusterStatus = 'connection_failed';
      }
    });
  }

  fetchServers() {
    this.http.get<any[]>(ApiConfig.getServersUrl()).subscribe({
      next: (data) => {
        this.servers = data;
        if (this.servers.length > 0 && !this.selectedServer) {
          this.selectedServer = this.servers[0];
        }
        // Update mode display after fetching servers
        this.updateCurrentModeDisplay();
      },
      error: () => {
        // Handle error silently or show alert
        // Still update mode display even on error
        this.updateCurrentModeDisplay();
      }
    });
  }

  deletePod(pod: any) {
    if (!this.selectedServer) return;
    const payload = {
      ServerName: this.selectedServer.id,
      PodName: pod.pod_id
    };
    this.http.post(ApiConfig.getDeletePodUrl(), payload).subscribe({
      next: () => {
        this.showAlert(
          'success',
          'Pod Decommissioned',
          `Pod "${pod.pod_id}" has been successfully decommissioned.`
        );
        this.fetchServers();
      },
      error: (err) => {
        const errorMsg = err?.error?.error || 'An error occurred while decommissioning the pod.';
        this.showAlert(
          'error',
          'Decommission Failed',
          `${errorMsg} Please try again or contact support if the issue persists.`
        );
      }
    });
  }



  openAddPodDialog() {
    if (!this.selectedServer) {
      this.showAlert(
        'error',
        'No Server Selected',
        'Please select a server before deploying a pod.'
      );
      return;
    }

    const dialogRef = this.dialog.open(AddPodDialogComponent, {
      width: '480px',
      data: {
        serverId: this.selectedServer.id,
        serverName: this.selectedServer.name,
        serverResources: this.selectedServer.resources,
        existingPods: this.selectedServer.pods || []
      }
    });

    dialogRef.componentInstance.podCreated.subscribe((pod: any) => {
      this.deployPod(pod, this.selectedServer.id);
    });
  }

  deployPod(podData: any, serverId: string) {
    const payload = { ...podData, ServerName: serverId };
    this.http.post(ApiConfig.getCreatePodUrl(), payload).subscribe({
      next: () => {
        this.showAlert(
          'success',
          'Deployment Successful',
          `Pod "${payload.PodName}" has been successfully deployed.`
        );
        this.fetchServers();
      },
      error: (err) => {
        const errorMsg = err?.error?.error || 'Failed to deploy pod.';
        this.showAlert(
          'error',
          'Deployment Failed',
          `${errorMsg} Please verify the configuration and try again.`
        );
      }
    });
  }

  openEditPodDialog(pod: any): void {
    const server = this.servers.find((s: any) => s.name === pod.serverName);
    if (!server) {
      this.showAlert(
        'error',
        'Server Not Found',
        'Server not found.'
      );
      return;
    }

    const dialogRef = this.dialog.open(EditPodDialogComponent, {
      width: '480px',
      data: { 
        pod,
        serverResources: server.resources
      }
    });

    dialogRef.componentInstance.podUpdated.subscribe((updatedPod: any) => {
      this.updatePod(updatedPod);
    });
  }

  updatePod(pod: any) {
    const server = this.servers.find((s: any) => s.name === pod.serverName);
    if (!server) {
      this.showAlert(
        'error',
        'Server Not Found',
        'Unable to locate the specified server. Please refresh and try again.'
      );
      return;
    }

    const payload = {
      ServerName: server.id,
      PodName: pod.pod_id,
      Resources: {
        gpus: pod.requested.gpus,
        ram_gb: pod.requested.ram_gb,
        storage_gb: pod.requested.storage_gb
      },
      image_url: pod.image_url,
      machine_ip: pod.machine_ip,
      Owner: pod.owner
    };

    this.http.post(ApiConfig.getUpdatePodUrl(), payload).subscribe({
      next: () => {
        this.showAlert(
          'success',
          'Update Successful',
          `Resource allocation successfully updated for pod "${pod.pod_id}"`
        );
        this.fetchServers();
      },
      error: (err) => {
        const errorMsg = err?.error?.error || 'An error occurred while updating the resource allocation.';
        this.showAlert(
          'error',
          'Update Failed',
          `${errorMsg} Please try again or contact support if the issue persists.`
        );
      }
    });
  }

  compareServers = (a: any, b: any) => a && b && a.id === b.id;

  get totalServers() {
    return this.servers.length;
  }

  get totalPods() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.pods?.length || 0), 0);
  }

  get totalCPUs() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.resources?.total?.cpus || 0), 0);
  }

  get allocatedCPUs() {
    return Math.max(
      0,
      this.servers.reduce((acc: number, s: any) => acc + ((s.resources?.total?.cpus || 0) - (s.resources?.available?.cpus || 0)), 0)
    );
  }

  get totalGPUs() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.resources?.total?.gpus || 0), 0);
  }

  get allocatedGPUs() {
    return Math.max(
      0,
      this.servers.reduce((acc: number, s: any) => acc + ((s.resources?.total?.gpus || 0) - (s.resources?.available?.gpus || 0)), 0)
    );
  }

  get totalRAM() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.resources?.total?.ram_gb || 0), 0);
  }

  get availableRAM() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.resources?.available?.ram_gb || 0), 0);
  }

  get allPods() {
    // Flatten all pods from all servers, add serverName property
    return this.servers.flatMap((s: any) => (s.pods || []).map((p: any) => ({ ...p, serverName: s.name })));
  }

  get formattedPodMessage(): string {
    return this.podMessage
      ? this.podMessage.replace(/\n/g, '<br>').replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;')
      : '';
  }


  selectServer(server: any) {
    this.selectedServer = server;
  }

  onConsistencyLedClick() {
    // Handle unknown/empty consistency message
    if (!this.consistencyMessage) {
      this.showAlert(
        'info',
        'Consistency Status',
        'Data consistency status is unknown. Checking now...'
      );
      this.checkConsistency();
      return;
    }
    
    // Determine alert type based on consistency message
    const isError = this.consistencyMessage?.toLowerCase().includes('error') || 
                   this.consistencyMessage?.toLowerCase().includes('inconsistency');
    const alertType = isError ? 'error' : 'success';
    
    // Show the consistency message in a snackbar
    this.showAlert(
      alertType,
      'Consistency Status',
      this.consistencyMessage
    );
    // Trigger a new consistency check immediately
    this.checkConsistency();
  }

  onClusterStatusClick() {
    // Handle unknown cluster status
    if (!this.clusterStatus || this.clusterStatus === 'unknown') {
      this.showAlert(
        'info',
        'Cluster Status',
        'Cluster status is unknown. Checking now...'
      );
      this.checkClusterStatus();
      return;
    }
    
    this.http.get<any>(ApiConfig.getHealthDetailedUrl()).subscribe({
      next: (res) => {
        const details = Object.entries(res.health_checks || {})
          .map(([check, result]: [string, any]) => 
            `${check.replace(/_/g, ' ').toUpperCase()}: ${result.status} - ${result.details}`
          )
          .join('\n');
        
        // Determine alert type based on cluster status
        const clusterStatus = res.cluster_status?.status || 'unknown';
        let alertType: 'success' | 'error' | 'info';
        
        if (clusterStatus === 'healthy') {
          alertType = 'success';
        } else if (clusterStatus === 'degraded') {
          alertType = 'info'; // Blue info alert for degraded status
        } else {
          alertType = 'error';
        }
        
        this.showAlert(
          alertType,
          'Kubernetes Cluster Health',
          `Status: ${clusterStatus}\n\n${details}`
        );
      },
      error: (err) => {
        this.showAlert(
          'error',
          'Cluster Health Check Failed',
          'Unable to retrieve detailed cluster health information.'
        );
      }
    });
  }

  showAlert(type: 'success' | 'error' | 'info', title: string, message: string, details?: string[]) {
    this.dialog.open(AlertDialogComponent, {
      data: { type, title, message, details },
      position: { top: '40px' }
    });
  }

  // Helper functions for pod status
  getStatusColor(status: string): string {
    const statusColors: { [key: string]: string } = {
      'online': 'status-success',
      'starting': 'status-success',
      'pending': 'status-pending',
      'in-progress': 'status-progress',
      'updating': 'status-progress',
      'failed': 'status-error',
      'error': 'status-error',
      'timeout': 'status-error',
      'unknown': 'status-unknown'
    };
    return statusColors[status] || 'status-unknown';
  }

  getStatusIcon(status: string): string {
    const statusIcons: { [key: string]: string } = {
      'online': 'check_circle',
      'starting': 'hourglass_empty',
      'pending': 'schedule',
      'in-progress': 'sync',
      'updating': 'update',
      'failed': 'error',
      'error': 'error_outline',
      'timeout': 'schedule',
      'unknown': 'help_outline'
    };
    return statusIcons[status] || 'help_outline';
  }

  getStatusDisplayName(status: string): string {
    const statusNames: { [key: string]: string } = {
      'online': 'Online',
      'starting': 'Starting',
      'pending': 'Pending',
      'in-progress': 'In Progress',
      'updating': 'Updating',
      'failed': 'Failed',
      'error': 'Error',
      'timeout': 'Timeout',
      'unknown': 'Unknown'
    };
    return statusNames[status] || 'Unknown';
  }

  // Add this method to handle mode selector resetResult event
  onModeSelectorMessage(result: { type: string; message: string; details?: string[] }) {
    const type = (result.type === 'success' || result.type === 'error' || result.type === 'info') ? result.type : 'success';
    this.showAlert(type, type.charAt(0).toUpperCase() + type.slice(1), result.message, result.details);
    
    // If reset was successful, immediately clear the display and show mode selector
    if (result.type === 'success' && result.message.includes('reset')) {
      console.log('Mode reset successful, clearing display and showing mode selector');
      // Clear current mode and data
      ModeManager.setCurrentMode(undefined as any);
      this.servers = [];
      this.selectedServer = null;
      this.currentModeConfig = null;
      // Show mode selector
      this.showModeSelector = true;
      // Stop any active polling
      if (this.clusterStatusInterval) {
        clearInterval(this.clusterStatusInterval);
        this.clusterStatusInterval = null;
      }
      this.clusterStatus = 'unknown';
    }
  }
}
