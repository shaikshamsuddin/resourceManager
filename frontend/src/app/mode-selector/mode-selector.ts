import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { HttpClient } from '@angular/common/http';
import { MatDialog } from '@angular/material/dialog';

import { ModeManager, ResourceManagerMode, ModeConfig } from '../config/mode.config';
import { ApiConfig } from '../config/api.config';

@Component({
  selector: 'app-mode-selector',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatChipsModule
  ],
  template: `
    <mat-card class="mode-selector-card">
      <div class="mode-selector-header">
        <div class="header-title-container">
          <h3>Resource Manager Mode</h3>
          <button
            mat-icon-button
            class="last-mode-reset-icon"
            matTooltip="Reset last saved mode (clear mode persistence)"
            (click)="resetLastSavedMode()"
          >
            <mat-icon>restart_alt</mat-icon>
          </button>
        </div>
        <p>Select the mode that best fits your needs</p>
      </div>
      
      <div class="mode-row">
        <div 
          *ngFor="let mode of availableModes" 
          class="mode-option"
          [class.selected]="isCurrentMode(mode.id)"
          (click)="selectMode(mode.id)"
        >
          <div class="mode-icon" [style.background-color]="mode.color">
            <mat-icon>{{ mode.icon }}</mat-icon>
          </div>
          
          <div class="mode-content">
            <h4>{{ mode.name }}</h4>
            <p>{{ mode.description }}</p>
            
            <div class="mode-features">
              <mat-chip 
                *ngFor="let feature of mode.features" 
                class="feature-chip"
                [style.background-color]="mode.color + '20'"
                [style.color]="mode.color"
              >
                {{ feature }}
              </mat-chip>
            </div>
          </div>
          
          <div class="mode-status" *ngIf="isCurrentMode(mode.id)">
            <mat-icon class="selected-icon">check_circle</mat-icon>
            <span>Active</span>
          </div>
        </div>
      </div>
      <!-- Reset icon row below the mode cards -->
      <div class="reset-row">
        <div *ngFor="let mode of availableModes" class="reset-icon-container">
          <button mat-icon-button matTooltip="Reset this mode" (click)="onResetMode(mode.id, $event)">
            <span class="reset-icon-bg" [style.background-color]="mode.color + '22'">
              <mat-icon class="reset-icon" [style.color]="mode.color">refresh</mat-icon>
            </span>
          </button>
        </div>
      </div>
    </mat-card>
  `,
  styles: [`
    .mode-selector-card {
      max-width: 800px;
      margin: 20px auto;
      padding: 24px;
    }
    
    .mode-selector-header {
      text-align: center;
      margin-bottom: 24px;
    }
    
    .header-title-container {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-bottom: 8px;
    }
    
    .mode-selector-header h3 {
      margin: 0;
      color: #333;
    }
    
    .mode-selector-header p {
      margin: 0;
      color: #666;
    }
    
    .mode-row {
      display: flex;
      justify-content: center;
      gap: 8px;
      margin-bottom: 24px;
      flex-wrap: nowrap;
    }
    
    .mode-option {
      border: 2px solid #e0e0e0;
      border-radius: 12px;
      padding: 12px;
      cursor: pointer;
      transition: all 0.3s ease;
      position: relative;
      background: white;
      min-width: 160px;
      max-width: 200px;
      flex: 1;
    }
    
    .mode-option:hover {
      border-color: #2196F3;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .mode-option.selected {
      border-color: #4CAF50;
      background: #f8fff8;
    }
    
    .mode-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 8px;
    }
    
    .mode-icon mat-icon {
      color: white;
      font-size: 20px;
      width: 20px;
      height: 20px;
    }
    
    .mode-content h4 {
      margin: 0 0 4px 0;
      color: #333;
      font-size: 14px;
    }
    
    .mode-content p {
      margin: 0 0 8px 0;
      color: #666;
      line-height: 1.3;
      font-size: 11px;
    }
    
    .mode-features {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    
    .feature-chip {
      font-size: 10px;
      height: 18px;
      padding: 0 6px;
    }
    
    .mode-status {
      position: absolute;
      top: 12px;
      right: 12px;
      display: flex;
      align-items: center;
      gap: 4px;
      color: #4CAF50;
      font-size: 12px;
      font-weight: 500;
    }
    
    .selected-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }
    .reset-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      width: 100%;
      margin-top: 0px;
      margin-bottom: 12px;
    }
    .reset-icon-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      flex: 1;
    }
    .reset-icon-bg {
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      width: 32px;
      height: 32px;
      box-shadow: 0 2px 8px 0 rgba(0,0,0,0.10);
    }
    .reset-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }
    button[mat-icon-button] {
      padding: 0;
      margin: 0;
      width: 32px;
      height: 32px;
      min-width: 32px;
      min-height: 32px;
      border-radius: 50%;
      overflow: visible;
    }
    
    .last-mode-reset-row {
      display: flex;
      justify-content: center;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid #e0e0e0;
    }
    
    .last-mode-reset-row button {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.9rem;
    }
    .last-mode-reset-icon {
      color: #888;
      background: #f3f4f6;
      border-radius: 50%;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
      transition: background 0.2s, color 0.2s;
      width: 28px;
      height: 28px;
      min-width: 28px;
      min-height: 28px;
    }
    .last-mode-reset-icon mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }
    .last-mode-reset-icon:hover {
      background: #e0e7ef;
      color: #333;
    }
  `]
})
export class ModeSelectorComponent {
  @Output() modeChanged = new EventEmitter<ResourceManagerMode>();
  @Output() resetResult = new EventEmitter<{ type: string; message: string }>();
  
