import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-alert-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <div class="alert-container" [ngClass]="data.type">
      <mat-icon class="alert-icon">
        {{ data.type === 'success' ? 'check_circle' : data.type === 'info' ? 'info' : 'error' }}
      </mat-icon>
      <div class="alert-content">
        <h2 class="alert-title">{{ data.title }}</h2>
        <p class="alert-message">{{ data.message }}</p>
        <ul *ngIf="data.details && data.details.length" class="alert-details">
          <li *ngFor="let detail of data.details">{{ detail }}</li>
        </ul>
      </div>
      <button mat-icon-button (click)="dialogRef.close()" class="close-button">
        <mat-icon>close</mat-icon>
      </button>
    </div>
  `,
  styles: [`
    .alert-container {
      display: flex;
      align-items: flex-start;
      padding: 20px;
      border-radius: 8px;
      min-width: 400px;
      position: relative;
    }

    .success {
      background-color: #e8f5e9;
      color: #1b5e20;
    }

    .error {
      background-color: #ffebee;
      color: #b71c1c;
    }

    .info {
      background-color: #e3f2fd;
      color: #0d47a1;
    }

    .alert-icon {
      margin-right: 16px;
      font-size: 24px;
      height: 24px;
      width: 24px;
    }

    .alert-content {
      flex: 1;
      padding-right: 40px;
    }

    .alert-title {
      margin: 0 0 8px 0;
      font-size: 1.1rem;
      font-weight: 500;
    }

    .alert-message {
      margin: 0;
      font-size: 0.95rem;
      line-height: 1.4;
    }

    .close-button {
      position: absolute;
      top: 8px;
      right: 8px;
    }

    .success .close-button {
      color: #1b5e20;
    }

    .error .close-button {
      color: #b71c1c;
    }

    .info .close-button {
      color: #0d47a1;
    }

    .alert-details {
      margin: 8px 0 0 0;
      padding-left: 18px;
      font-size: 0.95rem;
      color: inherit;
    }
  `]
})
export class AlertDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<AlertDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      type: 'success' | 'error' | 'info';
      title: string;
      message: string;
      details?: string[];
    }
  ) {
    // Auto-close success messages after 5 seconds
    if (data.type === 'success') {
      setTimeout(() => this.dialogRef.close(), 5000);
    }
  }
} 