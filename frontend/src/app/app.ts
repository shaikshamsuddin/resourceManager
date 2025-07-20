import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
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

@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    FormsModule,
    HttpClientModule,
    RouterOutlet,
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
    EditPodDialogComponent
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

  constructor(private http: HttpClient, private dialog: MatDialog) {
    this.fetchServers();
  }

  ngOnInit() {
    this.startConsistencyPolling();
  }

  ngOnDestroy() {
    if (this.consistencyCheckInterval) {
      clearInterval(this.consistencyCheckInterval);
    }
  }

  startConsistencyPolling() {
    this.checkConsistency();
    this.consistencyCheckInterval = setInterval(() => this.checkConsistency(), 10000);
  }

  checkConsistency() {
    this.http.get<any>('http://127.0.0.1:5000/consistency-check').subscribe({
      next: (res) => {
        this.consistencyMessage = res.message;
      },
      error: (err) => {
        this.consistencyMessage = err?.error?.message || 'data inconsistency error';
      }
    });
  }

  fetchServers() {
    this.http.get<any[]>('http://127.0.0.1:5000/servers').subscribe({
      next: (data) => {
        this.servers = data;
        if (this.servers.length > 0 && !this.selectedServer) {
          this.selectedServer = this.servers[0];
        }
      },
      error: () => {
        // Handle error silently or show alert
      }
    });
  }

  deletePod(pod: any) {
    if (!this.selectedServer) return;
    const payload = {
      ServerName: this.selectedServer.id,
      PodName: pod.pod_id
    };
    this.http.post('http://127.0.0.1:5000/delete', payload).subscribe({
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
    this.http.post('http://127.0.0.1:5000/create', payload).subscribe({
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

    this.http.post('http://127.0.0.1:5000/update', payload).subscribe({
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



  selectServer(server: any) {
    this.selectedServer = server;
  }

  onConsistencyLedClick() {
    // Show the consistency message in a snackbar
    this.showAlert(
      'info',
      'Consistency Status',
      this.consistencyMessage || 'No consistency status'
    );
    // Trigger a new consistency check immediately
    this.checkConsistency();
  }

  showAlert(type: 'success' | 'error' | 'info', title: string, message: string) {
    const dialogConfig = new MatDialogConfig();
    dialogConfig.position = { top: '20px' };
    dialogConfig.data = { type, title, message };
    dialogConfig.maxWidth = '600px';
    dialogConfig.minWidth = '400px';
    this.dialog.open(AlertDialogComponent, dialogConfig);
  }
}