  availableModes: ModeConfig[] = [];
  selectedMode: ResourceManagerMode | undefined = undefined;

  constructor(private http: HttpClient, private dialog: MatDialog) {
    this.availableModes = ModeManager.getAvailableModes();
    this.selectedMode = ModeManager.getCurrentMode();
    this.loadCurrentModeFromBackend();
  }

  loadCurrentModeFromBackend() {
    // Get current mode from backend on initialization
    this.http.get(ApiConfig.getModeUrl()).subscribe({
      next: (data: any) => {
        const backendMode = data.current_mode;
        if (backendMode && Object.values(ResourceManagerMode).includes(backendMode as ResourceManagerMode)) {
          this.selectedMode = backendMode as ResourceManagerMode;
          ModeManager.setCurrentMode(this.selectedMode);
        } else if (backendMode === null || backendMode === undefined) {
          // Backend has no mode selected - keep frontend as undefined
          this.selectedMode = undefined;
        }
      },
      error: (error) => {
        console.error('Failed to load current mode from backend:', error);
      }
    });
  }
  
  isCurrentMode(modeId: ResourceManagerMode): boolean {
    return this.selectedMode === modeId;
  }
  
  selectMode(mode: ResourceManagerMode): void {
    const previousMode = this.selectedMode;
    this.http.post(ApiConfig.getModeUrl(), { mode: mode }).subscribe({
      next: (res: any) => {
        if (res && !res.error && (res.type === undefined || res.type === 'success')) {
          this.selectedMode = mode;
          ModeManager.setCurrentMode(this.selectedMode);
          this.modeChanged.emit(this.selectedMode);
        } else if (res && (res.error || res.type === 'error' || res.type === 'info')) {
          this.resetResult.emit({ type: res.type || 'error', message: res.message || res.error });
        }
      },
      error: (err) => {
        const type = err?.error?.type || 'error';
        const message = err?.error?.message || err?.error?.error || 'Error: Mode change failed.';
        this.resetResult.emit({ type, message });
        this.selectedMode = previousMode;
      }
    });
  }
  onResetMode(mode: ResourceManagerMode, event: MouseEvent): void {
    event.stopPropagation();
    const modeLabel = mode === ResourceManagerMode.DEMO ? 'Local Mock Demo' : (mode === ResourceManagerMode.LOCAL_K8S ? 'Local Kubernetes' : 'Cloud Kubernetes');
    if (confirm(`Are you sure you want to reset all data for ${modeLabel}? This will delete all pods and reset resources.`)) {
      const modeParam = mode === ResourceManagerMode.DEMO ? 'demo' : (mode === ResourceManagerMode.LOCAL_K8S ? 'local-k8s' : 'cloud-k8s');
      this.http.post(`/reset-mode?mode=${modeParam}`, {}).subscribe({
        next: (res: any) => {
          this.resetResult.emit({ type: res.type || 'success', message: res.message || res.error || 'Reset completed.' });
        },
        error: (err) => {
          this.resetResult.emit({ type: 'error', message: err?.error?.message || err?.error?.error || 'Error: Reset failed.' });
        }
      });
    }
  }

  resetLastSavedMode(): void {
    console.log('resetLastSavedMode called');
    this.http.post(ApiConfig.getResetLastModeUrl(), {}).subscribe({
      next: (res: any) => {
        console.log('Reset response:', res);
        // Clear frontend selection and update UI
        this.selectedMode = undefined;
        ModeManager.setCurrentMode(undefined as any);
        localStorage.removeItem('resource-manager-mode');
        this.resetResult.emit({ type: res.type || 'success', message: res.message || 'Last saved mode reset successfully.' });
      },
      error: (err) => {
        console.error('Reset error:', err);
        this.resetResult.emit({ type: 'error', message: err?.error?.message || err?.error?.error || 'Error: Failed to reset last saved mode.' });
      }
    });
  }
} 