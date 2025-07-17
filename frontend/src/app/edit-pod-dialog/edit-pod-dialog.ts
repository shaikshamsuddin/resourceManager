import { Component, EventEmitter, Inject, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { PodDialogBase, PodDialogData } from '../shared/pod-dialog.base';

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
    <h2 mat-dialog-title>Update Pod</h2>
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

        <mat-form-field appearance="outline" [class.error-field]="resourceErrors['gpus']">
          <mat-label>GPUs</mat-label>
          <input matInput type="number" [(ngModel)]="pod.requested.gpus" 
                 name="gpus" required (ngModelChange)="onResourceChange('gpus')"
                 min="0" [max]="getMaxAvailable('gpus')">
          <mat-hint>Available: {{ getMaxAvailable('gpus') }} GPUs</mat-hint>
          <mat-error *ngIf="resourceErrors['gpus']">{{ resourceErrors['gpus'] }}</mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" [class.error-field]="resourceErrors['ram_gb']">
          <mat-label>RAM (GB)</mat-label>
          <input matInput type="number" [(ngModel)]="pod.requested.ram_gb" 
                 name="ram" required (ngModelChange)="onResourceChange('ram_gb')"
                 min="0" [max]="getMaxAvailable('ram_gb')">
          <mat-hint>Available: {{ getMaxAvailable('ram_gb') }} GB</mat-hint>
          <mat-error *ngIf="resourceErrors['ram_gb']">{{ resourceErrors['ram_gb'] }}</mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" [class.error-field]="resourceErrors['storage_gb']">
          <mat-label>Storage (GB)</mat-label>
          <input matInput type="number" [(ngModel)]="pod.requested.storage_gb" 
                 name="storage" required (ngModelChange)="onResourceChange('storage_gb')"
                 min="0" [max]="getMaxAvailable('storage_gb')">
          <mat-hint>Available: {{ getMaxAvailable('storage_gb') }} GB</mat-hint>
          <mat-error *ngIf="resourceErrors['storage_gb']">{{ resourceErrors['storage_gb'] }}</mat-error>
        </mat-form-field>

        <div class="form-section-title">Connection Details</div>

        <mat-form-field appearance="outline">
          <mat-label>Image URL</mat-label>
          <input matInput [(ngModel)]="pod.image_url" name="imageUrl" required
                 (ngModelChange)="onFieldChange()">
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Machine IP</mat-label>
          <input matInput [(ngModel)]="pod.machine_ip" name="machineIp" required
                 (ngModelChange)="onFieldChange()">
        </mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">Cancel</button>
      <button mat-raised-button color="primary" 
              (click)="onSubmit()" 
              [disabled]="!podForm.form.valid || hasResourceErrors() || !hasChanges">
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
    .error-field {
      ::ng-deep .mat-form-field-outline {
        border-color: #f44336;
      }
    }
    mat-error {
      font-size: 0.85rem;
      padding-top: 4px;
      color: #f44336;
    }
    mat-hint {
      font-size: 0.85rem;
      color: #666;
    }
  `]
})
export class EditPodDialogComponent extends PodDialogBase {
  @Output() podUpdated = new EventEmitter<any>();

  pod: any;
  originalPod: any;
  hasChanges = false;

  constructor(
    dialogRef: MatDialogRef<EditPodDialogComponent>,
    @Inject(MAT_DIALOG_DATA) data: PodDialogData
  ) {
    super(dialogRef, data);
    this.pod = JSON.parse(JSON.stringify(data.pod)); // Deep clone
    this.originalPod = JSON.parse(JSON.stringify(data.pod)); // Deep clone
    this.validateAllResources(this.pod.requested);
  }

  onResourceChange(resource: string) {
    this.validateResources(resource, this.pod.requested);
    this.checkChanges();
  }

  onFieldChange() {
    this.checkChanges();
  }

  checkChanges() {
    // Compare each field individually
    this.hasChanges = 
      this.pod.image_url !== this.originalPod.image_url ||
      this.pod.machine_ip !== this.originalPod.machine_ip ||
      this.pod.requested.gpus !== this.originalPod.requested.gpus ||
      this.pod.requested.ram_gb !== this.originalPod.requested.ram_gb ||
      this.pod.requested.storage_gb !== this.originalPod.requested.storage_gb;
  }

  onSubmit() {
    this.validateAllResources(this.pod.requested);
    if (this.hasResourceErrors()) {
      return;
    }
    this.podUpdated.emit(this.pod);
    this.dialogRef.close();
  }
}