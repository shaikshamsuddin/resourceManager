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
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { AddPodDialogComponent } from './add-pod-dialog/add-pod-dialog';
import { MatTableModule } from '@angular/material/table';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-root',
  imports: [
    CommonModule, FormsModule, HttpClientModule, RouterOutlet,
    MatCardModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatDividerModule,
    MatDialogModule, MatTableModule, AddPodDialogComponent
  ],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('frontend');

  servers: any[] = [];
  selectedServer: any = null;
  newPod = {
    PodName: '',
    Resources: {
      gpus: 0,
      ram_gb: 0,
      storage_gb: 0
    },
    image_url: '',
    machine_ip: '',
    username: '',
    password: ''
  };
  message = '';
  searchTerm: string = '';
  filteredServers: any[] = [];
  filteredPods: any[] = [];
  consistencyMessage: string = '';
  consistencyCheckInterval: any;
  podMessage: string = '';
  podMessageType: 'success' | 'error' | '' = '';

  constructor(private http: HttpClient, private dialog: MatDialog, private snackBar: MatSnackBar) {
    this.fetchServers();
  }

  ngOnInit() {
    this.onSearch();
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
        this.onSearch();
      },
      error: () => {
        this.message = 'Failed to load servers from backend.';
      }
    });
  }

  deletePod(pod: any) {
    if (!this.selectedServer) return;
    const payload = {
      ServerName: this.selectedServer.id,
      PodName: pod.pod_id,
      machine_ip: this.newPod.machine_ip,
      username: this.newPod.username,
      password: this.newPod.password
    };
    this.http.post('http://127.0.0.1:5000/delete', payload).subscribe({
      next: () => {
        this.message = `Pod ${pod.pod_id} deleted.`;
        this.fetchServers();
        setTimeout(() => this.message = '', 3000);
      },
      error: () => {
        this.message = 'Failed to delete pod.';
      }
    });
  }

  createPod() {
    if (!this.selectedServer) return;
    const payload = {
      ServerName: this.selectedServer.id,
      PodName: this.newPod.PodName,
      Resources: this.newPod.Resources,
      image_url: this.newPod.image_url,
      machine_ip: this.newPod.machine_ip,
      username: this.newPod.username,
      password: this.newPod.password,
      Owner: this.newPod.username
    };
    this.http.post('http://127.0.0.1:5000/create', payload).subscribe({
      next: () => {
        this.message = `Pod ${this.newPod.PodName} created.`;
        this.fetchServers();
        this.newPod = {
          PodName: '',
          Resources: { gpus: 0, ram_gb: 0, storage_gb: 0 },
          image_url: '',
          machine_ip: '',
          username: '',
          password: ''
        };
        setTimeout(() => this.message = '', 3000);
      },
      error: (err) => {
        this.message = err?.error?.error || 'Failed to create pod.';
      }
    });
  }

  openAddPodDialog() {
    const dialogRef = this.dialog.open(AddPodDialogComponent, {
      width: '480px',
      data: { selectedServer: this.selectedServer }
    });
    dialogRef.componentInstance.podCreated.subscribe((podData: any) => {
      this.createPodFromDialog(podData);
    });
  }

  createPodFromDialog(podData: any) {
    // Use selectedServer if not already set in podData
    const serverId = podData.ServerName || (this.selectedServer && this.selectedServer.id);
    if (!serverId) {
      this.snackBar.open('Please select a server to deploy the pod.', 'Close', { duration: 4000, panelClass: ['pod-snackbar-error'] });
      return;
    }
    const payload = { ...podData, ServerName: serverId };
    this.http.post('http://127.0.0.1:5000/create', payload).subscribe({
      next: () => {
        this.snackBar.open(`Pod ${payload.PodName} created successfully.`, 'Close', { duration: 4000, panelClass: ['pod-snackbar-success'] });
        this.fetchServers();
      },
      error: (err) => {
        this.snackBar.open(err?.error?.error || 'Failed to create pod.', 'Close', { duration: 4000, panelClass: ['pod-snackbar-error'] });
      }
    });
  }

  compareServers = (a: any, b: any) => a && b && a.id === b.id;

  updatePod(pod: any, updatedFields: any) {
    if (!this.selectedServer) return;
    const payload = {
      ServerName: this.selectedServer.id,
      PodName: pod.pod_id,
      ...updatedFields,
      machine_ip: this.newPod.machine_ip,
      username: this.newPod.username,
      password: this.newPod.password
    };
    this.http.post('http://127.0.0.1:5000/update', payload).subscribe({
      next: () => {
        this.message = `Pod ${pod.pod_id} updated.`;
        this.fetchServers();
        setTimeout(() => this.message = '', 3000);
      },
      error: () => {
        this.message = 'Failed to update pod.';
      }
    });
  }

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

  onSearch() {
    const term = this.searchTerm.trim().toLowerCase();
    if (!term) {
      this.filteredServers = this.servers;
      this.filteredPods = this.allPods;
      return;
    }
    this.filteredServers = this.servers.filter((s: any) =>
      s.name?.toLowerCase().includes(term) ||
      s.ip?.toLowerCase().includes(term) ||
      (s.status || '').toLowerCase().includes(term)
    );
    this.filteredPods = this.allPods.filter((p: any) =>
      p.pod_id?.toLowerCase().includes(term) ||
      p.serverName?.toLowerCase().includes(term) ||
      (p.status || '').toLowerCase().includes(term)
    );
  }

  selectServer(server: any) {
    this.selectedServer = server;
  }
}
