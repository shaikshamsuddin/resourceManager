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

import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { ApiConfig } from './config/api.config';


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
],
  templateUrl: './app.html',
  styleUrl: './app.css',
  standalone: true
})
export class App {
  protected readonly title = signal('frontend');

  servers: any[] = [];
  selectedServer: any = null;
  resourceIntegrityMessage: string = '';
  resourceIntegrityCheckInterval: any;
  podMessage: string = '';
  podMessageType: 'success' | 'error' | '' = '';
  azureVMStatus: string = 'unknown';
  azureVMStatusInterval: any;

  constructor(private http: HttpClient, private dialog: MatDialog) {
    // Validate API configuration on startup
    ApiConfig.validateConfig();
    this.fetchServers();
  }

  ngOnInit() {
    this.startResourceIntegrityPolling();
    this.startAzureVMStatusPolling();
  }

  ngOnDestroy() {
    if (this.resourceIntegrityCheckInterval) {
      clearInterval(this.resourceIntegrityCheckInterval);
    }
    if (this.azureVMStatusInterval) {
      clearInterval(this.azureVMStatusInterval);
    }
  }

  startResourceIntegrityPolling() {
    this.checkResourceIntegrity();
    this.resourceIntegrityCheckInterval = setInterval(() => this.checkResourceIntegrity(), 10000);
  }

  checkResourceIntegrity() {
    this.http.get<any>(ApiConfig.getResourceValidationUrl()).subscribe({
      next: (res) => {
        this.resourceIntegrityMessage = res.message;
      },
      error: (err) => {
        this.resourceIntegrityMessage = err?.error?.message || 'resource validation error';
      }
    });
  }



  startAzureVMStatusPolling() {
    this.checkAzureVMStatus();
    this.azureVMStatusInterval = setInterval(() => this.checkAzureVMStatus(), 30000);
  }

  checkAzureVMStatus() {
    // Check Azure VM connection by making a request to the servers endpoint
    this.http.get<any[]>(ApiConfig.getServersUrl()).subscribe({
      next: (res) => {
        if (res && res.length > 0) {
          // Check if we can get server details and if the server is responsive
          const server = res[0];
          if (server.status === 'Online' || server.status === 'online') {
            this.azureVMStatus = 'connected';
          } else {
            this.azureVMStatus = 'server_unavailable';
          }
        } else {
          this.azureVMStatus = 'connection_failed';
        }
      },
      error: (err) => {
        console.error('Azure VM connection check failed:', err);
        this.azureVMStatus = 'connection_failed';
      }
    });
  }

  fetchServers() {
    // Get data based on environment - using unified backend API
    this.http.get<any[]>(ApiConfig.getServersUrl()).subscribe({
      next: (response) => {
        console.log('Fetched servers:', response);
        // Populate servers array with all available servers for the selection card
        this.servers = response;
        // Don't auto-select a server - let user choose from the card
        if (this.servers.length > 0 && !this.selectedServer) {
          // Only auto-select if no server is currently selected
          this.selectedServer = this.servers[0];
        }
      },
      error: (error) => {
        console.error('Error fetching servers:', error);
        this.servers = [];
      }
    });
  }

  deletePod(pod: any) {
    if (!this.selectedServer) return;
    const payload = {
      server_id: this.selectedServer.server_id || this.selectedServer.id,
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
        serverId: this.selectedServer.server_id || this.selectedServer.id,
        serverName: this.selectedServer.server_name || this.selectedServer.name,
        serverResources: this.selectedServer.resources,
        existingPods: this.selectedServer.pods || []
      }
    });

    dialogRef.componentInstance.podCreated.subscribe((pod: any) => {
      this.deployPod(pod, this.selectedServer.server_id || this.selectedServer.id);
    });
  }

  deployPod(podData: any, serverId: string) {
    const payload = { ...podData, server_id: serverId };
    this.http.post(ApiConfig.getCreatePodUrl(), payload).subscribe({
      next: () => {
        this.showAlert(
          'success',
          'Deployment Successful',
          `Pod "${podData.PodName}" has been successfully deployed to the selected server.`
        );
        this.fetchServers();
      },
      error: (err) => {
        const errorMsg = err?.error?.error || 'An error occurred during deployment.';
        this.showAlert(
          'error',
          'Deployment Failed',
          `${errorMsg} Please check the server resources and try again.`
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
      ? this.podMessage.replace(/\n/g, '<br>')
      : '';
  }

  onResourceIntegrityLedClick() {
    // Handle unknown/empty resource integrity message
    if (!this.resourceIntegrityMessage) {
      this.showAlert(
        'info',
        'Resource Integrity Status',
        'Resource integrity status is unknown. Checking now...'
      );
      this.checkResourceIntegrity();
      return;
    }
    
    // Determine alert type based on resource integrity message
    const isError = this.resourceIntegrityMessage?.toLowerCase().includes('error') || 
                   this.resourceIntegrityMessage?.toLowerCase().includes('failed') ||
                   this.resourceIntegrityMessage?.toLowerCase().includes('invalid');
    const alertType = isError ? 'error' : 'success';
    
    // Show the resource integrity message in a snackbar
    this.showAlert(
      alertType,
      'Resource Integrity Status',
      this.resourceIntegrityMessage
    );
    // Trigger a new resource integrity check immediately
    this.checkResourceIntegrity();
  }

  onAzureVMStatusClick() {
    // Handle unknown Azure VM status
    if (!this.azureVMStatus || this.azureVMStatus === 'unknown') {
      this.showAlert(
        'info',
        'Azure VM Status',
        'Azure VM status is unknown. Checking now...'
      );
      this.checkAzureVMStatus();
      return;
    }
    
    // Get detailed Azure VM connection information
    this.http.get<any[]>(ApiConfig.getServersUrl()).subscribe({
      next: (response) => {
        if (response && response.length > 0) {
          const server = response[0];
          const status = server.status || 'unknown';
          const location = server.metadata?.location || server.ip || 'Unknown location';
          const pods = server.pods?.length || 0;
          
          let alertType: 'success' | 'error' | 'info' = 'info';
          if (status === 'Online' || status === 'online') {
            alertType = 'success';
          } else {
            alertType = 'error';
          }
          
          const details = `Server: ${server.server_name || server.name}\nLocation: ${location}\nStatus: ${status}\nActive Pods: ${pods}`;
          
          this.showAlert(
            alertType,
            'Azure VM Connection Status',
            details
          );
        } else {
          this.showAlert(
            'error',
            'Azure VM Connection Failed',
            'No servers found. Please check your Azure VM configuration and network connectivity.'
          );
        }
      },
      error: (err) => {
        this.showAlert(
          'error',
          'Azure VM Connection Failed',
          'Unable to connect to Azure VM. Please check:\n\n• Network connectivity\n• Azure VM is running\n• Kubeconfig is properly configured\n• Backend service is accessible'
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



  selectServer(server: any) {
    this.selectedServer = server;
    console.log('Selected server:', server);
    
    // Show a brief message to confirm selection
    this.showAlert(
      'info',
      'Server Selected',
      `You are now managing: ${server.server_name || server.name}`
    );
  }
}
