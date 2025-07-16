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

@Component({
  selector: 'app-root',
  imports: [
    CommonModule, FormsModule, HttpClientModule, RouterOutlet,
    MatCardModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatDividerModule
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

  constructor(private http: HttpClient) {
    this.fetchServers();
  }

  fetchServers() {
    this.http.get<any[]>('http://127.0.0.1:5000/servers').subscribe({
      next: (data) => {
        this.servers = data;
        if (this.servers.length > 0) {
          this.selectedServer = this.servers[0];
        }
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

  get totalPods() {
    return this.servers.reduce((acc: number, s: any) => acc + (s.pods?.length || 0), 0);
  }
}
