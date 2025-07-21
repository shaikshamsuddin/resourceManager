import { Component, EventEmitter, Inject, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { PodDialogBase, PodDialogData, PodResources } from '../shared/pod-dialog.base';
import { environmentService } from '../config/environment.config';
import { DefaultValues, ResourceType } from '../constants/app.constants';

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
        <mat-form-field appearance="outline" style="width: 100%" [class.error-field]="nameError">
          <mat-label>Pod Name</mat-label>
          <input matInput [(ngModel)]="pod.PodName" name="PodName" required
                 (ngModelChange)="onPodNameChange($event)">
          <mat-error *ngIf="nameError">{{ nameError }}</mat-error>
        </mat-form-field>
        <div class="form-section-title">Resources</div>
        <mat-form-field appearance="outline" [class.error-field]="resourceErrors['gpus']">
          <mat-label>GPUs</mat-label>
          <input matInput type="number" [(ngModel)]="pod.Resources.gpus" 
                 name="gpus" required (ngModelChange)="onResourceChange('gpus')"
                 min="0" [max]="getMaxAvailable('gpus')">
          <mat-hint>Available: {{ getMaxAvailable('gpus') }} GPUs</mat-hint>
          <mat-error *ngIf="resourceErrors['gpus']">{{ resourceErrors['gpus'] }}</mat-error>
        </mat-form-field>
        <mat-form-field appearance="outline" [class.error-field]="resourceErrors['ram_gb']">
          <mat-label>RAM (GB)</mat-label>
          <input matInput type="number" [(ngModel)]="pod.Resources.ram_gb" 
                 name="ram_gb" required (ngModelChange)="onResourceChange('ram_gb')"
                 min="0" [max]="getMaxAvailable('ram_gb')">
          <mat-hint>Available: {{ getMaxAvailable('ram_gb') }} GB</mat-hint>
          <mat-error *ngIf="resourceErrors['ram_gb']">{{ resourceErrors['ram_gb'] }}</mat-error>
        </mat-form-field>
        <mat-form-field appearance="outline" [class.error-field]="resourceErrors['storage_gb']">
          <mat-label>Storage (GB)</mat-label>
          <input matInput type="number" [(ngModel)]="pod.Resources.storage_gb" 
                 name="storage_gb" required (ngModelChange)="onResourceChange('storage_gb')"
                 min="0" [max]="getMaxAvailable('storage_gb')">
          <mat-hint>Available: {{ getMaxAvailable('storage_gb') }} GB</mat-hint>
          <mat-error *ngIf="resourceErrors['storage_gb']">{{ resourceErrors['storage_gb'] }}</mat-error>
        </mat-form-field>
        <!-- Image URL field - conditionally shown based on environment -->
        <div class="form-section-title" *ngIf="environmentService.requireImageUrl()">Image Details</div>
        <mat-form-field appearance="outline" style="width: 100%" *ngIf="environmentService.requireImageUrl()">
          <mat-label>Image URL</mat-label>
          <input matInput [(ngModel)]="pod.image_url" name="image_url" required>
        </mat-form-field>
        <mat-dialog-actions align="end">
          <button mat-button type="button" (click)="onCancel()">Cancel</button>
          <button mat-raised-button color="primary" type="submit" 
                  [disabled]="!podForm.form.valid || hasErrors()">Deploy Pod</button>
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
export class AddPodDialogComponent extends PodDialogBase {
  @Output() podCreated = new EventEmitter<any>();

  // Make environmentService accessible in template
  environmentService = environmentService;

  pod = {
    PodName: '',
    Resources: {
      [ResourceType.GPUS]: DefaultValues.DEFAULT_GPUS,
      [ResourceType.RAM_GB]: DefaultValues.DEFAULT_MEMORY_GB,
      [ResourceType.STORAGE_GB]: DefaultValues.DEFAULT_STORAGE_GB
    } as PodResources,
    image_url: DefaultValues.DEFAULT_IMAGE,
    ServerName: '',
    ServerDisplayName: ''
  };

  constructor(
    dialogRef: MatDialogRef<AddPodDialogComponent>,
    @Inject(MAT_DIALOG_DATA) data: PodDialogData
  ) {
    super(dialogRef, data);
    this.pod.ServerName = data.serverId;
    this.pod.ServerDisplayName = data.serverName;
  }

  onResourceChange(resource: string) {
    this.validateResources(resource, this.pod.Resources);
  }

  onPodNameChange(podName: string) {
    this.validatePodName(podName);
  }

  onSubmit() {
    this.validateAllResources(this.pod.Resources);
    if (!this.validatePodName(this.pod.PodName) || this.hasResourceErrors()) {
      return;
    }
    this.podCreated.emit(this.pod);
    this.dialogRef.close();
  }
}
