import { Component, Inject, Input, Output, EventEmitter } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';

@Component({
  selector: 'app-add-pod-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatDialogModule
  ],
  templateUrl: './add-pod-dialog.html',
  styleUrls: ['./add-pod-dialog.css']
})
export class AddPodDialogComponent {
  @Input() servers: any[] = [];
  @Output() podCreated = new EventEmitter<any>();

  newPod = {
    PodName: '',
    Resources: { gpus: 0, ram_gb: 0, storage_gb: 0 },
    image_url: '',
    machine_ip: '',
    username: '',
    password: ''
  };
  selectedServer: any = null;

  constructor(
    public dialogRef: MatDialogRef<AddPodDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {
    this.servers = data.servers;
    this.selectedServer = this.servers[0];
  }

  createPod() {
    this.podCreated.emit({
      ...this.newPod,
      ServerName: this.selectedServer.id,
      Owner: this.newPod.username
    });
    this.dialogRef.close();
  }

  close() {
    this.dialogRef.close();
  }
}
