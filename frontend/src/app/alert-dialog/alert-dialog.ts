import { Component, Inject, OnInit, OnDestroy } from '@angular/core';
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
        <p class="alert-message" [innerHTML]="formatMessage(data.message)"></p>
        <ul *ngIf="data.details && data.details.length" class="alert-details">
          <li *ngFor="let detail of data.details">{{ detail }}</li>
        </ul>
        <div class="progress-container">
          <div class="progress-bar" [style.width.%]="progressPercentage"></div>
        </div>
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
      padding-left: 20px;
      font-size: 0.9rem;
    }

    .progress-container {
      margin-top: 12px;
      height: 4px;
      background-color: rgba(0, 0, 0, 0.1);
      border-radius: 2px;
      overflow: hidden;
    }

    .progress-bar {
      height: 100%;
      border-radius: 2px;
      transition: width 0.3s ease;
    }

    .success .progress-bar {
      background-color: #4caf50;
    }

    .error .progress-bar {
      background-color: #f44336;
    }

    .info .progress-bar {
      background-color: #2196f3;
    }

    @media (max-width: 600px) {
      .alert-container {
        min-width: 300px;
        padding: 16px;
      }
      
      .alert-content {
        padding-right: 30px;
      }
    }
  `]
})
export class AlertDialogComponent implements OnInit, OnDestroy {
  countdown: number = 5;
  progressPercentage: number = 100;
  private countdownInterval: any;
  private progressInterval: any;
  private readonly TOTAL_TIME = 5; // 5 seconds total
  private startTime: number = Date.now();

  constructor(
    public dialogRef: MatDialogRef<AlertDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      type: 'success' | 'error' | 'info';
      title: string;
      message: string;
      details?: string[];
    }
  ) {}

  ngOnInit() {
    // Start smooth progress bar update (every 100ms)
    this.progressInterval = setInterval(() => {
      const elapsed = (Date.now() - this.startTime) / 1000;
      const remaining = Math.max(0, this.TOTAL_TIME - elapsed);
      this.progressPercentage = (remaining / this.TOTAL_TIME) * 100;
      
      if (remaining <= 0) {
        this.dialogRef.close();
      }
    }, 100); // Update every 100ms for smooth animation

    // Start countdown timer (every 1 second for display purposes)
    this.countdownInterval = setInterval(() => {
      this.countdown--;
      if (this.countdown <= 0) {
        this.dialogRef.close();
      }
    }, 1000);
  }

  ngOnDestroy() {
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
    }
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
    }
  }

  formatMessage(message: string): string {
    return message.replace(/\n/g, '<br>');
  }
} 