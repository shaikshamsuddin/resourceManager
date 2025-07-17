import { Component, EventEmitter, Inject, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-edit-pod-dialog',
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
    <h2 mat-dialog-title>Edit Pod</h2>
    <mat-dialog-content>
      <form #podForm="ngForm" class="pod-form">
        <mat-form-field appearance="outline">
          <mat-label>Server Name</mat-label>
          <input matInput [(ngModel)]="pod.serverName" name="serverName" readonly>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Pod Name</mat-label>
          <input matInput [(ngModel)]="pod.pod_id" name="podName" readonly>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Username</mat-label>
          <input matInput [(ngModel)]="pod.owner" name="username" readonly>
        </mat-form-field>

        <div class="form-section-title">Resources</div>

        <mat-form-field appearance="outline">
          <mat-label>GPUs</mat-label>
          <input matInput type="number" [(ngModel)]="pod.requested.gpus" name="gpus" required>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>RAM (GB)</mat-label>
          <input matInput type="number" [(ngModel)]="pod.requested.ram_gb" name="ram" required>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Storage (GB)</mat-label>
          <input matInput type="number" [(ngModel)]="pod.requested.storage_gb" name="storage" required>
        </mat-form-field>

        <div class="form-section-title">Connection Details</div>

        <mat-form-field appearance="outline">
          <mat-label>Image URL</mat-label>
          <input matInput [(ngModel)]="pod.image_url" name="imageUrl" required>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Machine IP</mat-label>
          <input matInput [(ngModel)]="pod.machine_ip" name="machineIp" required>
        </mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">Cancel</button>
      <button mat-raised-button color="primary" (click)="onSubmit()" [disabled]="!podForm.form.valid">
        Update Pod
      </button>
    </mat-dialog-actions>
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
    :host ::ng-deep .mat-form-field-appearance-outline.readonly .mat-form-field-outline {
      background-color: rgba(0, 0, 0, 0.04);
    }
    .form-section-title {
      font-size: 1.1rem;
      font-weight: 600;
      color: #333;
      margin: 8px 0 4px 0;
      padding-top: 8px;
      border-top: 1px solid #eee;
    }
  `]
})
export class EditPodDialogComponent {
  @Output() podUpdated = new EventEmitter<any>();

  pod: any;

  constructor(
    public dialogRef: MatDialogRef<EditPodDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {
    // Clone the pod data to avoid modifying the original directly
    this.pod = {
      ...data.pod,
      requested: { ...data.pod.requested }  // Ensure we clone the nested requested object
    };
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSubmit(): void {
    const updatedPod = {
      pod_id: this.pod.pod_id,
      serverName: this.pod.serverName,
      owner: this.pod.owner,
      requested: {
        gpus: this.pod.requested.gpus,
        ram_gb: this.pod.requested.ram_gb,
        storage_gb: this.pod.requested.storage_gb
      },
      image_url: this.pod.image_url,
      machine_ip: this.pod.machine_ip
    };
    this.podUpdated.emit(updatedPod);
    this.dialogRef.close();
  }
}