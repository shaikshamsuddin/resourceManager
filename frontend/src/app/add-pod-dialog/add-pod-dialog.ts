import { Component, EventEmitter, Inject, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-add-pod-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule
  ],
  template: `
    <h2 mat-dialog-title>Deploy New Pod</h2>
    <mat-dialog-content>
      <form #podForm="ngForm" class="pod-form" (ngSubmit)="onSubmit()">
        <mat-form-field appearance="outline" >
          <mat-label>Server Name</mat-label>
          <input matInput [(ngModel)]="pod.ServerDisplayName" name="ServerDisplayName" readonly>
        </mat-form-field>
        <div class="form-section-title">Pod Details</div>
        <mat-form-field appearance="outline" style="width: 100%">
          <mat-label>Pod Name</mat-label>
          <input matInput [(ngModel)]="pod.PodName" name="PodName" required>
        </mat-form-field>
        <div class="form-section-title">Resources</div>
        <mat-form-field appearance="outline" >
          <mat-label>GPUs</mat-label>
          <input matInput type="number" [(ngModel)]="pod.Resources.gpus" name="gpus" required>
        </mat-form-field>
        <mat-form-field appearance="outline" >
          <mat-label>RAM (GB)</mat-label>
          <input matInput type="number" [(ngModel)]="pod.Resources.ram_gb" name="ram_gb" required>
        </mat-form-field>
        <mat-form-field appearance="outline" >
          <mat-label>Storage (GB)</mat-label>
          <input matInput type="number" [(ngModel)]="pod.Resources.storage_gb" name="storage_gb" required>
        </mat-form-field>
        <div class="form-section-title">Image & K8s Details</div>
        <mat-form-field appearance="outline" style="width: 100%">
          <mat-label>Image URL</mat-label>
          <input matInput [(ngModel)]="pod.image_url" name="image_url" required>
        </mat-form-field>
        <mat-form-field appearance="outline" style="width: 100%">
          <mat-label>K8s Machine IP</mat-label>
          <input matInput [(ngModel)]="pod.machine_ip" name="machine_ip" required>
        </mat-form-field>
        <mat-form-field appearance="outline" >
          <mat-label>K8s Username</mat-label>
          <input matInput [(ngModel)]="pod.username" name="username" required>
        </mat-form-field>
        <mat-form-field appearance="outline" >
          <mat-label>K8s Password</mat-label>
          <input matInput [(ngModel)]="pod.password" name="password" required type="password">
        </mat-form-field>
        <mat-dialog-actions align="end">
          <button mat-button type="button" (click)="onCancel()">Cancel</button>
          <button mat-raised-button color="primary" type="submit" [disabled]="!podForm.form.valid">Deploy Pod</button>
        </mat-dialog-actions>
      </form>
    </mat-dialog-content>
  `,
  styles: [`
    .pod-form {
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
      padding: 16px 0;
      max-height: 60vh;
      overflow-y: auto;
    }
    mat-form-field {
      width: 100%;
    }
    .form-section-title {
      font-size: 1.1rem;
      font-weight: 600;
      color: #333;
      margin: 8px 0 4px 0;
      padding-top: 8px;
      border-top: 1px solid #eee;
    }
    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin: 12px 12px 10px 12px;
    }
    @media (max-width: 900px) {
      .pod-form {
        padding: 8px 2px 4px 2px;
      }
      .dialog-actions {
        margin: 6px 2px 6px 2px;
      }
    }
  `]
})
export class AddPodDialogComponent {
  @Output() podCreated = new EventEmitter<any>();

  pod = {
    PodName: '',
    Resources: {
      gpus: 0,
      ram_gb: 0,
      storage_gb: 0
    },
    image_url: '',
    machine_ip: '',
    username: '',
    password: '',
    ServerName: '', // for backend
    ServerDisplayName: '' // for UI
  };

  constructor(
    public dialogRef: MatDialogRef<AddPodDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {
    if (data?.selectedServer) {
      this.pod.ServerName = data.selectedServer.id;
      this.pod.ServerDisplayName = data.selectedServer.name;
      this.pod.machine_ip = data.selectedServer.ip || '';
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSubmit(): void {
    this.podCreated.emit(this.pod);
    this.dialogRef.close();
  }
}
