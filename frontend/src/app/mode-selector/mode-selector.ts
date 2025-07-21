import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { HttpClient } from '@angular/common/http';

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
        <h3>Resource Manager Mode</h3>
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
    
    .mode-selector-header h3 {
      margin: 0 0 8px 0;
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
  `]
})
export class ModeSelectorComponent {
  @Output() modeChanged = new EventEmitter<ResourceManagerMode>();
  
  availableModes: ModeConfig[] = [];
  selectedMode: ResourceManagerMode = ResourceManagerMode.DEMO;

    constructor(private http: HttpClient) {
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
    this.selectedMode = mode;
    // Immediately apply the mode change
    ModeManager.setCurrentMode(this.selectedMode);
    this.modeChanged.emit(this.selectedMode);
  }
} 